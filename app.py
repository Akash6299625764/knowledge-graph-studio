
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import os, re
from dotenv import load_dotenv
load_dotenv()
from database import (
    init_db, migrate_json_if_needed, load_db, db_to_vis,
    insert_node, update_node, delete_node, node_exists,
    insert_edge, delete_edge, edge_key_exists,
    next_node_id, next_edge_id, clear_all
)

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# ── Init DB on startup ───────────────────────────────────────────────────────
init_db()
migrate_json_if_needed()

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/graph", methods=["GET"])
def get_graph():
    return jsonify(db_to_vis())

@app.route("/node", methods=["POST"])
def add_node():
    data  = request.get_json()
    label = data.get("label", "").strip()
    ntype = data.get("type", "Node").strip()
    props = data.get("properties", {})
    if not label:
        return jsonify({"error": "Label required"}), 400
    nid = next_node_id(label)
    while node_exists(nid):
        nid += "_"
    insert_node(nid, label, ntype, props)
    return jsonify({"id": nid, "graph": db_to_vis()})

@app.route("/node/<nid>", methods=["PUT"])
def update_node_route(nid):
    data = request.get_json()
    if not node_exists(nid):
        return jsonify({"error": "Node not found"}), 404
    db   = load_db()
    node = db["nodes"][nid]
    update_node(
        nid,
        data.get("label",      node["label"]),
        data.get("type",       node["type"]),
        data.get("properties", node["properties"]),
    )
    return jsonify({"graph": db_to_vis()})

@app.route("/node/<nid>", methods=["DELETE"])
def delete_node_route(nid):
    if not node_exists(nid):
        return jsonify({"error": "Node not found"}), 404
    delete_node(nid)
    return jsonify({"graph": db_to_vis()})

@app.route("/edge", methods=["POST"])
def add_edge():
    data    = request.get_json()
    from_id = data.get("from", "").strip()
    to_id   = data.get("to",   "").strip()
    rel     = data.get("relation", "RELATED_TO").strip()
    props   = data.get("properties", {})
    if not node_exists(from_id) or not node_exists(to_id):
        return jsonify({"error": "Both nodes must exist"}), 400
    eid = next_edge_id()
    insert_edge(eid, from_id, to_id, rel, props)
    return jsonify({"id": eid, "graph": db_to_vis()})

@app.route("/edge/<eid>", methods=["DELETE"])
def delete_edge_route(eid):
    delete_edge(eid)
    return jsonify({"graph": db_to_vis()})

@app.route("/query", methods=["POST"])
def query():
    from query_engine import run_query
    data   = request.get_json()
    q      = data.get("q", "").strip()
    result = run_query(q, load_db())
    return jsonify(result)

@app.route("/clear", methods=["POST"])
def clear():
    clear_all()
    return jsonify({"graph": {"nodes": [], "edges": []}})

@app.route("/fix_edges", methods=["GET","POST"])
def fix_edges():
    from database import get_db
    result = get_db().edges.delete_many({"label": {"$regex": "^}"}})
    return jsonify({"deleted": result.deleted_count, "graph": db_to_vis()})

# ── OWL ──────────────────────────────────────────────────────────────────────

@app.route("/owl/parse", methods=["POST"])
def owl_parse():
    from owl_parser import owl_to_graph, validate_owl
    data = request.get_json()
    err  = validate_owl(data.get("owl",""))
    if err:
        return jsonify({"error": err}), 400
    graph = owl_to_graph(data["owl"])
    # normalize ner → type so frontend displays correctly
    nodes = [{"id": n["id"], "label": n.get("label", n["id"]), "type": n.get("ner","Concept")} for n in graph["nodes"]]
    edges = [e for e in graph["edges"] if e["label"] not in ("type","label")]
    return jsonify({"graph": {"nodes": nodes, "edges": edges}})

