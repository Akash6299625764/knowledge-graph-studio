"""
database.py  –  MongoDB persistence layer
Replaces SQLite with MongoDB.
Collections: nodes, edges
Set MONGO_URI in .env or environment variable.
Default: mongodb://localhost:27017  (local MongoDB)
For Atlas: mongodb+srv://user:pass@cluster.mongodb.net/
"""
import os, re
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.environ.get("MONGO_DB",  "knowledge_graph")

_client = None
_db     = None

def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _db     = _client[DB_NAME]
    return _db

def init_db():
    db = get_db()
    # unique index on node id
    db.nodes.create_index("id", unique=True)
    # index edges for fast lookup
    db.edges.create_index("id", unique=True)
    db.edges.create_index([("from_id", ASCENDING), ("to_id", ASCENDING), ("label", ASCENDING)])
    print(f"MongoDB connected → {DB_NAME}")

# ── Read ──────────────────────────────────────────────────────────────────────

def load_db():
    db = get_db()
    nodes = {}
    for doc in db.nodes.find({}, {"_id": 0}):
        nodes[doc["id"]] = {
            "label":      doc["label"],
            "type":       doc.get("type", "Node"),
            "properties": doc.get("properties", {}),
        }
    edges = []
    for doc in db.edges.find({}, {"_id": 0}):
        edges.append({
            "id":         doc["id"],
            "from":       doc["from_id"],
            "to":         doc["to_id"],
            "label":      doc["label"],
            "properties": doc.get("properties", {}),
        })
    return {"nodes": nodes, "edges": edges}

def db_to_vis(db=None):
    if db is None:
        db = load_db()
    nodes = [{"id": nid, **ndata} for nid, ndata in db["nodes"].items()]
    return {"nodes": nodes, "edges": db["edges"]}

# ── Write ─────────────────────────────────────────────────────────────────────

def insert_node(nid, label, ntype, properties):
    get_db().nodes.update_one(
        {"id": nid},
        {"$set": {"id": nid, "label": label, "type": ntype, "properties": properties}},
        upsert=True
    )

def update_node(nid, label, ntype, properties):
    get_db().nodes.update_one(
        {"id": nid},
        {"$set": {"label": label, "type": ntype, "properties": properties}}
    )

def delete_node(nid):
    get_db().nodes.delete_one({"id": nid})
    get_db().edges.delete_many({"$or": [{"from_id": nid}, {"to_id": nid}]})

def node_exists(nid):
    return get_db().nodes.find_one({"id": nid}, {"_id": 1}) is not None

def insert_edge(eid, from_id, to_id, label, properties):
    get_db().edges.update_one(
        {"id": eid},
        {"$set": {"id": eid, "from_id": from_id, "to_id": to_id,
                  "label": label, "properties": properties}},
        upsert=True
    )

def delete_edge(eid):
    get_db().edges.delete_one({"id": eid})

def edge_key_exists(from_id, to_id, label):
    return get_db().edges.find_one(
        {"from_id": from_id, "to_id": to_id, "label": label}, {"_id": 1}
    ) is not None

def next_node_id(label):
    count = get_db().nodes.count_documents({})
    return "n" + str(count + 1) + "_" + re.sub(r"\W+", "", label)[:12]

def next_edge_id():
    count = get_db().edges.count_documents({})
    return "e" + str(count + 1)

def clear_all():
    get_db().nodes.delete_many({})
    get_db().edges.delete_many({})

def edge_key_exists(from_id, to_id, label):
    return get_db().edges.find_one(
        {"from_id": from_id, "to_id": to_id, "label": label}, {"_id": 1}
    ) is not None

# ── Migration from SQLite graph.db ───────────────────────────────────────────

def migrate_json_if_needed():
    """Migrate from old graph_db.json or graph.db (SQLite) if MongoDB is empty."""
    if get_db().nodes.count_documents({}) > 0:
        return  # already has data

    # try JSON first
    json_path = os.path.join(os.path.dirname(__file__), "graph_db.json")
    if os.path.exists(json_path):
        import json
        with open(json_path) as f:
            old = json.load(f)
        for nid, ndata in old.get("nodes", {}).items():
            insert_node(nid, ndata["label"], ndata.get("type","Node"), ndata.get("properties",{}))
        for e in old.get("edges", []):
            insert_edge(e["id"], e["from"], e["to"], e["label"], e.get("properties",{}))
        print(f"Migrated from graph_db.json → {get_db().nodes.count_documents({})} nodes")
        return

    # try SQLite
    sqlite_path = os.path.join(os.path.dirname(__file__), "graph.db")
    if os.path.exists(sqlite_path):
        import sqlite3
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("SELECT * FROM nodes"):
            import json
            insert_node(row["id"], row["label"], row["type"], json.loads(row["properties"]))
        for row in conn.execute("SELECT * FROM edges"):
            import json
            insert_edge(row["id"], row["from_id"], row["to_id"], row["label"], json.loads(row["properties"]))
        conn.close()
        print(f"Migrated from graph.db (SQLite) → {get_db().nodes.count_documents({})} nodes")
