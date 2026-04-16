"""
extractor.py - spaCy NLP-based PDF → graph extractor
Used as fallback when Groq API is unavailable or rate-limited.
"""
import re
import pdfplumber

def _clean(t):
    t = re.sub(r"\(cid:\d+\)", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def _safe_id(text):
    s = re.sub(r"[^a-zA-Z0-9_]", "_", text.strip())
    s = re.sub(r"_+", "_", s).strip("_")
    if not s: s = "entity"
    if s[0].isdigit(): s = "e_" + s
    return s[:60]

# spaCy NER label → graph node type
NER_TYPE_MAP = {
    "PERSON":   "Person",
    "ORG":      "Organization",
    "GPE":      "Location",
    "LOC":      "Location",
    "PRODUCT":  "Technology",
    "EVENT":    "Event",
    "WORK_OF_ART": "Concept",
    "LAW":      "Concept",
    "LANGUAGE": "Technology",
    "NORP":     "Organization",
    "FAC":      "Location",
    "DATE":     "Concept",
    "MONEY":    "Concept",
    "PERCENT":  "Concept",
    "QUANTITY": "Concept",
    "CARDINAL": "Concept",
    "ORDINAL":  "Concept",
}

# Technology keywords to tag as Technology type
TECH_KEYWORDS = {
    "python","java","javascript","typescript","react","angular","vue","node",
    "flask","django","fastapi","mongodb","postgresql","mysql","redis","docker",
    "kubernetes","aws","azure","gcp","tensorflow","pytorch","spacy","bert",
    "gpt","llm","nlp","ml","ai","api","rest","graphql","sql","nosql","html",
    "css","git","github","linux","windows","transformer","neural","network",
    "deep learning","machine learning","natural language"
}

STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "by","from","is","are","was","were","be","been","being","have","has",
    "had","do","does","did","will","would","could","should","may","might",
    "this","that","these","those","it","its","we","our","they","their",
    "he","she","his","her","as","if","then","than","so","yet","both",
    "not","no","nor","can","also","just","more","about","into","through",
    "during","before","after","above","below","between","each","other",
    "such","when","where","which","who","whom","how","all","any","both",
    "few","more","most","other","some","such","only","own","same","too",
    "very","s","t","can","will","just","don","should","now","i","you"
}


def _load_spacy():
    """Load spaCy model — tries large, medium, then small."""
    import spacy
    for model in ["en_core_web_lg", "en_core_web_md", "en_core_web_sm"]:
        try:
            return spacy.load(model)
        except OSError:
            continue
    raise RuntimeError(
        "No spaCy model found. Run: python -m spacy download en_core_web_sm"
    )


def _extract_text(pdf_path, max_pages=15):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:max_pages]:
            t = page.extract_text()
            if t:
                pages.append(re.sub(r"\(cid:\d+\)", " ", t))
    return "\n".join(pages)


