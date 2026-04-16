from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
import datetime, math

W, H = A4

# ── Colors ────────────────────────────────────────────────────────────────────
C_BG     = colors.HexColor("#080c14")
C_PANEL  = colors.HexColor("#0d1220")
C_CARD   = colors.HexColor("#111827")
C_ACCENT = colors.HexColor("#00e5b8")
C_ACCENT2= colors.HexColor("#818cf8")
C_YELLOW = colors.HexColor("#fbbf24")
C_RED    = colors.HexColor("#f87171")
C_GREEN  = colors.HexColor("#34d399")
C_ORANGE = colors.HexColor("#fb923c")
C_PINK   = colors.HexColor("#f472b6")
C_MUTED  = colors.HexColor("#64748b")
C_TEXT   = colors.HexColor("#1e293b")
C_WHITE  = colors.white
C_BORDER = colors.HexColor("#1e2d45")
C_LIGHT  = colors.HexColor("#f1f5fb")
C_LIGHT2 = colors.HexColor("#e8eef8")

# ── Styles ────────────────────────────────────────────────────────────────────
def S(name, **kw): return ParagraphStyle(name, **kw)

sTitle   = S("T",  fontSize=30, textColor=C_ACCENT,  alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=8)
sSub     = S("Su", fontSize=13, textColor=C_MUTED,   alignment=TA_CENTER, fontName="Helvetica",      spaceAfter=4)
sH1      = S("H1", fontSize=17, textColor=C_ACCENT,  fontName="Helvetica-Bold", spaceBefore=20, spaceAfter=8)
sH2      = S("H2", fontSize=13, textColor=C_ACCENT2, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
sH3      = S("H3", fontSize=11, textColor=C_TEXT,    fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
sBody    = S("B",  fontSize=9.5,textColor=C_TEXT,    fontName="Helvetica",      spaceAfter=5, leading=15, alignment=TA_JUSTIFY)
sCode    = S("C",  fontSize=7.8,textColor=colors.HexColor("#1e3a5f"), fontName="Courier",
             backColor=colors.HexColor("#eef4ff"), borderPad=7, spaceAfter=7, leading=12)
sCodeCmt = S("CC", fontSize=7.8,textColor=colors.HexColor("#16a34a"), fontName="Courier-Oblique",
             backColor=colors.HexColor("#eef4ff"), borderPad=0, spaceAfter=0, leading=12)
sBullet  = S("Bu", fontSize=9.5,textColor=C_TEXT,    fontName="Helvetica", spaceAfter=3, leading=14, leftIndent=14)
sCaption = S("Ca", fontSize=8,  textColor=C_MUTED,   fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=10)
sTH      = S("TH", fontSize=9,  textColor=C_WHITE,   fontName="Helvetica-Bold", alignment=TA_CENTER)
sTD      = S("TD", fontSize=8.5,textColor=C_TEXT,    fontName="Helvetica", leading=12)
sTDcode  = S("TC", fontSize=8,  textColor=colors.HexColor("#1e3a5f"), fontName="Courier", leading=11)

def HR(c=C_ACCENT, t=1.5): return HRFlowable(width="100%", thickness=t, color=c, spaceAfter=8, spaceBefore=4)
def SP(h=8): return Spacer(1, h)
def P(txt, st=None): return Paragraph(txt, st or sBody)
def B(txt): return Paragraph(f"• &nbsp;{txt}", sBullet)
def H1(t): return P(t, sH1)
def H2(t): return P(t, sH2)
def H3(t): return P(t, sH3)

def code_block(lines):
    """Render a code block with line-by-line coloring."""
    items = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            items.append(P(line.replace(" ","&nbsp;").replace("<","&lt;"), sCodeCmt))
        else:
            items.append(P(line.replace(" ","&nbsp;").replace("<","&lt;"), sCode))
    return items

def tbl(data, widths, hdr=1, alt=True):
    t = Table(data, colWidths=widths)
    style = [
        ("BACKGROUND",(0,0),(-1,hdr-1), C_PANEL),
        ("TEXTCOLOR",  (0,0),(-1,hdr-1), C_WHITE),
        ("FONTNAME",   (0,0),(-1,hdr-1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0),(-1,hdr-1), 9),
        ("ALIGN",      (0,0),(-1,-1), "LEFT"),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("GRID",       (0,0),(-1,-1), 0.4, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1), 8),
        ("FONTSIZE",   (0,hdr),(-1,-1), 8.5),
    ]
    if alt:
        style.append(("ROWBACKGROUNDS",(0,hdr),(-1,-1),[C_LIGHT, C_WHITE]))
    t.setStyle(TableStyle(style))
    return t

# ── Diagrams ──────────────────────────────────────────────────────────────────
class ArchDiagram(Flowable):
    def __init__(self, w=500, h=200): self.w,self.h=w,h
    def wrap(self,*a): return self.w,self.h
    def draw(self):
        c=self.canv
        def box(x,y,w,h,col,lines,small=False):
            c.setFillColor(col); c.setStrokeColor(C_WHITE)
            c.roundRect(x,y,w,h,8,fill=1,stroke=1)
            c.setFillColor(C_WHITE)
            fs=7 if small else 8
            c.setFont("Helvetica-Bold",fs)
            for i,l in enumerate(lines):
                c.drawCentredString(x+w/2, y+h-14-i*11, l)
        def arrow(x1,y1,x2,y2,lbl=""):
            c.setStrokeColor(C_MUTED); c.setFillColor(C_MUTED); c.setLineWidth(1.2)
            c.line(x1,y1,x2,y2)
            dx,dy=x2-x1,y2-y1; L=math.sqrt(dx*dx+dy*dy) or 1
            ux,uy=dx/L,dy/L; ax,ay=x2-ux*8,y2-uy*8
            p=c.beginPath(); p.moveTo(x2,y2); p.lineTo(ax-uy*4,ay+ux*4); p.lineTo(ax+uy*4,ay-ux*4); p.close()
            c.drawPath(p,fill=1)
            if lbl:
                c.setFont("Helvetica",6.5); c.setFillColor(C_TEXT)
                c.drawCentredString((x1+x2)/2+8,(y1+y2)/2+4,lbl)
        # boxes
        box(10, 75,110,55,C_ACCENT2,["Browser","vis-network","HTML/JS"])
        box(170,75,110,55,C_ACCENT, ["Flask","Backend","app.py"])
        box(330,75,110,55,C_YELLOW, ["MongoDB","Atlas","Cloud DB"])
        box(170,10,110,40,C_ORANGE, ["Groq LLM","llama-3.3-70b"])
        box(330,10,110,40,C_RED,    ["spaCy NLP","Fallback"])
        box(170,155,110,35,C_GREEN, ["SQLite","Fallback DB"])
        # arrows
        arrow(120,102,170,102,"REST API")
        arrow(280,102,330,102,"PyMongo")
        arrow(225,75,225,50,"AI Query")
        arrow(280,30,330,30,"NLP Fallback")
        arrow(225,130,225,155,"DB Fallback")

class FlowDiagram(Flowable):
    def __init__(self,steps,colors_list,w=500,h=70):
        self.steps=steps; self.cols=colors_list; self.w=w; self.h=h
    def wrap(self,*a): return self.w,self.h
    def draw(self):
        c=self.canv; n=len(self.steps)
        bw=min(78,(self.w-10*(n-1))/n); gap=(self.w-bw*n)/(n-1) if n>1 else 0
        for i,(lbl,col) in enumerate(zip(self.steps,self.cols)):
            x=i*(bw+gap); y=8
            c.setFillColor(col); c.setStrokeColor(C_WHITE)
            c.roundRect(x,y,bw,self.h-16,7,fill=1,stroke=1)
            c.setFillColor(C_WHITE); c.setFont("Helvetica-Bold",7)
            lines=lbl.split("\n")
            for j,l in enumerate(lines):
                c.drawCentredString(x+bw/2,y+self.h-24-j*10,l)
            if i<n-1:
                ax1=x+bw+2; ay=y+(self.h-16)/2; ax2=x+bw+gap-2
                c.setStrokeColor(C_MUTED); c.setFillColor(C_MUTED); c.setLineWidth(1.5)
                c.line(ax1,ay,ax2,ay)
                p=c.beginPath(); p.moveTo(ax2,ay); p.lineTo(ax2-6,ay-4); p.lineTo(ax2-6,ay+4); p.close()
                c.drawPath(p,fill=1)

class DBDiagram(Flowable):
    def __init__(self,w=500,h=170): self.w,self.h=w,h
    def wrap(self,*a): return self.w,self.h
    def draw(self):
        c=self.canv
        def draw_tbl(x,y,title,fields,col):
            tw,rh=200,18
            c.setFillColor(col); c.roundRect(x,y,tw,22,4,fill=1,stroke=0)
            c.setFillColor(C_WHITE); c.setFont("Helvetica-Bold",9)
            c.drawCentredString(x+tw/2,y+7,title)
            for i,(fn,ft,pk) in enumerate(fields):
                fy=y-(i+1)*rh
                c.setFillColor(C_LIGHT if i%2==0 else C_WHITE)
                c.rect(x,fy,tw,rh,fill=1,stroke=0)
                c.setStrokeColor(colors.HexColor("#cbd5e1")); c.setLineWidth(0.4)
                c.rect(x,fy,tw,rh,fill=0,stroke=1)
                c.setFillColor(col if pk else C_TEXT)
                c.setFont("Helvetica-Bold" if pk else "Helvetica",8)
                c.drawString(x+6,fy+5,fn)
                c.setFillColor(C_MUTED); c.setFont("Helvetica",7.5)
                c.drawRightString(x+tw-6,fy+5,ft)
            c.setStrokeColor(colors.HexColor("#94a3b8")); c.setLineWidth(1)
            c.rect(x,y-len(fields)*rh,tw,len(fields)*rh,fill=0,stroke=1)
        nf=[("_id","ObjectId (auto)",False),("id","String — unique",True),
            ("label","String",False),("type","String",False),("properties","Object {}",False)]
        ef=[("_id","ObjectId (auto)",False),("id","String — unique",True),
            ("from_id","→ nodes.id",True),("to_id","→ nodes.id",True),
            ("label","String",False),("properties","Object {}",False)]
        draw_tbl(20, self.h-10,"nodes",nf,C_ACCENT)
        draw_tbl(280,self.h-10,"edges",ef,C_ACCENT2)
        c.setStrokeColor(C_MUTED); c.setLineWidth(1.2)
        for ay in [self.h-55,self.h-73]:
            c.line(220,ay,280,ay)
            p=c.beginPath(); p.moveTo(280,ay); p.lineTo(274,ay-4); p.lineTo(274,ay+4); p.close()
            c.setFillColor(C_MUTED); c.drawPath(p,fill=1)
        c.setFont("Helvetica",7); c.setFillColor(C_MUTED)
        c.drawCentredString(250,self.h-50,"from_id")
        c.drawCentredString(250,self.h-68,"to_id")

# ── Cover ─────────────────────────────────────────────────────────────────────
def cover():
    e=[]
    e.append(SP(50))
    d=Drawing(500,130)
    d.add(Rect(0,0,500,130,fillColor=C_PANEL,strokeColor=C_ACCENT,strokeWidth=2,rx=14,ry=14))
    d.add(String(250,95,"Knowledge Graph Studio",fontSize=28,fillColor=C_ACCENT,fontName="Helvetica-Bold",textAnchor="middle"))
    d.add(String(250,68,"Complete Project Report",fontSize=16,fillColor=C_ACCENT2,fontName="Helvetica",textAnchor="middle"))
    d.add(String(250,44,"Code Explanation · Data Flow · Database Schema · Architecture",fontSize=9,fillColor=C_MUTED,fontName="Helvetica",textAnchor="middle"))
    d.add(String(250,22,"AI-Powered Research Knowledge Graph Builder",fontSize=9,fillColor=C_MUTED,fontName="Helvetica-Oblique",textAnchor="middle"))
    e.append(d); e.append(SP(28))
    info=[["Project","Knowledge Graph Studio"],["Version","2.0 — AI Enhanced"],
          ["Backend","Python 3.11 + Flask"],["Database","MongoDB Atlas + SQLite Fallback"],
          ["AI Model","Groq llama-3.3-70b-versatile"],["NLP Fallback","spaCy en_core_web_sm"],
          ["Frontend","HTML5 + CSS3 + vis-network"],["Date",datetime.date.today().strftime("%B %d, %Y")]]
    rows=[[P(f"<b>{k}</b>",S("k",fontSize=9,fontName="Helvetica-Bold",textColor=C_ACCENT2)),
           P(v,S("v",fontSize=9,fontName="Helvetica",textColor=C_TEXT))] for k,v in info]
    e.append(tbl(rows,[130,280],hdr=0,alt=True))
    e.append(PageBreak())
    return e

# ── TOC ───────────────────────────────────────────────────────────────────────
def toc():
    e=[]
    e.append(H1("Table of Contents")); e.append(HR())
    items=[("1","Project Overview & Features","3"),
           ("2","Technology Stack","4"),
           ("3","System Architecture","5"),
           ("4","Complete Program Flow","6"),
           ("5","File: app.py — Line by Line","7"),
           ("6","File: database.py — Line by Line","9"),
           ("7","File: ai_extractor.py — Line by Line","11"),
           ("8","File: nl_query.py — Line by Line","13"),
           ("9","File: extractor.py — Line by Line","14"),
           ("10","File: query_engine.py — Line by Line","15"),
           ("11","File: owl_parser.py — Line by Line","17"),
           ("12","File: processor.py — Line by Line","18"),
           ("13","Database Schema — How Data is Stored","19"),
           ("14","REST API Reference","21"),
           ("15","Frontend Architecture","22"),
           ("16","Interview Q&A","23")]
    rows=[[P(f"<b>{n}.</b>",S("n",fontSize=9,fontName="Helvetica-Bold",textColor=C_ACCENT2)),
           P(t,S("t",fontSize=9,fontName="Helvetica",textColor=C_TEXT)),
           P(pg,S("p",fontSize=9,fontName="Helvetica",textColor=C_MUTED,alignment=TA_CENTER))]
          for n,t,pg in items]
    e.append(tbl(rows,[30,340,50],hdr=0,alt=True))
    e.append(PageBreak())
    return e

# ── Section 1: Overview ───────────────────────────────────────────────────────
def s1_overview():
    e=[]
    e.append(H1("1. Project Overview & Features")); e.append(HR())
    e.append(P("Knowledge Graph Studio is a full-stack web application that transforms research papers (PDFs) into interactive, queryable knowledge graphs. It uses AI (Groq LLM) to extract entities and relationships, stores them in MongoDB Atlas, and visualizes them as a force-directed graph in the browser."))
    e.append(SP(8)); e.append(H2("What is a Knowledge Graph?"))
    e.append(P("A knowledge graph is a network where nodes represent real-world entities (people, organizations, concepts) and edges represent relationships between them. Example:"))
    e.append(P("<b>Albert Einstein</b> → <i>DEVELOPED</i> → <b>Theory of Relativity</b> → <i>INFLUENCED</i> → <b>Modern Physics</b>",S("ex",fontSize=9,fontName="Helvetica",textColor=C_ACCENT2,leftIndent=20,spaceAfter=8)))
    e.append(H2("Key Features"))
    feats=[("📄 AI PDF Extraction","Upload research papers — Groq LLM extracts entities and relationships automatically"),
           ("🔀 Multi-PDF Fusion","Upload multiple papers at once — all graphs merge into one unified knowledge graph"),
           ("🤖 Natural Language Query","Ask plain English questions — AI answers and highlights relevant nodes"),
           ("⌕ Cypher-like Queries","MATCH, PATH, NEIGHBORS, STATS — query the graph like Neo4j"),
           ("🦉 OWL/RDF-XML Import","Import ontologies from OWL files directly into the graph"),
           ("☁ MongoDB Atlas","Cloud persistence — data accessible from anywhere"),
           ("🔄 SQLite Fallback","Works offline automatically if MongoDB is unavailable"),
           ("🎨 Dark/Light Theme","Toggle between dark and light UI modes")]
    rows=[[P(i,S("i",fontSize=9,fontName="Helvetica",textColor=C_ACCENT)),
           P(d,S("d",fontSize=9,fontName="Helvetica",textColor=C_TEXT))] for i,d in feats]
    e.append(tbl([[P("<b>Feature</b>",sTH),P("<b>Description</b>",sTH)]]+rows,[80,360]))
    e.append(PageBreak())
    return e

# ── Section 2: Tech Stack ─────────────────────────────────────────────────────
def s2_tech():
    e=[]
    e.append(H1("2. Technology Stack")); e.append(HR())
    e.append(H2("Backend"))
    rows=[[P("<b>Technology</b>",sTH),P("<b>Version</b>",sTH),P("<b>Purpose</b>",sTH)],
          ["Python","3.11","Core runtime — 3.14 has TLS incompatibility with MongoDB Atlas"],
          ["Flask","3.x","Web framework — handles all HTTP routes and API endpoints"],
          ["PyMongo","4.x","MongoDB driver — connects to Atlas cloud database"],
          ["spaCy","3.8","NLP — Named Entity Recognition + dependency parsing (fallback)"],
          ["pdfplumber","0.11","PDF text extraction — handles multi-page documents"],
          ["Groq SDK","latest","LLM API client — calls llama-3.3-70b for AI extraction"],
          ["owlready2","0.50","OWL ontology processing and RDF/XML generation"],
          ["networkx","3.x","Graph algorithms — BFS shortest path calculation"],
          ["python-dotenv","1.x","Loads .env file — keeps API keys out of code"],
          ["Werkzeug","3.x","Secure file upload handling — prevents path traversal"]]
    e.append(tbl(rows,[90,60,290]))
    e.append(SP(10)); e.append(H2("Frontend & Database"))
    rows2=[[P("<b>Technology</b>",sTH),P("<b>Purpose</b>",sTH)],
           ["HTML5 / CSS3 / Vanilla JS","Single-page application — no build tools needed"],
           ["vis-network (CDN)","Interactive graph visualization with physics simulation"],
           ["MongoDB Atlas (Free M0)","Primary cloud database — stores all nodes and edges"],
           ["SQLite (graph.db)","Local fallback database — works without internet"],
           ["Groq API (Free tier)","llama-3.3-70b — PDF extraction + NL query answering"]]
    e.append(tbl(rows2,[180,260]))
    e.append(PageBreak())
    return e

# ── Section 3: Architecture ───────────────────────────────────────────────────
def s3_arch():
    e=[]
    e.append(H1("3. System Architecture")); e.append(HR())
    e.append(P("The application uses a three-tier architecture: browser frontend, Python/Flask backend, and cloud database. The AI layer (Groq) enhances extraction and querying capabilities."))
    e.append(SP(10)); e.append(ArchDiagram(500,200))
    e.append(P("Figure 1: System Architecture — all components and their connections",sCaption))
    e.append(SP(8)); e.append(H2("Project File Structure"))
    rows=[[P("<b>File</b>",sTH),P("<b>Role</b>",sTH),P("<b>Size</b>",sTH)],
          ["app.py","Flask web server — all REST API routes","~160 lines"],
          ["database.py","MongoDB/SQLite abstraction layer","~180 lines"],
          ["ai_extractor.py","LLM-powered PDF → knowledge graph","~100 lines"],
          ["nl_query.py","Natural language question answering","~90 lines"],
          ["extractor.py","spaCy NLP fallback extractor","~80 lines"],
          ["query_engine.py","Cypher-like query language engine","~400 lines"],
          ["owl_parser.py","OWL/RDF-XML → graph JSON parser","~100 lines"],
          ["processor.py","PDF → OWL ontology (owlready2)","~150 lines"],
          ["templates/index.html","Complete frontend SPA","~1100 lines"],
          [".env","API keys and DB credentials (not in git)","3 lines"]]
    e.append(tbl(rows,[130,260,60]))
    e.append(PageBreak())
    return e

# ── Section 4: Program Flow ───────────────────────────────────────────────────
def s4_flow():
    e=[]
    e.append(H1("4. Complete Program Flow")); e.append(HR())
    e.append(H2("4.1  Application Startup"))
    e.append(P("When you run <b>py -3.11 app.py</b>, this sequence happens:"))
    for line in ["py -3.11 app.py",
                 "  ├── load_dotenv()            # reads .env → MONGO_URI, GROQ_API_KEY into os.environ",
                 "  ├── init_db()                # tries MongoDB Atlas → creates indexes",
                 "  │     └── if fails → SQLite  # creates graph.db with nodes+edges tables",
                 "  ├── migrate_json_if_needed()  # imports old graph_db.json if it exists",
                 "  └── Flask starts on :5000     # ready to accept browser requests"]:
        e.append(P(line.replace(" ","&nbsp;"),sCode))
    e.append(SP(8)); e.append(H2("4.2  PDF Upload & AI Extraction Flow"))
    steps=["PDF\nUpload","Text\nExtract","Chunk\nText","Groq\nLLM","Parse\nJSON","Save to\nMongoDB"]
    cols=[C_ACCENT2,C_ACCENT,C_YELLOW,C_ORANGE,C_PINK,C_GREEN]
    e.append(FlowDiagram(steps,cols,500,72))
    e.append(P("Figure 2: PDF to Knowledge Graph — 6-step AI extraction pipeline",sCaption))
    for line in ["POST /upload",
                 "  ├── secure_filename() → save PDF to /uploads/",
                 "  ├── ai_extractor.extract_graph_ai(path)",
                 "  │     ├── pdfplumber.open() → extract text from all pages",
                 "  │     ├── split text into 3000-char chunks (max 10 chunks)",
                 "  │     └── for each chunk:",
                 "  │           ├── Groq API call → llama-3.3-70b",
                 "  │           ├── returns JSON: {entities:[...], relations:[...]}",
                 "  │           └── deduplicate + merge into all_entities, all_relations",
                 "  │     [if Groq fails → fallback to spaCy NER + SVO parsing]",
                 "  ├── for each entity  → insert_node() → MongoDB nodes collection",
                 "  ├── for each relation → insert_edge() → MongoDB edges collection",
                 "  └── return {graph, stats, method} → browser renders graph"]:
        e.append(P(line.replace(" ","&nbsp;"),sCode))
    e.append(SP(8)); e.append(H2("4.3  Natural Language Query Flow"))
    steps2=["User\nQuestion","Load\nGraph","Build\nSummary","Groq\nLLM","Parse\nAnswer","Highlight\nNodes"]
    e.append(FlowDiagram(steps2,cols,500,72))
    e.append(P("Figure 3: Natural Language Query — question to highlighted graph nodes",sCaption))
    for line in ["POST /ask",
                 "  ├── load_db() → fetch all nodes+edges from MongoDB",
                 "  ├── _build_graph_summary() → compact text (max 150 nodes, 150 edges)",
                 "  ├── Groq API: question + graph summary → llama-3.3-70b",
                 "  ├── returns: {answer, relevant_node_ids, confidence}",
                 "  ├── validate node IDs exist in DB",
                 "  └── return answer + IDs → frontend dims other nodes, zooms to relevant"]:
        e.append(P(line.replace(" ","&nbsp;"),sCode))
    e.append(SP(8)); e.append(H2("4.4  Manual CRUD Flow"))
    for line in ["POST /node  → validate label → next_node_id() → insert_node() → return graph",
                 "PUT  /node/<id> → load_db() → update_node() → return graph",
                 "DELETE /node/<id> → delete_node() + delete all connected edges → return graph",
                 "POST /edge  → check both nodes exist → next_edge_id() → insert_edge() → return graph"]:
        e.append(P(line.replace(" ","&nbsp;"),sCode))
    e.append(PageBreak())
    return e

# ── Section 5: app.py ─────────────────────────────────────────────────────────
def s5_app():
    e=[]
    e.append(H1("5. File: app.py — Line by Line")); e.append(HR())
    e.append(P("app.py is the entry point and web server. It defines all HTTP routes and connects every module together."))
    blocks=[
        ("Lines 1-5: Imports",
         "from flask import Flask, request, jsonify, render_template\nfrom werkzeug.utils import secure_filename\nfrom dotenv import load_dotenv\nload_dotenv()",
         "Flask provides the web framework. secure_filename() sanitizes uploaded filenames to prevent path traversal attacks (e.g. ../../etc/passwd). load_dotenv() reads the .env file and puts MONGO_URI and GROQ_API_KEY into os.environ before anything else runs."),
        ("Lines 6-11: Import database functions",
         "from database import (\n    init_db, migrate_json_if_needed, load_db, db_to_vis,\n    insert_node, update_node, delete_node, node_exists,\n    insert_edge, delete_edge, edge_key_exists,\n    next_node_id, next_edge_id, clear_all\n)",
         "All database operations are imported from database.py. app.py never talks to MongoDB or SQLite directly — it only calls these functions. This is the abstraction layer pattern."),
        ("Lines 13-16: App setup",
         "app = Flask(__name__)\nUPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')\nos.makedirs(UPLOAD_FOLDER, exist_ok=True)\napp.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024",
         "Creates the Flask app. Sets upload folder to uploads/ next to app.py. makedirs creates it if missing. MAX_CONTENT_LENGTH limits uploads to 50MB — prevents memory exhaustion attacks."),
        ("Lines 19-20: Startup",
         "init_db()\nmigrate_json_if_needed()",
         "Runs once when app starts. init_db() connects to MongoDB and creates indexes (or initializes SQLite). migrate_json_if_needed() imports any old graph_db.json data if that file exists."),
        ("GET /  →  index()",
         "@app.route('/')\ndef index():\n    return render_template('index.html')",
         "When browser opens localhost:5000, Flask reads templates/index.html and sends it. This is the entire frontend — one HTML file with all CSS and JS inside."),
        ("GET /graph  →  get_graph()",
         "@app.route('/graph', methods=['GET'])\ndef get_graph():\n    return jsonify(db_to_vis())",
         "Called by the browser on page load and after every change. db_to_vis() fetches all nodes and edges from MongoDB and formats them for vis-network: {nodes:[...], edges:[...]}. The ?t=timestamp query param prevents browser caching."),
        ("POST /node  →  add_node()",
         "label = data.get('label','').strip()\nnid = next_node_id(label)      # e.g. 'n5_JohnSmith'\nwhile node_exists(nid):         # ensure uniqueness\n    nid += '_'\ninsert_node(nid, label, ntype, props)\nreturn jsonify({'id': nid, 'graph': db_to_vis()})",
         "Creates a new node. next_node_id() generates 'n{count}_{label}' — the count prefix ensures uniqueness, the label suffix makes it human-readable. The while loop handles rare collisions. Returns the full updated graph so the browser re-renders immediately."),
        ("DELETE /node/<nid>  →  delete_node_route()",
         "@app.route('/node/<nid>', methods=['DELETE'])\ndef delete_node_route(nid):\n    if not node_exists(nid):\n        return jsonify({'error': 'Node not found'}), 404\n    delete_node(nid)   # also deletes all connected edges\n    return jsonify({'graph': db_to_vis()})",
         "Deletes a node AND all its edges. The 404 check prevents silent failures. delete_node() in database.py uses MongoDB's $or operator to delete edges where from_id OR to_id matches — keeps the graph consistent."),
        ("POST /ask  →  ask()",
         "@app.route('/ask', methods=['POST'])\ndef ask():\n    from nl_query import answer_question\n    question = data.get('question','').strip()\n    result = answer_question(question, load_db())\n    return jsonify(result)",
         "AI natural language query. Imports nl_query lazily (only when needed). Loads the full graph from MongoDB, passes it with the question to Groq LLM, returns the answer + relevant node IDs for highlighting."),
        ("POST /upload  →  upload()",
         "file.save(path)\nfrom ai_extractor import extract_graph_ai\nresult = extract_graph_ai(path)\nfor n in result['nodes']:\n    if not node_exists(nid):\n        insert_node(...)\nfor e in result['edges']:\n    if not edge_key_exists(...):\n        insert_edge(...)",
         "Saves the PDF, runs AI extraction, then inserts only NEW nodes/edges. The node_exists() and edge_key_exists() checks prevent duplicates when the same PDF is uploaded twice. Returns stats (nodes/edges added) and the full updated graph."),
    ]
    for title, code, explanation in blocks:
        e.append(KeepTogether([
            H3(title),
            P(code.replace(" ","&nbsp;").replace("\n","<br/>"), sCode),
            P(f"<b>Explanation:</b> {explanation}"),
            SP(4)
        ]))
    e.append(PageBreak())
    return e

# ── Section 6: database.py ────────────────────────────────────────────────────
def s6_db():
    e=[]
    e.append(H1("6. File: database.py — Line by Line")); e.append(HR())
    e.append(P("database.py is the data access layer. It abstracts MongoDB and SQLite behind a single API so the rest of the code never needs to know which database is active."))
    blocks=[
        ("Module-level globals (singleton pattern)",
         "_client = None\n_db     = None\n_use_mongo = False",
         "These three variables are set once when the app starts and reused for every request. This is the singleton pattern — creating one database connection and sharing it, rather than reconnecting on every request (which would be very slow)."),
        ("get_db() — connection with fallback",
         "def get_db():\n    global _client, _db, _use_mongo\n    if _db is not None:\n        return _db          # already connected, reuse\n    _client = MongoClient(MONGO_URI,\n        serverSelectionTimeoutMS=10000,\n        tlsInsecure=True)   # bypass TLS cert validation\n    _client.admin.command('ping')  # test connection\n    _db = _client[DB_NAME]\n    _use_mongo = True",
         "tlsInsecure=True bypasses TLS certificate validation — needed because Python 3.11's OpenSSL is strict with MongoDB Atlas's TLS configuration. The ping command forces an actual connection test immediately so we know if MongoDB is reachable before any data operations."),
        ("Fallback to SQLite",
         "    except Exception as e:\n        print(f'MongoDB failed, falling back to SQLite')\n    _use_mongo = False\n    _db = 'sqlite'\n    return _db",
         "If MongoDB fails for ANY reason (network, wrong credentials, SSL error), the code silently falls back to SQLite. The string 'sqlite' is stored in _db as a sentinel value. _is_mongo() checks _use_mongo flag to decide which path to take."),
        ("init_db() — create indexes",
         "def init_db():\n    if _is_mongo():\n        _db.nodes.create_index('id', unique=True)\n        _db.edges.create_index('id', unique=True)\n        _db.edges.create_index([\n            ('from_id', ASCENDING),\n            ('to_id',   ASCENDING),\n            ('label',   ASCENDING)\n        ])",
         "Creates MongoDB indexes on startup. The unique index on nodes.id prevents duplicate nodes. The compound index on edges (from_id, to_id, label) makes edge_key_exists() fast and prevents duplicate relationships between the same pair of nodes."),
        ("insert_node() — upsert pattern",
         "def insert_node(nid, label, ntype, properties):\n    if _is_mongo():\n        _db.nodes.update_one(\n            {'id': nid},\n            {'$set': {'id':nid,'label':label,'type':ntype,'properties':properties}},\n            upsert=True\n        )",
         "upsert=True means: UPDATE if a document with this id exists, INSERT if not. This prevents duplicates when the same PDF is uploaded twice — the second upload just updates existing nodes rather than creating duplicates."),
        ("delete_node() — cascade delete",
         "def delete_node(nid):\n    if _is_mongo():\n        _db.nodes.delete_one({'id': nid})\n        _db.edges.delete_many({\n            '$or': [{'from_id': nid}, {'to_id': nid}]\n        })",
         "The $or operator deletes ALL edges where this node appears as either source (from_id) or target (to_id). This cascade delete keeps the graph consistent — no orphaned edges pointing to deleted nodes."),
        ("next_node_id() — ID generation",
         "def next_node_id(label):\n    count = _db.nodes.count_documents({})\n    return 'n' + str(count+1) + '_' + re.sub(r'\\W+','',label)[:12]",
         "Generates IDs like 'n5_JohnSmith'. The number prefix (count+1) ensures uniqueness even if two nodes have the same label. The label suffix (first 12 alphanumeric chars) makes IDs human-readable for debugging. re.sub removes special characters."),
        ("load_db() — fetch all data",
         "def load_db():\n    if _is_mongo():\n        nodes = {}\n        for doc in _db.nodes.find({}, {'_id': 0}):\n            nodes[doc['id']] = {'label':doc['label'],...}\n        edges = [{'id':d['id'],'from':d['from_id'],...}\n                 for d in _db.edges.find({}, {'_id': 0})]\n        return {'nodes': nodes, 'edges': edges}",
         "{'_id': 0} excludes MongoDB's internal _id field from results. Nodes are returned as a dict keyed by id for O(1) lookup. Edges are a list. This structure is used by the query engine, AI query, and visualization."),
    ]
    for title, code, explanation in blocks:
        e.append(KeepTogether([
            H3(title),
            P(code.replace(" ","&nbsp;").replace("\n","<br/>"), sCode),
            P(f"<b>Explanation:</b> {explanation}"),
            SP(4)
        ]))
    e.append(PageBreak())
    return e

# ── Section 7: ai_extractor.py ────────────────────────────────────────────────
def s7_ai():
    e=[]
    e.append(H1("7. File: ai_extractor.py — Line by Line")); e.append(HR())
    e.append(P("ai_extractor.py is the AI brain of the project. It reads PDFs, splits them into chunks, sends each chunk to Groq's LLM, and collects structured entity/relationship data."))
    blocks=[
        ("Constants",
         "CHUNK_SIZE = 3000   # characters per chunk\nMAX_CHUNKS = 10    # max chunks per PDF",
         "3000 chars is roughly 500 words — enough context for the LLM to understand relationships without exceeding token limits. MAX_CHUNKS=10 means max 30,000 chars (about 10 pages) processed per PDF, controlling API usage and cost."),
        ("SYSTEM_PROMPT — instructing the LLM",
         'SYSTEM_PROMPT = """You are a knowledge graph extraction expert.\nReturn ONLY valid JSON:\n{\n  "entities": [{"id":"snake_case","label":"Name","type":"Person|Org|..."}],\n  "relations": [{"from":"id","relation":"USES","to":"id"}]\n}"""',
         "The system prompt is the most important part. It tells the LLM exactly what format to return. temperature=0.1 makes output deterministic and factual (not creative). The strict JSON format requirement means we can reliably parse the response."),
        ("_chunk_text() — smart splitting",
         "def _chunk_text(text, size=CHUNK_SIZE):\n    sentences = re.split(r'(?<=[.!?])\\s+', text)\n    chunks, current = [], ''\n    for s in sentences:\n        if len(current) + len(s) > size and current:\n            chunks.append(current.strip())\n            current = s\n        else:\n            current += ' ' + s",
         "Splits on sentence boundaries (.!?) rather than arbitrary character positions. This keeps sentences intact so the LLM gets coherent context. A sentence is never cut in the middle, which would confuse the LLM about entity relationships."),
        ("extract_graph_ai() — main function",
         "def extract_graph_ai(pdf_path):\n    if not GROQ_API_KEY:\n        from extractor import extract_graph\n        return extract_graph(pdf_path)  # spaCy fallback\n    text = _extract_text(pdf_path)\n    chunks = _chunk_text(text)\n    all_entities = {}  # id -> node dict\n    all_relations = []\n    seen_edges = set()  # prevent duplicates",
         "If no API key is configured, silently falls back to spaCy. all_entities is a dict keyed by ID — this automatically deduplicates entities across chunks (same entity mentioned in chunk 1 and chunk 5 only appears once). seen_edges is a set of (from,to,relation) tuples to prevent duplicate edges."),
        ("Processing each chunk",
         "for i, chunk in enumerate(chunks):\n    try:\n        raw  = _call_groq(chunk)\n        data = _parse_llm_response(raw)\n        for ent in data.get('entities', []):\n            eid = _safe_id(ent.get('id') or ent.get('label',''))\n            if eid not in all_entities:  # deduplicate\n                all_entities[eid] = {...}\n    except Exception as e:\n        errors += 1\n        continue  # skip bad chunks, don't crash",
         "The try/except around each chunk means one bad LLM response doesn't crash the whole extraction. errors counter tracks failures. If ALL chunks fail, it falls back to spaCy. _safe_id() converts any text to valid snake_case ID."),
        ("Fallback logic",
         "if errors == len(chunks):\n    from extractor import extract_graph\n    result = extract_graph(pdf_path)\n    result['method'] = 'spacy_fallback'\n    return result",
         "Only falls back to spaCy if EVERY chunk failed. If even one chunk succeeded, we use the AI results. This ensures maximum AI coverage while guaranteeing the user always gets some result."),
    ]
    for title, code, explanation in blocks:
        e.append(KeepTogether([H3(title),P(code.replace(" ","&nbsp;").replace("\n","<br/>"),sCode),P(f"<b>Explanation:</b> {explanation}"),SP(4)]))
    e.append(PageBreak())
    return e

# ── Section 8: nl_query.py ────────────────────────────────────────────────────
def s8_nl():
    e=[]
    e.append(H1("8. File: nl_query.py — Line by Line")); e.append(HR())
    e.append(P("nl_query.py handles natural language questions about the graph. It sends the question + a compact graph summary to Groq LLM and returns a human-readable answer plus the IDs of relevant nodes."))
    blocks=[
        ("_build_graph_summary() — token management",
         "def _build_graph_summary(db):\n    node_items = list(nodes.items())[:150]  # max 150 nodes\n    edge_items  = edges[:150]               # max 150 edges\n    node_str = '\\n'.join(\n        f'{{\"id\":\"{nid}\",\"label\":\"{n[\"label\"]}\",\"type\":\"{n[\"type\"]}\"}}'\n        for nid, n in node_items\n    )",
         "Limits to 150 nodes and 150 edges to avoid exceeding the LLM's context window (token limit). The graph is serialized as compact JSON strings — no whitespace — to minimize token usage. Sending the full graph for large knowledge graphs would exceed limits and cost more."),
        ("answer_question() — main function",
         "resp = client.chat.completions.create(\n    model='llama-3.3-70b-versatile',\n    messages=[\n        {'role':'system','content':SYSTEM_PROMPT},\n        {'role':'user','content': f'Question: {question}\\n\\nGraph:\\n{graph_summary}'}\n    ],\n    temperature=0.1, max_tokens=1024\n)",
         "The user message contains both the question AND the graph data. The LLM reads the graph, finds relevant nodes, and answers the question. temperature=0.1 keeps answers factual and consistent."),
        ("Validating LLM response",
         "valid_nodes = [nid for nid in result.get('relevant_node_ids',[]) if nid in nodes]\nvalid_edges = [e['id'] for e in edges if e['id'] in result.get('relevant_edge_ids',[])]",
         "The LLM might hallucinate node IDs that don't exist. This validation filters out any IDs not present in the actual database. Only real, existing node IDs are returned to the frontend for highlighting."),
    ]
    for title, code, explanation in blocks:
        e.append(KeepTogether([H3(title),P(code.replace(" ","&nbsp;").replace("\n","<br/>"),sCode),P(f"<b>Explanation:</b> {explanation}"),SP(4)]))
    e.append(PageBreak())
    return e

# ── Section 9: extractor.py ───────────────────────────────────────────────────
def s9_ext():
    e=[]
    e.append(H1("9. File: extractor.py — Line by Line")); e.append(HR())
    e.append(P("extractor.py is the spaCy-based fallback extractor. It uses NLP (Natural Language Processing) to extract entities and relationships without needing an API key."))
    blocks=[
        ("Loading spaCy model",
         "try:\n    nlp = spacy.load('en_core_web_lg')  # best quality\nexcept OSError:\n    try:\n        nlp = spacy.load('en_core_web_md')  # medium\n    except OSError:\n        nlp = spacy.load('en_core_web_sm')  # minimum",
         "Tries to load the largest model first (best accuracy), falls back to smaller ones. This runs at import time — the model loads once into memory and is reused for all PDFs. Loading takes 1-2 seconds but subsequent uses are fast."),
        ("NER type mapping",
         "NER_TYPE_MAP = {\n    'PERSON':'Person', 'ORG':'Organization',\n    'GPE':'Location',  'LOC':'Location',\n    'DATE':'Date',     'EVENT':'Event',\n    'PRODUCT':'Product', ...\n}",
         "Maps spaCy's internal NER labels to our graph node types. GPE (Geopolitical Entity) maps to Location. WORK_OF_ART, LAW, LANGUAGE all map to Concept. This standardizes the type vocabulary across the whole graph."),
        ("SVO triple extraction",
         "for token in sent:\n    if token.pos_ != 'VERB': continue\n    subjs = [c for c in token.children\n             if c.dep_ in ('nsubj','nsubjpass')]\n    objs  = [c for c in token.children\n             if c.dep_ in ('dobj','attr','pobj')]\n    for s in subjs:\n        for o in objs:\n            add_edge(s.text, token.lemma_, o.text)",
         "Subject-Verb-Object extraction using dependency parsing. For each VERB token, finds its grammatical subject (nsubj) and object (dobj). Example: 'Einstein developed relativity' → subject=Einstein, verb=developed, object=relativity → edge: Einstein -[developed]→ relativity. token.lemma_ gives the base form (developed→develop)."),
        ("Co-occurrence extraction",
         "for sent in doc.sents:\n    ents = [e.text for e in sent.ents]\n    for i in range(len(ents) - 1):\n        if ents[i] != ents[i+1]:\n            add_edge(ents[i], 'related_to', ents[i+1])",
         "If two named entities appear in the same sentence, they're probably related. This creates 'related_to' edges between consecutive entities in each sentence. Less precise than SVO but catches relationships that don't have explicit verbs."),
    ]
    for title, code, explanation in blocks:
        e.append(KeepTogether([H3(title),P(code.replace(" ","&nbsp;").replace("\n","<br/>"),sCode),P(f"<b>Explanation:</b> {explanation}"),SP(4)]))
    e.append(PageBreak())
    return e

# ── Section 10: query_engine.py ───────────────────────────────────────────────
def s10_qe():
    e=[]
    e.append(H1("10. File: query_engine.py — Line by Line")); e.append(HR())
    e.append(P("query_engine.py implements a mini Cypher-like query language. It parses text queries and executes them against the in-memory graph data."))
    blocks=[
        ("run_query() — router",
         "def run_query(q, db):\n    upper = q.upper()\n    if upper.startswith('STATS'):     return _stats(db)\n    if upper.startswith('NEIGHBORS'): return _neighbors(q, db)\n    if upper.startswith('PATH'):      return _path(q, db)\n    if upper.startswith('COUNT'):     return _count(q, db)\n    if upper.startswith('MATCH'):     return _match(q, db)",
         "Simple keyword-based router. Checks the first word of the query and dispatches to the right handler. All handlers return the same structure: {columns, rows, graph, message} so the frontend can render them uniformly."),
        ("_match() — pattern parsing with regex",
         "rel_pattern = re.search(\n    r'\\((\\w*):?(\\w*)\\)\\s*-\\[(\\w*):?(\\w*)\\]->\\s*\\((\\w*):?(\\w*)\\)', q\n)",
         "This regex parses (n:Person)-[r:WORKS_AT]->(m:Organization). The 6 capture groups are: node1_var, node1_type, rel_var, rel_type, node2_var, node2_type. If this pattern matches, it's a relationship query. If not, it falls through to node-only matching."),
        ("WHERE clause evaluation",
         "m = re.match(r'(\\w+)\\.(\\w+)\\s+CONTAINS\\s+\"([^\"]*)\"', clause)\nif m:\n    var, field, val = m.groups()\n    return val.lower() in str(_get_field(row, var, field)).lower()",
         "Evaluates WHERE conditions like 'n.label CONTAINS \"Einstein\"'. Supports CONTAINS, STARTS WITH, = (equals), != (not equals), AND, OR. _get_field() extracts the right value from the result row based on variable name and field name."),
        ("_path() — BFS shortest path",
         "adj = {}\nfor e in edges:\n    adj.setdefault(e['from'],[]).append((e['to'],  e['label'],e['id']))\n    adj.setdefault(e['to'],  []).append((e['from'],e['label'],e['id']))\nqueue = deque([(src_id, [src_id], [])])\nvisited = {src_id}",
         "Builds an adjacency list treating edges as undirected (both directions). BFS (Breadth-First Search) guarantees the shortest path is found first. Each queue item carries (current_node, path_nodes_so_far, path_edges_so_far). The visited set prevents infinite loops in cyclic graphs."),
        ("_stats() — graph statistics",
         "type_counts = {}\nfor n in nodes.values():\n    t = n.get('type','Unknown')\n    type_counts[t] = type_counts.get(t, 0) + 1\nrel_counts = {}\nfor e in edges:\n    rel_counts[e['label']] = rel_counts.get(e['label'],0) + 1",
         "Counts nodes by type and edges by relationship label. Returns a table showing total nodes, total edges, breakdown by entity type, and breakdown by relationship type. Useful for understanding the composition of your knowledge graph."),
    ]
    for title, code, explanation in blocks:
        e.append(KeepTogether([H3(title),P(code.replace(" ","&nbsp;").replace("\n","<br/>"),sCode),P(f"<b>Explanation:</b> {explanation}"),SP(4)]))
    e.append(PageBreak())
    return e

# ── Section 11-12: owl_parser + processor ────────────────────────────────────
def s11_owl():
    e=[]
    e.append(H1("11. File: owl_parser.py — Line by Line")); e.append(HR())
    e.append(P("owl_parser.py parses OWL/RDF-XML ontology files into graph JSON. It uses Python's built-in xml.etree — no external OWL library needed for parsing."))
    blocks=[
        ("XML Namespaces",
         "RDF  = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'\nRDFS = 'http://www.w3.org/2000/01/rdf-schema#'\nOWL  = 'http://www.w3.org/2002/07/owl#'",
         "OWL files use XML namespaces as prefixes for all tags. Every owl:Class tag is actually {http://www.w3.org/2002/07/owl#}Class in the XML. These constants are used to find elements: root.findall(f'{{{OWL}}}Class')."),
        ("_local() — URI to name",
         "def _local(uri):\n    for sep in ['#', '/']:\n        if sep in uri:\n            return uri.rsplit(sep, 1)[-1]\n    return uri",
         "Extracts the local name from a URI. 'http://ontology#Person' → 'Person'. 'http://ontology/concepts/BERT' → 'BERT'. rsplit with maxsplit=1 splits only on the last occurrence of the separator."),
        ("Parsing NamedIndividuals (nodes)",
         "for el in root.findall(f'{{{OWL}}}NamedIndividual'):\n    ind_id = _local(el.get(f'{{{RDF}}}about',''))\n    label_el = el.find(f'{{{RDFS}}}label')\n    label = label_el.text if label_el else ind_id\n    type_el = el.find(f'{{{RDF}}}type')\n    etype = _local(type_el.get(f'{{{RDF}}}resource',''))",
         "NamedIndividuals are the actual instances in an ontology — they become graph nodes. rdf:about gives the URI (converted to ID). rdfs:label gives the display name. rdf:type gives the class (entity type)."),
        ("DOCTYPE stripping",
         "clean = re.sub(r'<!DOCTYPE[^>]*\\[.*?\\]>', '', text, flags=re.DOTALL)\nroot  = ET.fromstring(clean)",
         "Python's xml.etree doesn't support DOCTYPE declarations. The regex strips them before parsing. re.DOTALL makes . match newlines so multi-line DOCTYPE blocks are removed correctly."),
    ]
    for title, code, explanation in blocks:
        e.append(KeepTogether([H3(title),P(code.replace(" ","&nbsp;").replace("\n","<br/>"),sCode),P(f"<b>Explanation:</b> {explanation}"),SP(4)]))
    e.append(H1("12. File: processor.py — Line by Line")); e.append(HR())
    e.append(P("processor.py converts PDFs into OWL ontology files using owlready2. It's the most complex file — it dynamically creates OWL classes and properties at runtime."))
    blocks2=[
        ("Fresh world per call",
         "owlready2.default_world = owlready2.World()\nunique_iri = f'http://research-kg.org/ontology/{uuid.uuid4().hex}#'\nonto = owlready2.get_ontology(unique_iri)",
         "owlready2 caches ontology classes globally. If you process two PDFs, the second call would reuse classes from the first, causing metaclass conflicts. Creating a fresh World() and using a unique UUID-based IRI prevents this completely."),
        ("Dynamic class creation",
         "for label, cls_name in NER_CLASS_MAP.items():\n    cls = types.new_class(cls_name, (ResearchEntity,))\n    cls.namespace = onto\n    ner_classes[label] = cls",
         "types.new_class() creates Python classes dynamically at runtime. Each NER type (PERSON, ORG, etc.) becomes an OWL class that inherits from ResearchEntity. This is equivalent to writing 'class Person(ResearchEntity): pass' but done programmatically."),
        ("Dynamic property creation",
         "for rel in {t[1] for t in triples}:\n    prop = types.new_class(prop_name, (owlready2.ObjectProperty,))\n    prop.domain = [ResearchEntity]\n    prop.range  = [ResearchEntity]",
         "Each unique verb extracted from the PDF becomes an OWL ObjectProperty. domain and range constrain what types of entities can be connected by this property. The result is a proper OWL ontology that can be opened in Protégé."),
    ]
    for title, code, explanation in blocks2:
        e.append(KeepTogether([H3(title),P(code.replace(" ","&nbsp;").replace("\n","<br/>"),sCode),P(f"<b>Explanation:</b> {explanation}"),SP(4)]))
    e.append(PageBreak())
    return e

# ── Section 13: Database Schema ───────────────────────────────────────────────
def s13_schema():
    e=[]
    e.append(H1("13. Database Schema — How Data is Stored")); e.append(HR())
    e.append(P("All graph data is stored in MongoDB Atlas (cloud) with SQLite as an automatic offline fallback. The schema is identical in both databases."))
    e.append(SP(10)); e.append(DBDiagram(500,170))
    e.append(P("Figure 4: Database schema — nodes and edges collections with relationships",sCaption))
    e.append(H2("MongoDB: nodes collection"))
    rows=[[P("<b>Field</b>",sTH),P("<b>Type</b>",sTH),P("<b>Example</b>",sTH),P("<b>Notes</b>",sTH)],
          ["_id","ObjectId","ObjectId('69c5...')","Auto-generated by MongoDB"],
          ["id","String","john_smith","Unique — indexed. Used as graph node ID"],
          ["label","String","John Smith","Display name shown on graph"],
          ["type","String","Person","Entity type: Person|Org|Location|Concept|..."],
          ["properties","Object","{'born':1879}","Key-value metadata. Empty {} if none"]]
    e.append(tbl(rows,[60,80,130,170]))
    e.append(SP(8)); e.append(H2("MongoDB: edges collection"))
    rows2=[[P("<b>Field</b>",sTH),P("<b>Type</b>",sTH),P("<b>Example</b>",sTH),P("<b>Notes</b>",sTH)],
           ["_id","ObjectId","ObjectId('69c5...')","Auto-generated by MongoDB"],
           ["id","String","e5","Unique edge ID. Format: e{count}"],
           ["from_id","String","john_smith","References nodes.id (source node)"],
           ["to_id","String","stanford_university","References nodes.id (target node)"],
           ["label","String","AFFILIATED_WITH","Relationship type — uppercase snake_case"],
           ["properties","Object","{'since':2020}","Key-value metadata. Empty {} if none"]]
    e.append(tbl(rows2,[60,80,130,170]))
    e.append(SP(8)); e.append(H2("MongoDB Indexes"))
    rows3=[[P("<b>Collection</b>",sTH),P("<b>Index</b>",sTH),P("<b>Type</b>",sTH),P("<b>Purpose</b>",sTH)],
           ["nodes","id","Unique","Prevents duplicate nodes. Fast lookup by ID"],
           ["edges","id","Unique","Prevents duplicate edge IDs"],
           ["edges","(from_id, to_id, label)","Compound","Prevents duplicate relationships. Fast edge_key_exists()"]]
    e.append(tbl(rows3,[70,130,80,160]))
    e.append(SP(8)); e.append(H2("SQLite Schema (Fallback)"))
    for line in ["CREATE TABLE nodes (",
                 "    id         TEXT PRIMARY KEY,   -- unique node identifier",
                 "    label      TEXT NOT NULL,       -- display name",
                 "    type       TEXT DEFAULT 'Node', -- entity type",
                 "    properties TEXT DEFAULT '{}'    -- JSON string",
                 ");",
                 "",
                 "CREATE TABLE edges (",
                 "    id         TEXT PRIMARY KEY,   -- unique edge identifier",
                 "    from_id    TEXT NOT NULL,       -- source node id",
                 "    to_id      TEXT NOT NULL,       -- target node id",
                 "    label      TEXT NOT NULL,       -- relationship type",
                 "    properties TEXT DEFAULT '{}'    -- JSON string",
                 ");"]:
        e.append(P(line.replace(" ","&nbsp;"),sCode))
    e.append(SP(8)); e.append(H2("How Data Flows: PDF → MongoDB"))
    rows4=[[P("<b>Step</b>",sTH),P("<b>What Happens</b>",sTH),P("<b>Where Stored</b>",sTH)],
           ["1. Upload","PDF saved to /uploads/ folder","Local filesystem"],
           ["2. Extract text","pdfplumber reads all pages","RAM (temporary)"],
           ["3. Chunk","Text split into 3000-char pieces","RAM (temporary)"],
           ["4. LLM call","Each chunk sent to Groq API","Groq servers (API call)"],
           ["5. Parse JSON","Entities and relations extracted","RAM (temporary)"],
           ["6. Deduplicate","Same entity from multiple chunks merged","RAM (temporary)"],
           ["7. Insert nodes","insert_node() with upsert=True","MongoDB nodes collection"],
           ["8. Insert edges","insert_edge() if not exists","MongoDB edges collection"],
           ["9. Return graph","db_to_vis() fetches all data","Sent to browser as JSON"]]
    e.append(tbl(rows4,[30,250,160]))
    e.append(PageBreak())
    return e

# ── Section 14: API Reference ─────────────────────────────────────────────────
def s14_api():
    e=[]
    e.append(H1("14. REST API Reference")); e.append(HR())
    rows=[[P("<b>Method</b>",sTH),P("<b>Endpoint</b>",sTH),P("<b>Request Body</b>",sTH),P("<b>Response</b>",sTH)],
          ["GET","/","—","Serves index.html frontend"],
          ["GET","/graph","—","{nodes:[...], edges:[...]}"],
          ["POST","/node","{label, type, properties}","{id, graph}"],
          ["PUT","/node/<id>","{label, type, properties}","{graph}"],
          ["DELETE","/node/<id>","—","{graph}"],
          ["POST","/edge","{from, to, relation}","{id, graph}"],
          ["DELETE","/edge/<id>","—","{graph}"],
          ["POST","/upload","multipart/form-data PDF","{graph, stats, method}"],
          ["POST","/query","{q: 'MATCH (n:Person)'}","{columns, rows, graph, message}"],
          ["POST","/ask","{question: 'Who are...'}","{answer, relevant_node_ids, confidence}"],
          ["POST","/owl/parse","{owl: '<rdf:RDF...>'}","{graph}"],
          ["POST","/owl/import","{owl: '<rdf:RDF...>'}","{graph, added_nodes, added_edges}"],
          ["POST","/clear","—","{graph: {nodes:[], edges:[]}}"]]
    e.append(tbl(rows,[45,110,150,135]))
    e.append(PageBreak())
    return e

# ── Section 15: Frontend ──────────────────────────────────────────────────────
def s15_frontend():
    e=[]
    e.append(H1("15. Frontend Architecture")); e.append(HR())
    e.append(P("The entire frontend is a single file: templates/index.html (~1100 lines). It's a Single Page Application (SPA) with no build tools, no npm, no React — just HTML, CSS, and vanilla JavaScript."))
    e.append(H2("Layout Structure"))
    for line in ["┌─────────────────────────────────────────────────────────────┐",
                 "│  Header: Logo | Node count | Edge count | Buttons           │",
                 "├──────────────┬──────────────────────────────┬───────────────┤",
                 "│  Sidebar     │  Graph Canvas (vis-network)  │  Detail Panel │",
                 "│  ─────────   │                              │  (node info)  │",
                 "│  + Create    │  Force-directed physics       │               │",
                 "│  ◉ Nodes     │  simulation                  │               │",
                 "│  ⌕ Query     │                              │               │",
                 "│  🤖 AI       │  Dot grid background         │               │",
                 "│  📄 PDF      │                              │               │",
                 "│  🦉 OWL      │                              │               │",
                 "├──────────────┴──────────────────────────────┴───────────────┤",
                 "│  Toolbar: Layout selector | Edge labels | Fit button        │",
                 "└─────────────────────────────────────────────────────────────┘"]:
        e.append(P(line.replace(" ","&nbsp;"),sCode))
    e.append(H2("Key JavaScript Functions"))
    rows=[[P("<b>Function</b>",sTH),P("<b>What it does</b>",sTH)],
          ["loadGraph()","Fetches /graph?t=timestamp, calls renderGraph()"],
          ["renderGraph(data)","Destroys old vis-network, creates new one with nodes+edges"],
          ["uploadPDF()","POSTs PDF to /upload, shows spinner, calls renderGraph on response"],
          ["uploadMultiPDF()","Loops through files, calls /upload for each, shows progress bar"],
          ["askAI()","POSTs question to /ask, highlights relevant_node_ids on graph"],
          ["runQuery()","POSTs query to /query, renders result table + subgraph"],
          ["showDetail(nodeId)","Opens right panel with node info, outgoing/incoming edges"],
          ["toggleTheme()","Toggles :root.light class, saves to localStorage"],
          ["clearAll()","POSTs to /clear, re-fetches graph to confirm empty"]]
    e.append(tbl(rows,[140,300]))
    e.append(H2("vis-network Configuration"))
    e.append(P("The graph uses forceAtlas2Based physics solver with these settings:"))
    for line in ["physics: {",
                 "  solver: 'forceAtlas2Based',",
                 "  forceAtlas2Based: {",
                 "    gravitationalConstant: -60,  // repulsion between nodes",
                 "    centralGravity: 0.005,        // pull toward center",
                 "    springLength: 140,            // ideal edge length",
                 "    springConstant: 0.08,         // edge stiffness",
                 "    damping: 0.4                  // how fast motion stops",
                 "  }",
                 "}"]:
        e.append(P(line.replace(" ","&nbsp;"),sCode))
    e.append(PageBreak())
    return e

# ── Section 16: Interview Q&A ─────────────────────────────────────────────────
def s16_interview():
    e=[]
    e.append(H1("16. Interview Questions & Answers")); e.append(HR())
    qas=[
        ("What is this project?",
         "A full-stack web app that reads research papers (PDFs), extracts entities and relationships using AI (Groq LLM), stores them in MongoDB Atlas, and visualizes them as an interactive knowledge graph."),
        ("What is a knowledge graph?",
         "A graph where nodes are real-world entities (people, orgs, concepts) and edges are relationships. Example: 'BERT' -[DEVELOPED_BY]→ 'Google' -[LOCATED_IN]→ 'USA'."),
        ("Why Python 3.11 specifically?",
         "Python 3.14 has a TLS incompatibility with MongoDB Atlas — the SSL handshake fails with TLSV1_ALERT_INTERNAL_ERROR. Python 3.11 works correctly with MongoDB's TLS configuration."),
        ("How does PDF extraction work?",
         "pdfplumber extracts text → split into 3000-char chunks → each chunk sent to Groq LLM → LLM returns JSON {entities, relations} → deduplicated → saved to MongoDB."),
        ("What happens if Groq API is down?",
         "The code has a fallback chain. If Groq fails, it automatically uses spaCy NER + SVO dependency parsing. If all chunks fail, spaCy is used. The user always gets results."),
        ("How do you prevent duplicate nodes?",
         "MongoDB upsert=True with unique index on id field. Same ID never creates a duplicate — it just updates the existing document."),
        ("How does the NL query work?",
         "Load graph from MongoDB → build compact text summary (max 150 nodes) → send question + summary to Groq LLM → LLM returns answer + relevant node IDs → frontend highlights those nodes."),
        ("What is the database schema?",
         "Two MongoDB collections: nodes {id, label, type, properties} and edges {id, from_id, to_id, label, properties}. Indexes on id (unique) and compound (from_id, to_id, label)."),
        ("How does BFS shortest path work?",
         "Build adjacency list from all edges (bidirectional). BFS queue carries (current_node, path_nodes, path_edges). When destination reached, return the path. visited set prevents infinite loops."),
        ("How would you scale this for production?",
         "Replace tlsInsecure=True with proper TLS certs. Add JWT authentication. Use Gunicorn with multiple workers. Add Redis caching. Use Celery for background PDF processing. Add rate limiting on AI endpoints."),
        ("What is tlsInsecure=True and why is it used?",
         "It bypasses TLS certificate validation in PyMongo. Used because Python 3.11's OpenSSL sends a TLS handshake that MongoDB Atlas rejects with strict cert validation. Acceptable for development, not production."),
        ("How does the database abstraction work?",
         "database.py uses module-level globals (_db, _use_mongo). Every function checks _is_mongo() and branches to MongoDB or SQLite code. app.py calls insert_node() without knowing which DB is active."),
    ]
    for i,(q,a) in enumerate(qas):
        e.append(KeepTogether([
            P(f"<b>Q{i+1}. {q}</b>",S("q",fontSize=10,fontName="Helvetica-Bold",textColor=C_ACCENT2,spaceBefore=10,spaceAfter=3)),
            P(a,S("a",fontSize=9.5,fontName="Helvetica",textColor=C_TEXT,leftIndent=12,spaceAfter=2,leading=14)),
        ]))
    return e

# ── Build PDF ─────────────────────────────────────────────────────────────────
def build():
    fname = "Knowledge_Graph_Studio_Complete_Report.pdf"
    doc = SimpleDocTemplate(fname, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2.2*cm, bottomMargin=2*cm,
        title="Knowledge Graph Studio — Complete Project Report",
        author="Knowledge Graph Studio")

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(C_ACCENT); canvas.setLineWidth(0.5)
        canvas.line(2*cm, H-1.5*cm, W-2*cm, H-1.5*cm)
        canvas.setFont("Helvetica",7.5); canvas.setFillColor(C_MUTED)
        canvas.drawString(2*cm, H-1.25*cm, "Knowledge Graph Studio — Complete Project Report")
        canvas.drawRightString(W-2*cm, H-1.25*cm, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#cbd5e1")); canvas.setLineWidth(0.4)
        canvas.line(2*cm, 1.3*cm, W-2*cm, 1.3*cm)
        canvas.setFont("Helvetica",7); canvas.setFillColor(C_MUTED)
        canvas.drawCentredString(W/2, 0.85*cm, "AI-Powered Research Knowledge Graph Builder  ·  Python + Flask + MongoDB + Groq LLM")
        canvas.restoreState()

    story = []
    story += cover()
    story += toc()
    story += s1_overview()
    story += s2_tech()
    story += s3_arch()
    story += s4_flow()
    story += s5_app()
    story += s6_db()
    story += s7_ai()
    story += s8_nl()
    story += s9_ext()
    story += s10_qe()
    story += s11_owl()
    story += s13_schema()
    story += s14_api()
    story += s15_frontend()
    story += s16_interview()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅ PDF generated: {fname}")

if __name__ == "__main__":
    build()