@app.route("/owl/import", methods=["POST"])
def owl_import():
    from owl_parser import owl_to_graph, validate_owl
    data = request.get_json()
    err  = validate_owl(data.get("owl",""))
    if err:
        return jsonify({"error": err}), 400
    graph = owl_to_graph(data["owl"])
    added_nodes = added_edges = 0
    for n in graph["nodes"]:
        nid = re.sub(r"\W+", "_", n["id"])
        if not node_exists(nid):
            insert_node(nid, n.get("label", n["id"]), n.get("ner","Concept"), {})
            added_nodes += 1
    for e in graph["edges"]:
        if e["label"] in ("type", "label"):
            continue
        fid = re.sub(r"\W+", "_", e["from"])
        tid = re.sub(r"\W+", "_", e["to"])
        if node_exists(fid) and node_exists(tid) and not edge_key_exists(fid, tid, e["label"]):
            insert_edge(next_edge_id(), fid, tid, e["label"], {})
            added_edges += 1
    return jsonify({"graph": db_to_vis(), "added_nodes": added_nodes, "added_edges": added_edges})

# ── PDF ───────────────────────────────────────────────────────────────────────

@app.route("/upload", methods=["POST"])
def upload():
    if "pdf" not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files["pdf"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "PDF only"}), 400
    path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(path)
    try:
        from extractor import extract_graph
        result = extract_graph(path)
        for n in result["nodes"]:
            nid = n["id"]
            if not node_exists(nid):
                insert_node(nid, n["label"], n.get("type","Concept"), {})
        for e in result["edges"]:
            if node_exists(e["from"]) and node_exists(e["to"]):
                if not edge_key_exists(e["from"], e["to"], e["label"]):
                    insert_edge(next_edge_id(), e["from"], e["to"], e["label"], {})
        return jsonify({"graph": db_to_vis(), "stats": result["stats"]})
    except Exception as ex:
        import traceback
        return jsonify({"error": str(ex), "trace": traceback.format_exc()}), 500

@app.route("/owl/export", methods=["GET"])
def owl_export():
    db = load_db()
    ONTO = "http://research-kg.org/ontology#"
    lines = [
        '<?xml version="1.0"?>',
        '<rdf:RDF',
        f'  xmlns:onto="{ONTO}"',
        '  xmlns:owl ="http://www.w3.org/2002/07/owl#"',
        '  xmlns:rdf ="http://www.w3.org/1999/02/22-rdf-syntax-ns#"',
        '  xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">',
        '',
        f'  <owl:Ontology rdf:about="{ONTO}"/>',
        '',
        '  <!-- Classes -->',
    ]
    types_seen = set()
    for n in db["nodes"].values():
        t = re.sub(r"\W+", "_", n.get("type", "Concept"))
        if t not in types_seen:
            lines.append(f'  <owl:Class rdf:about="{ONTO}{t}"/>')
            types_seen.add(t)
    lines.append('')
    lines.append('  <!-- Object Properties -->')
    rels_seen = set()
    for e in db["edges"]:
        r = re.sub(r"\W+", "_", e.get("label", "related_to"))
        if r not in rels_seen:
            lines.append(f'  <owl:ObjectProperty rdf:about="{ONTO}{r}"/>')
            rels_seen.add(r)
    lines.append('')
    lines.append('  <!-- Individuals -->')
    for nid, n in db["nodes"].items():
        safe_id = re.sub(r"\W+", "_", nid)
        ntype   = re.sub(r"\W+", "_", n.get("type", "Concept"))
        label   = n.get("label", nid).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        lines.append(f'  <owl:NamedIndividual rdf:about="{ONTO}{safe_id}">')
        lines.append(f'    <rdf:type rdf:resource="{ONTO}{ntype}"/>')
        lines.append(f'    <rdfs:label>{label}</rdfs:label>')
        lines.append(f'  </owl:NamedIndividual>')
    lines.append('')
    lines.append('  <!-- Relations -->')
    for e in db["edges"]:
        fid = re.sub(r"\W+", "_", e.get("from", ""))
        tid = re.sub(r"\W+", "_", e.get("to", ""))
        rel = re.sub(r"\W+", "_", e.get("label", "related_to"))
        if fid and tid:
            lines.append(f'  <rdf:Description rdf:about="{ONTO}{fid}">')
            lines.append(f'    <onto:{rel} rdf:resource="{ONTO}{tid}"/>')
            lines.append(f'  </rdf:Description>')
    lines.append('')
    lines.append('</rdf:RDF>')
    owl_text = "\n".join(lines)
    from io import BytesIO
    buf = BytesIO(owl_text.encode("utf-8"))
    buf.seek(0)
    return send_file(buf, mimetype="application/rdf+xml",
                     as_attachment=True, download_name="knowledge_graph.owl")

if __name__ == "__main__":
    app.run(debug=False, port=5000)