def extract_graph(pdf_path):
    text = _extract_text(pdf_path)[:40_000]

    if not text.strip():
        return {"nodes": [], "edges": [], "stats": {"nodes": 0, "edges": 0}, "method": "spacy"}

    try:
        nlp = _load_spacy()
    except RuntimeError:
        # last resort: regex fallback
        return _regex_fallback(text)

    doc = nlp(text)

    nodes = {}
    edges = []
    seen_edges = set()

    def add_node(name, ntype="Concept"):
        name = _clean(name)
        if not name or len(name) < 2 or len(name) > 80:
            return None
        words = name.lower().split()
        if all(w in STOPWORDS for w in words):
            return None
        # override type if it looks like a technology
        if name.lower() in TECH_KEYWORDS or any(k in name.lower() for k in TECH_KEYWORDS):
            ntype = "Technology"
        nid = _safe_id(name)
        if nid and nid not in nodes:
            nodes[nid] = {"id": nid, "label": name, "type": ntype}
        return nid

    # ── Named Entity Recognition ──────────────────────────────────────────────
    for ent in doc.ents:
        ntype = NER_TYPE_MAP.get(ent.label_, "Concept")
        add_node(ent.text, ntype)

    # ── SVO (Subject-Verb-Object) triple extraction ───────────────────────────
    for sent in doc.sents:
        for token in sent:
            if token.pos_ != "VERB":
                continue
            subjects = [c for c in token.children if c.dep_ in ("nsubj", "nsubjpass")]
            objects  = [c for c in token.children if c.dep_ in ("dobj", "attr", "pobj", "iobj")]
            for subj in subjects:
                for obj in objects:
                    s_text = _clean(subj.text)
                    o_text = _clean(obj.text)
                    sid = _safe_id(s_text)
                    oid = _safe_id(o_text)
                    if sid in nodes and oid in nodes and sid != oid:
                        rel = token.lemma_.upper()
                        key = (sid, oid, rel)
                        if key not in seen_edges:
                            seen_edges.add(key)
                            edges.append({"from": sid, "to": oid, "label": rel})

    # ── Co-occurrence: entities in same sentence ──────────────────────────────
    for sent in doc.sents:
        ents_in_sent = [
            _safe_id(_clean(e.text))
            for e in sent.ents
            if _safe_id(_clean(e.text)) in nodes
        ]
        for i in range(len(ents_in_sent) - 1):
            s, o = ents_in_sent[i], ents_in_sent[i + 1]
            if s != o:
                key = (s, o, "RELATED_TO")
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({"from": s, "to": o, "label": "RELATED_TO"})

    edge_list = edges[:500]
    used = {e["from"] for e in edge_list} | {e["to"] for e in edge_list}
    node_list = [n for n in nodes.values() if n["id"] in used]
    if len(node_list) < 5:
        node_list = list(nodes.values())[:50]

    return {
        "nodes": node_list,
        "edges": edge_list,
        "stats": {"nodes": len(node_list), "edges": len(edge_list)},
        "method": "spacy",
    }


# ── Pure regex fallback (no spaCy) ────────────────────────────────────────────

PATTERNS = {
    "Person":       r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )*[A-Z][a-z]+)\b',
    "Organization": r'\b([A-Z][A-Za-z&\s]{2,30}(?:University|Institute|College|Corp|Inc|Ltd|Lab|Center|Centre|School|Department|Ministry|Agency|Foundation|Association|Society|Group|Team))\b',
    "Technology":   r'\b(Python|Java|JavaScript|TypeScript|React|Angular|Vue|Node\.js|Flask|Django|FastAPI|MongoDB|PostgreSQL|MySQL|Redis|Docker|Kubernetes|AWS|Azure|GCP|TensorFlow|PyTorch|spaCy|BERT|GPT|LLM|NLP|ML|AI|API|REST|GraphQL|SQL|NoSQL|HTML|CSS|Git|GitHub|Linux|Windows)\b',
    "Concept":      r'\b([A-Z][a-z]{3,}(?:\s[A-Z][a-z]{3,}){0,2})\b',
}

def _regex_fallback(text):
    nodes = {}
    edges = []
    seen_edges = set()

    def add_node(name, ntype="Concept"):
        nid = _safe_id(name)
        if nid and nid not in nodes and len(name) > 2:
            nodes[nid] = {"id": nid, "label": name, "type": ntype}
        return nid

    for ntype, pattern in PATTERNS.items():
        for match in re.finditer(pattern, text):
            name = _clean(match.group(1))
            words = name.lower().split()
            if any(w in STOPWORDS for w in words): continue
            if 2 < len(name) < 60:
                add_node(name, ntype)

    sentences = re.split(r'[.!?\n]', text)
    for sent in sentences[:300]:
        sent = _clean(sent)
        if len(sent) < 10: continue
        caps = re.findall(r'\b([A-Z][a-zA-Z]{2,}(?:\s[A-Z][a-zA-Z]{2,})?)\b', sent)
        caps = [c for c in caps if c.lower() not in STOPWORDS]
        for i in range(len(caps) - 1):
            s, o = caps[i], caps[i+1]
            if s == o: continue
            sid, oid = _safe_id(s), _safe_id(o)
            if sid in nodes and oid in nodes:
                key = (sid, oid, "RELATED_TO")
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({"from": sid, "to": oid, "label": "RELATED_TO"})

    edge_list = edges[:500]
    used = {e["from"] for e in edge_list} | {e["to"] for e in edge_list}
    node_list = [n for n in nodes.values() if n["id"] in used]
    if len(node_list) < 5:
        node_list = list(nodes.values())[:50]

    return {
        "nodes": node_list,
        "edges": edge_list,
        "stats": {"nodes": len(node_list), "edges": len(edge_list)},
        "method": "regex",
    }
