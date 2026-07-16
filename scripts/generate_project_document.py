"""
Generates the full Sanket AI project document as a professionally formatted PDF.
Run:  python scripts/generate_project_document.py
Output: Sanket_AI_Project_Document.pdf  (project root)  ~28-30 pages
"""
from fpdf import FPDF
from fpdf.enums import XPos, YPos

ACCENT = (47, 98, 207)
ACCENT_L = (223, 232, 250)
DARK = (24, 30, 44)
BODY = (46, 54, 68)
GREY = (96, 106, 121)
LINE = (215, 222, 232)
OKG = (21, 130, 95)
WARN = (176, 110, 12)
CRIT = (200, 55, 48)
CARD = (244, 247, 251)


def s(t: str) -> str:
    rep = {"₹": "Rs ", "→": "->", "⇄": "<->", "—": " - ", "–": "-", "‘": "'", "’": "'",
           "“": '"', "”": '"', "…": "...", "×": "x", "°": " deg", "µ": "u", "•": "-",
           "≈": "~", "®": "(R)", "‑": "-", "·": " - ", "✓": "[x]", "≤": "<=", "≥": ">="}
    for a, b in rep.items():
        t = t.replace(a, b)
    return t.encode("latin-1", "replace").decode("latin-1")


class PDF(FPDF):
    section = ""

    def header(self):
        if self.page_no() <= 2:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.set_y(8)
        self.cell(0, 6, s("Sanket AI - Project Document"), align="L")
        self.cell(0, 6, s(self.section), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*LINE)
        self.set_line_width(0.2)
        self.line(self.l_margin, 15, self.w - self.r_margin, 15)
        self.set_y(20)

    def footer(self):
        if self.page_no() <= 2:
            return
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, s(f"Team IIITDards  -  ET AI Hackathon 2.0  -  Problem Statement 8"), align="L")
        self.cell(0, 6, s(f"Page {self.page_no()}"), align="R")


pdf = PDF(format="A4")
pdf.set_auto_page_break(auto=True, margin=16)
pdf.set_margins(18, 20, 18)
EPW = pdf.epw  # effective page width


# ── helpers ──────────────────────────────────────────────────────────────────
def h1(title):
    pdf.section = title
    if pdf.get_y() > pdf.h - 60:
        pdf.add_page()
    else:
        pdf.ln(3)
    pdf.start_section(title)
    pdf.set_fill_color(*ACCENT)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 11, s("  " + title), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)


def h2(title):
    if pdf.get_y() > pdf.h - 40:
        pdf.add_page()
    pdf.start_section(title, level=1)
    pdf.set_text_color(*ACCENT)
    pdf.set_font("Helvetica", "B", 11.5)
    pdf.cell(0, 7, s(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)


def body(text):
    pdf.set_text_color(*BODY)
    pdf.set_font("Helvetica", "", 10.3)
    pdf.multi_cell(EPW, 5.4, s(text))
    pdf.ln(1.6)


def bullets(items, gap=1.0):
    pdf.set_text_color(*BODY)
    pdf.set_font("Helvetica", "", 10.3)
    for it in items:
        y = pdf.get_y()
        pdf.set_x(pdf.l_margin + 2)
        pdf.set_text_color(*ACCENT)
        pdf.cell(4, 5.2, s("-"))
        pdf.set_text_color(*BODY)
        pdf.set_x(pdf.l_margin + 6)
        pdf.multi_cell(EPW - 6, 5.2, s(it))
        pdf.ln(gap)
    pdf.ln(1.2)


def callout(text, color=ACCENT, bg=ACCENT_L):
    pdf.ln(1)
    x, y = pdf.l_margin, pdf.get_y()
    pdf.set_font("Helvetica", "I", 10)
    # measure height
    lines = pdf.multi_cell(EPW - 10, 5.2, s(text), dry_run=True, output="LINES")
    hgt = len(lines) * 5.2 + 6
    if y + hgt > pdf.h - 18:
        pdf.add_page()
        y = pdf.get_y()
    pdf.set_fill_color(*bg)
    pdf.set_draw_color(*color)
    pdf.rect(x, y, EPW, hgt, "F")
    pdf.set_fill_color(*color)
    pdf.rect(x, y, 1.5, hgt, "F")
    pdf.set_xy(x + 6, y + 3)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(EPW - 10, 5.2, s(text))
    pdf.set_y(y + hgt + 3)


def table(headers, rows, widths):
    pdf.ln(1)
    # scale widths to EPW
    tot = sum(widths)
    widths = [w / tot * EPW for w in widths]
    # header
    pdf.set_font("Helvetica", "B", 9.3)
    pdf.set_fill_color(*ACCENT)
    pdf.set_text_color(255, 255, 255)
    for w, hh in zip(widths, headers):
        pdf.cell(w, 7, s(" " + hh), fill=True, border=0)
    pdf.ln(7)
    # rows
    pdf.set_font("Helvetica", "", 9.2)
    fill = False
    for row in rows:
        # compute row height from wrapped cells
        heights = []
        for w, c in zip(widths, row):
            lines = pdf.multi_cell(w - 2, 4.8, s(str(c)), dry_run=True, output="LINES")
            heights.append(len(lines) * 4.8 + 2.6)
        rh = max(heights)
        if pdf.get_y() + rh > pdf.h - 18:
            pdf.add_page()
        x0, y0 = pdf.l_margin, pdf.get_y()
        pdf.set_fill_color(*(CARD if fill else (255, 255, 255)))
        pdf.rect(x0, y0, EPW, rh, "F")
        x = x0
        pdf.set_text_color(*BODY)
        for w, c in zip(widths, row):
            pdf.set_xy(x + 1, y0 + 1.3)
            pdf.multi_cell(w - 2, 4.8, s(str(c)), align="L")
            x += w
        pdf.set_draw_color(*LINE)
        pdf.set_line_width(0.15)
        pdf.line(x0, y0 + rh, x0 + EPW, y0 + rh)
        pdf.set_y(y0 + rh)
        fill = not fill
    pdf.ln(3)


def box(x, y, w, h, title, sub, fillc, textc=DARK):
    pdf.set_fill_color(*fillc)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.3)
    pdf.rect(x, y, w, h, "DF")
    pdf.set_xy(x, y + (h / 2 - (5 if sub else 2.5)))
    pdf.set_text_color(*textc)
    pdf.set_font("Helvetica", "B", 8.6)
    pdf.cell(w, 5, s(title), align="C")
    if sub:
        pdf.set_xy(x, y + h / 2)
        pdf.set_font("Helvetica", "", 7.2)
        pdf.set_text_color(*GREY)
        pdf.multi_cell(w, 3.4, s(sub), align="C")


def arrow_down(cx, y, h=5):
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.4)
    pdf.line(cx, y, cx, y + h)
    pdf.line(cx - 1.6, y + h - 1.8, cx, y + h)
    pdf.line(cx + 1.6, y + h - 1.8, cx, y + h)


# ══════════════════════════════════════════════════════════════════════════════
# COVER
# ══════════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.set_fill_color(*ACCENT)
pdf.rect(0, 0, pdf.w, 80, "F")
pdf.set_fill_color(138, 108, 240)
pdf.rect(0, 80, pdf.w, 4, "F")
pdf.set_xy(18, 26)
pdf.set_text_color(255, 255, 255)
pdf.set_font("Helvetica", "B", 34)
pdf.cell(0, 16, s("Sanket AI"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(18)
pdf.set_font("Helvetica", "", 15)
pdf.cell(0, 9, s("The Unified Asset & Operations Brain"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(18)
pdf.set_font("Helvetica", "", 11)
pdf.cell(0, 7, s("Industrial Knowledge Intelligence Platform  -  Project Document"))

pdf.set_xy(18, 100)
pdf.set_text_color(*DARK)
pdf.set_font("Helvetica", "I", 12)
pdf.multi_cell(EPW, 6.5, s("An AI platform that ingests a plant's heterogeneous documents and its P&ID topology "
                           "into a unified knowledge graph - and returns cited, computed answers across "
                           "maintenance, compliance, and operations, at the point of need."))
pdf.ln(8)
# meta table on cover
pdf.set_font("Helvetica", "", 10.5)
meta = [("Team", "IIITDards"), ("Event", "ET AI Hackathon 2.0"),
        ("Problem Statement", "8 - AI for Industrial Knowledge Intelligence"),
        ("Status", "Working prototype - 33 automated tests passing"),
        ("Runtime", "Runs with zero external services (in-memory + deterministic engine)")]
for k, v in meta:
    pdf.set_x(18)
    pdf.set_text_color(*ACCENT)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(42, 7, s(k))
    pdf.set_text_color(*BODY)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.multi_cell(EPW - 42, 7, s(v))
pdf.ln(6)
pdf.set_draw_color(*ACCENT)
pdf.set_line_width(0.5)
pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
pdf.ln(4)
pdf.set_text_color(*GREY)
pdf.set_font("Helvetica", "I", 9.5)
pdf.multi_cell(EPW, 5, s("Deliverables in this project: Working Prototype - Architecture (this document + in-app "
                         "diagram) - Presentation Deck - Demo Video. This document covers the problem, the solution, "
                         "the architecture and design, the evaluation, the business case, and the future roadmap."))


# ══════════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS
# ══════════════════════════════════════════════════════════════════════════════
def render_toc(p, outline):
    p.set_y(24)
    p.set_font("Helvetica", "B", 22)
    p.set_text_color(*ACCENT)
    p.cell(0, 14, s("Contents"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_draw_color(*LINE)
    p.line(18, p.get_y(), p.w - 18, p.get_y())
    p.ln(4)
    for e in outline:
        lvl = e.level
        p.set_x(18 + lvl * 7)
        if lvl == 0:
            p.set_font("Helvetica", "B", 11)
            p.set_text_color(*DARK)
            p.ln(1.5)
        else:
            p.set_font("Helvetica", "", 9.8)
            p.set_text_color(*GREY)
        name = s(e.name)
        pg = str(e.page_number)
        avail = EPW - (lvl * 7) - 12
        p.cell(avail, 6.4, name)
        p.set_font("Helvetica", "", 9.5)
        p.set_text_color(*GREY)
        p.cell(12, 6.4, pg, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


pdf.add_page()
pdf.insert_toc_placeholder(render_toc, pages=2)


# ══════════════════════════════════════════════════════════════════════════════
# CONTENT
# ══════════════════════════════════════════════════════════════════════════════
pdf.add_page()

h1("Executive Summary")
body("In asset-intensive industry, knowledge is abundant but fragmented. A single large plant runs across "
     "seven to twelve disconnected document systems - engineering drawings in one place, maintenance work "
     "orders in another, inspection records in a third, and regulatory submissions scattered across email "
     "archives. Professionals spend an estimated 35% of their time simply searching for information that "
     "already exists somewhere in the organisation, and this fragmentation contributes to 18-22% of unplanned "
     "downtime because maintenance teams make decisions without complete equipment history or failure context.")
body("Sanket AI is a unified asset and operations brain. It ingests heterogeneous documents and the plant's "
     "P&ID topology into a single knowledge graph, and makes their collective intelligence queryable, cited, "
     "and actionable across any function. Its defining insight is architectural: rather than ranking documents "
     "by keyword similarity, Sanket makes the plant's physical connectivity the substrate the AI reasons over. "
     "A pump's vibration cannot be explained without knowing that a control valve two nodes upstream is "
     "cavitating - so Sanket traverses the graph to connect them.")
body("The platform delivers all five capability areas the problem statement describes: universal document "
     "ingestion with a knowledge graph, an expert knowledge copilot, maintenance and root-cause analysis, "
     "quality and regulatory compliance, and lessons-learned failure intelligence. Every answer carries source "
     "citations and a confidence score that is computed from evidence rather than asserted by a language model.")
callout("Headline result: for the query \"P-101A pump, 47 Hz vibration\", Sanket returns the root cause - V-201 "
        "control-valve cavitation, one hop upstream - at 97% computed confidence, cited to real inspection logs "
        "and work orders, in seconds versus roughly four hours of manual cross-system investigation.")
h2("At a glance")
table(["Dimension", "What Sanket delivers"],
      [["Pillars covered", "All 5 (ingestion+KG, copilot, RCA, compliance, failure intelligence)"],
       ["Core differentiator", "Graph-topology reasoning over the P&ID - not keyword search"],
       ["Trust", "Computed confidence + verified citations (hallucinated IDs flagged)"],
       ["Validation", "100% benchmark accuracy, 100% citation faithfulness, 97% entity F1"],
       ["Business impact", "~Rs 2.17 crore/year modelled for a mid-size plant"],
       ["Engineering", "10-view product, 33 tests, runs with zero external services"]],
      [26, 74])

h1("1. Problem Statement and Context")
body("Knowledge fragmentation in industrial operations is not a file-management problem. It is a safety "
     "problem, a quality problem, and an operational-efficiency problem - and it compounds over time. The "
     "organisations that solve it first gain a structural advantage in how they operate, maintain, and "
     "improve their assets.")
h2("1.1 The evidence")
bullets([
    "A 2024 McKinsey survey found professionals in asset-intensive industries spend ~35% of working hours "
    "searching for information, clarifying instructions, or recreating documents that already exist.",
    "A NASSCOM-EY study of Indian manufacturing and energy companies found the average large plant operates "
    "across 7 to 12 disconnected document systems.",
    "BIS Research estimated that this fragmentation contributes to 18-22% of unplanned downtime events in "
    "Indian heavy industry.",
    "An estimated 25% of India's experienced industrial engineers and operators will retire within the next "
    "decade, taking decades of undocumented operational knowledge with them - the 'knowledge cliff'.",
])
h2("1.2 What the challenge asks for")
body("The challenge is to build an AI-powered Industrial Knowledge Intelligence platform that ingests "
     "heterogeneous documents - engineering drawings, maintenance records, safety procedures, inspection "
     "reports, operating instructions, project files - across structured and unstructured formats, and makes "
     "their collective intelligence queryable, actionable, and continuously updated at the point of need, "
     "across any device or function. Five illustrative capability areas are suggested, and Sanket implements "
     "all five.")
h2("1.3 Evaluation focus (and how Sanket answers it)")
table(["Evaluation focus", "Sanket's answer"],
      [["Entity-extraction accuracy across document types", "97% F1 on gold-labelled equipment tags; extracts tags, dates, parameters, personnel, regulations"],
       ["Query answer quality on a domain benchmark", "100% on a 10-question domain benchmark, auto-scored"],
       ["Knowledge-graph linkage completeness", "100% of documents linked to equipment in the graph"],
       ["Time-to-answer vs traditional search", "Sub-second vs ~4 hours of manual cross-system search"],
       ["Compliance-gap detection accuracy", "Deterministic clause-to-evidence mapping across 7 standards"],
       ["Cross-functional knowledge discovery", "Unified graph links equipment, docs, failure modes, people, regulations"]],
      [42, 58])
h2("1.4 The cost of inaction")
body("Left unsolved, fragmentation compounds. Every retirement removes context that is never written down. "
     "Every new document system adds another silo to search. Every avoidable trip erodes both output and "
     "trust in the plant's data. The organisations that treat knowledge as connected infrastructure - rather "
     "than as files in folders - will operate, maintain, and improve their assets with a durable structural "
     "advantage over those that do not.")
h2("1.5 Why now")
body("Three forces make this solvable today that were not a few years ago: knowledge graphs have matured into "
     "a practical substrate for industrial ontologies; large language models can extract structure from "
     "unstructured text and converse over it; and cheap, fast inference makes agentic reasoning affordable at "
     "the point of need. Sanket combines all three - but critically, it does not depend on the LLM for its "
     "core correctness, which keeps it reproducible and trustworthy.")

h1("2. Solution Overview")
body("Sanket AI is delivered as a single, cohesive product - a command centre with ten views - backed by a "
     "set of deterministic reasoning engines and a Neo4j-optional knowledge graph. The same 'brain' powers "
     "five distinct capabilities.")
h2("2.1 The five pillars")
table(["Pillar", "Capability", "In the product"],
      [["1", "Universal Document Ingestion & Knowledge Graph", "Ingest view"],
       ["2", "Expert Knowledge Copilot", "Ask view"],
       ["3", "Maintenance & Root-Cause Analysis", "Diagnose view"],
       ["4", "Quality & Regulatory Compliance", "Compliance view"],
       ["5", "Lessons-Learned & Failure Intelligence", "Alerts + Capture views"]],
      [10, 62, 28])
h2("2.2 Beyond the five pillars")
bullets([
    "Predictive maintenance: a trained UCI AI4I classifier is wired in as an agent tool (sensor readings -> "
    "failure-probability and likely mode).",
    "Knowledge-Cliff Capture: a retiring expert's undocumented know-how is captured as a permanent, queryable "
    "graph node - directly addressing the retirement problem.",
    "Live monitoring: quality deviations (SPC) and predicted time-to-failure per asset.",
    "Business-impact modelling: an interactive ROI calculator grounded in the brief's own statistics.",
])
h2("2.3 The command centre (ten views)")
bullets([
    "Overview - plant-wide KPIs and validated metrics.",
    "Diagnose - the flagship graph-topology RCA console.",
    "Ask - the cited knowledge copilot.",
    "Ingest - document ingestion and entity extraction.",
    "Knowledge Graph - the unified multi-entity graph.",
    "Live Monitor - deviations and predicted time-to-failure.",
    "Compliance - clause-to-evidence gap detection.",
    "ROI - business-impact calculator.",
    "Capture - knowledge-cliff capture.",
    "Architecture - the live system diagram.",
])
h2("2.4 More than a search box or a dashboard")
body("A search box returns documents and leaves the reasoning to the human. A CMMS dashboard shows the data "
     "for one asset in one system. A generic AI copilot answers from whatever text it retrieved, with no "
     "guarantee the answer is grounded or the citation is real. Sanket is different on three axes: it reasons "
     "over the connections between assets, not just their documents; it computes confidence and verifies every "
     "citation; and it unifies every document type and function into one graph, so a maintenance question, a "
     "compliance question, and an operations question all draw on the same brain.")

h1("3. The Core Insight: Topology as the Reasoning Substrate")
body("Retrieval-augmented generation finds documents. It cannot reason about physical connectivity. A "
     "centrifugal pump's 47 Hz vibration cannot be diagnosed without knowing that a control valve two nodes "
     "upstream in the P&ID is experiencing cavitation, and that cavitation transmits hydraulic excitation "
     "downstream. Sanket makes the plant topology the reasoning substrate, not merely a metadata filter.")
body("When a symptom is reported, Sanket does not search a document index. It identifies the asset in the "
     "graph, traverses upstream along the P&ID's CONNECTED_TO edges, pulls every inspection log and work order "
     "for each neighbour, correlates ISO-14224 co-failure statistics, and returns the causal chain that no "
     "single document contains.")
# causal-chain diagram
pdf.ln(2)
if pdf.get_y() + 34 > pdf.h - 16:
    pdf.add_page()
pdf.set_auto_page_break(False)
y = pdf.get_y()
bw, bh = 52, 20
gap = (EPW - 2 * bw) - 4
x1 = pdf.l_margin
x2 = pdf.l_margin + bw + gap + 4
box(x1, y, bw, bh, "V-201  (Control Valve)", "Root cause: cavitation", (250, 226, 224), CRIT)
box(x2, y, bw, bh, "P-101A  (CW Pump)", "Symptom: 47 Hz vibration", (253, 240, 220), WARN)
# arrow between
pdf.set_draw_color(*ACCENT)
pdf.set_line_width(0.5)
midy = y + bh / 2
pdf.line(x1 + bw, midy, x2, midy)
pdf.line(x2 - 2.4, midy - 2, x2, midy)
pdf.line(x2 - 2.4, midy + 2, x2, midy)
pdf.set_xy(x1 + bw, midy - 8)
pdf.set_font("Helvetica", "", 7.6)
pdf.set_text_color(*GREY)
pdf.cell(gap + 4, 5, s("transmitted vibration"), align="C")
pdf.set_xy(x1 + bw, midy + 3)
pdf.cell(gap + 4, 5, s("ISO-14224 correlation r = 0.72"), align="C")
pdf.set_auto_page_break(True, margin=16)
pdf.set_y(y + bh + 6)
callout("Empirically, this matters: across our benchmark, graph-topology RCA identifies the true upstream root "
        "cause 100% of the time, versus 17% for a keyword-search baseline that returns the symptom's own "
        "documents.", OKG, (224, 244, 236))
h2("3.1 Document RAG versus graph-topology reasoning")
table(["Aspect", "Document RAG (keyword/vector)", "Sanket (graph topology)"],
      [["Unit of retrieval", "A document chunk", "A path through the plant graph"],
       ["Can connect an effect to an upstream cause?", "No - only surfaces text that mentions the symptom", "Yes - traverses CONNECTED_TO to the cause"],
       ["Answer to 'why is P-101A vibrating?'", "Returns P-101A's own logs (the symptom)", "Returns V-201 cavitation (the cause)"],
       ["Confidence", "Model-asserted or similarity score", "Computed from evidence, auditable"],
       ["Root-cause hit rate (our A/B)", "17%", "100%"]],
      [26, 37, 37])
h2("3.2 What makes the topology trustworthy")
body("The graph is not a black box. Edges are the plant's real pipe connections; failure modes come from ISO "
     "14224; co-failure correlations are explicit statistics; and every hop in a causal chain is shown to the "
     "user. An engineer can read the reasoning and check it against their own knowledge of the plant - which "
     "is exactly what earns trust on the floor.")

h1("4. The Five Pillars in Detail")
h2("4.1 Universal Document Ingestion and Knowledge Graph")
body("Sanket ingests heterogeneous document text - inspection reports, emails, OEM manuals, scanned forms, "
     "incident records, and shift-handover notes. A deterministic extractor (regex plus the graph's own "
     "vocabulary) pulls the entities the brief names: equipment tags, process parameters, regulatory "
     "references, personnel, and dates - and links them into the knowledge graph. Because extraction is "
     "deterministic, its accuracy is measurable (97% F1) and it runs with no LLM; an LLM pass can refine it "
     "when a key is present.")
bullets([
    "Preview: paste or load a document -> see extracted entities, colour-coded by whether they resolve to an "
    "existing graph node (cross-document discovery).",
    "Commit: the document is added to the graph, linked to every equipment it mentions.",
    "Six heterogeneous formats are demonstrated: PDF/scanned inspection report, email archive, OEM manual, "
    "regulatory submission, incident/near-miss, and free-text handover.",
])
h2("4.2 Expert Knowledge Copilot")
body("Any engineer - or a field technician on a phone - can ask a natural-language question and receive a "
     "cited answer drawn from the whole corpus, with a computed confidence and direct links to the source "
     "documents. Intent routing recognises questions about specific equipment, regulatory standards, or "
     "failure modes, and retrieves and synthesises accordingly.")
body("Ask 'what is the condition and history of P-101A?' and the copilot returns the asset's profile, the "
     "most relevant records with one-line findings and clickable citations, the applicable regulatory "
     "requirements, and a confidence based on the number and recency of sources - typically in well under a "
     "second. The same interface handles a regulatory question or a failure-mode question. Every answer links "
     "back to its sources, so nothing is a black box.")
h2("4.3 Maintenance and Root-Cause Analysis")
body("The flagship capability. A dual-mode engine runs a real graph investigation with no LLM (deterministic) "
     "and, when a Groq key is present, a LangGraph agent. Both produce a cited causal chain, a computed "
     "confidence with an auditable breakdown, ruled-out counter-hypotheses, next-checks, and a predicted "
     "time-to-failure derived from the telemetry trend.")
body("Consider the flagship scenario. A vibration alarm fires on pump P-101A at 47 Hz. The engine identifies "
     "the asset, traverses the P&ID upstream to its neighbours (the control valve V-201, the suction strainer "
     "ST-101, the storage tank), and pulls the inspection logs and work orders for each. It scores every "
     "candidate by physical proximity, ISO-14224 co-failure correlation to the observed symptom, and the "
     "severity and recency of its evidence. V-201 wins: its cavitation has a 0.72 co-failure correlation with "
     "pump vibration and recent high-severity findings. The engine returns V-201 cavitation as the root cause, "
     "one hop upstream, at 97% computed confidence, with the strainer explicitly ruled out - all cited, all in "
     "seconds. A second scenario (compressor K-501) resolves upstream to a blocked lube-oil filter, "
     "demonstrating the method generalises beyond a single scripted query.")
h2("4.4 Quality and Regulatory Compliance")
body("Sanket maps regulatory clauses - OISD, Factory Act, PESO, ISO, API, and CPCB - against each asset's "
     "actual inspection and monitoring evidence, and flags gaps where an applicable clause has no acceptable "
     "evidence within its interval. It produces a plant-wide compliance rate, per-asset gap lists with "
     "severity, and one-click audit evidence packages.")
h2("4.5 Lessons-Learned and Failure Intelligence")
body("A background analysis scans the corpus for active failure signatures and, using ISO-14224 co-failure "
     "statistics, projects the next likely failure for each asset - pushing proactive warnings before a "
     "condition recurs. It also surfaces the plant's top recurring failure modes across the whole history, and "
     "captures retiring experts' tribal knowledge as permanent graph nodes.")
h2("4.6 One brain, five capabilities - the capability matrix")
table(["Pillar", "Primary input", "Core output", "Key trust feature"],
      [["Ingestion & KG", "Raw document text", "Extracted entities linked into the graph", "97% F1, linkage shown"],
       ["Copilot", "Natural-language question", "Cited answer + confidence", "Source links, verified"],
       ["RCA", "A symptom / alarm", "Cited causal chain", "Computed confidence"],
       ["Compliance", "Asset + clauses", "Gap list + audit pack", "Evidence-backed"],
       ["Failure Intelligence", "Corpus history", "Proactive warnings", "ISO-14224 grounded"]],
      [22, 24, 30, 24])
body("Because all five draw on the same knowledge graph, they reinforce one another: an ingested document "
     "immediately improves the copilot's answers and the RCA evidence; a captured expert insight becomes "
     "queryable everywhere; and a compliance gap can be traced to the same assets an RCA implicates.")

h1("5. System Architecture")
body("Sanket is a layered system with one deliberate abstraction at its heart - a Store facade that makes the "
     "knowledge graph backend interchangeable. This is what lets the entire platform boot and demo with no "
     "database and no API keys, and upgrade to Neo4j and a Groq LLM agent the moment they are available.")
# architecture layered diagram
pdf.ln(1)
layers = [
    ("PRESENTATION", "Command-centre UI (10 views) - Cytoscape P&ID + Knowledge Graph - SSE streaming - infographics", (223, 232, 250)),
    ("API - FastAPI", "/rca (diagnose)   /graph (P&ID + knowledge graph)   /intel (ingest, ask, compliance, lessons, ROI, eval)", (233, 239, 250)),
    ("STORE FACADE (key abstraction)", "MemStore (in-memory from seed JSON)   <->  auto-select  <->   Neo4jStore (Cypher, production)", (219, 232, 249)),
    ("REASONING ENGINES", "Deterministic RCA + LangGraph LLM agent - Ingestion/extraction - Copilot - Compliance - Lessons - ML classifier", (233, 239, 250)),
]
lw = EPW
lh = 15
lx = pdf.l_margin
if pdf.get_y() + 4 * lh + 3 * 5 + 8 > pdf.h - 16:
    pdf.add_page()
pdf.set_auto_page_break(False)
ly = pdf.get_y()
for i, (t, d, col) in enumerate(layers):
    pdf.set_fill_color(*col)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.3)
    pdf.rect(lx, ly, lw, lh, "DF")
    pdf.set_xy(lx + 3, ly + 2.4)
    pdf.set_text_color(*ACCENT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(lw - 6, 4.6, s(t))
    pdf.set_xy(lx + 3, ly + 7.4)
    pdf.set_text_color(*BODY)
    pdf.set_font("Helvetica", "", 7.9)
    pdf.multi_cell(lw - 6, 3.5, s(d))
    ly += lh
    if i < len(layers) - 1:
        arrow_down(lx + lw / 2, ly, 4.5)
        ly += 5
pdf.set_auto_page_break(True, margin=16)
pdf.set_y(ly + 4)

h2("5.1 The Store facade")
body("get_store() probes Neo4j once. If the database is reachable and populated it returns a Neo4jStore; "
     "otherwise it transparently falls back to a MemStore built from the seed JSON files. Both implement an "
     "identical interface (traverse, documents_for, failure_modes, co_failure, telemetry, compliance, and so "
     "on), so every engine, endpoint, and view is backend-agnostic. Setting SANKET_FORCE_MEMSTORE=1 pins the "
     "offline backend; a short connection timeout keeps the fallback snappy.")
h2("5.2 Request lifecycle - a diagnosis")
bullets([
    "The UI opens an SSE stream to /rca/stream. If no Groq key is set, the deterministic engine runs.",
    "The engine identifies the asset, traverses the P&ID upstream, and pulls CMMS evidence for each neighbour.",
    "It correlates ISO-14224 co-failure statistics and selects the primary root-cause hypothesis.",
    "It computes confidence from evidence and verifies every citation against the graph.",
    "Tool calls, tokens, and a final meta payload (causal chain, confidence, metrics, citations) stream back; "
    "the P&ID lights up and the infographics render.",
])
h2("5.3 Design principles")
bullets([
    "Determinism first: the core works without an LLM, making it reproducible, testable, and demo-safe.",
    "Trust by construction: confidence is computed and citations are verified - not left to the model.",
    "Backend-agnostic: one interface, two stores, zero code changes to scale from a laptop to a cluster.",
    "Graceful degradation: robust /health and clear degraded states when a dependency is down.",
])

h1("6. Data Model and Knowledge Graph")
body("The knowledge graph is multi-entity. Beyond equipment, it models the documents that describe assets, "
     "the failure modes that affect them, the people who recorded findings, the regulations that govern them, "
     "and the ISA-95 area they belong to - with typed relationships across all of them.")
table(["Node type", "Represents", "Example"],
      [["Equipment", "A tagged asset in the P&ID", "P-101A, V-201, K-501"],
       ["Document", "An inspection log, work order, or ingested doc", "INS-2025-0847, WO-2025-0891"],
       ["FailureMode", "An ISO-14224 failure mode", "VA-C-CAV (valve cavitation)"],
       ["Person", "Personnel who recorded a finding", "Priya Mehta, Suresh Nair"],
       ["Regulation", "A regulatory clause", "OISD-STD-130, Factory Act 1948"],
       ["Area (ISA-95)", "Plant area / unit context", "Area A-01"]],
      [24, 46, 30])
h2("6.1 Typed relationships")
bullets([
    "CONNECTED_TO - directed P&ID flow between equipment (the reasoning substrate).",
    "DESCRIBES - a document describes an asset.",
    "RECORDED - a person recorded a document.",
    "HAS_MODE / RECORDS_FAILURE - equipment or document to a failure mode.",
    "GOVERNED_BY - equipment to a regulatory clause.",
    "CAUSES - ISO-14224 causal link between failure modes.",
    "IN_AREA - equipment to its ISA-95 area.",
])
h2("6.2 Ontology grounding")
body("The taxonomy is grounded in ISO 14224 (reliability and maintenance data), with equipment classes and "
     "failure modes for pumps, valves, heat exchangers, compressors, motors, strainers, and vessels, plus "
     "co-failure correlation statistics. Compliance is grounded in named Indian and international standards. "
     "Vibration is evaluated against ISO 10816 zones. This domain grounding is what makes the output legible "
     "and credible to industrial engineers.")
h2("6.3 The graph at a glance")
table(["Element", "Count in the seed corpus"],
      [["Equipment (across two circuits)", "17"],
       ["Documents (work orders, inspections, ingested, tribal)", "82"],
       ["Inspection logs / work orders", "52 / 30"],
       ["ISO-14224 equipment classes / failure modes", "7 / 16"],
       ["Regulatory clauses", "7 (OISD, Factory Act, PESO, ISO, API, CPCB)"],
       ["Telemetry-monitored assets", "3 (vibration / delta-P trends)"],
       ["Sample raw documents (for ingestion)", "6 formats"]],
      [56, 44])
h2("6.4 Extensibility")
body("The model is intentionally open. New equipment classes and failure modes are added by extending the ISO "
     "14224 taxonomy file; new standards by extending the clause file; new document types by adding an "
     "extractor route. Because the store presents one interface, none of these changes touch the reasoning "
     "engines or the UI. Adding a second plant is a matter of ingesting its P&ID and documents under a new "
     "plant identifier.")

h1("7. Reasoning Engines")
h2("7.1 Confidence, computed not asserted")
body("Confidence is a function of evidence: the number of corroborating documents, their recency, the severity "
     "of findings, the ISO-14224 co-failure correlation, and whether a physical upstream path was confirmed. "
     "Each component is returned in a breakdown, so when a judge asks how 97% was derived, there is a real, "
     "auditable answer.")
table(["Evidence factor", "Contribution", "For the P-101A case"],
      [["Base rate", "+25", "+25"],
       ["Corroborating documents (up to 4)", "+9 each", "+36 (4 documents)"],
       ["Highest-severity finding", "+12 (HIGH) / +6 (MED)", "+12 (HIGH)"],
       ["Evidence recency", "+8 (<90d) / +4 (<1y)", "+8"],
       ["ISO-14224 co-failure correlation", "correlation x 18", "+13 (r 0.72)"],
       ["Confirmed upstream physical path", "+8", "+8"],
       ["Total (capped at 97)", "", "97%"]],
      [40, 30, 30])
h2("7.2 Citation verification")
body("Every document ID an answer cites is checked against the knowledge graph. Valid IDs become clickable "
     "source chips; unverifiable IDs are flagged as unverified and never masquerade as real. Citation "
     "faithfulness is scored and reported (100% on the benchmark).")
h2("7.3 Predictive maintenance and time-to-failure")
body("A trained UCI AI4I RandomForest classifier is exposed as an agent tool that predicts failure "
     "probability and likely mode from sensor readings, with a transparent physics-style fallback when the "
     "model is unavailable. Separately, the engine extrapolates each asset's telemetry trend to estimate weeks "
     "to the trip threshold (for example, P-101A is projected to trip in about five weeks at its current "
     "degradation rate).")
h2("7.4 The RCA answer structure")
bullets([
    "Root-cause summary - one sentence naming the equipment and mechanism.",
    "Hypothesis with a computed confidence and a confidence basis.",
    "Evidence - cited documents with one-line findings.",
    "Ruled out - candidates considered and excluded, with reasons.",
    "Predicted time-to-failure and recommended action with urgency.",
    "Next checks and immediate actions.",
])

h1("8. User Experience and Design System")
body("The interface is a single-file, build-free command centre engineered to look like premium industrial "
     "software, not a notebook. The design language is deliberate: a calm dark canvas, a single restrained "
     "blue accent, and status colours (red/amber/green) reserved strictly for equipment state and severity - "
     "never decoration. A humanist sans carries the interface; a monospace face is reserved for data - "
     "equipment tags, numbers, and readouts.")
h2("8.1 Signature interactions")
bullets([
    "A live P&ID that lights up during a diagnosis - the failing asset turns red, the upstream cause amber, "
    "and the causal path is highlighted.",
    "A causal-chain ribbon, an ISO-10816 vibration-zone gauge, a trend chart, and an evidence-stacked "
    "confidence meter - real infographics, not decoration.",
    "Clickable citations that open a source-document drawer.",
    "A command palette (Ctrl+K), voice input for field use, a role switcher, dark/light themes, and an "
    "offline PWA shell.",
])
h2("8.2 Accessibility and responsiveness")
body("The layout is responsive down to a mobile field-technician view, with a bottom navigation and stacked "
     "infographics. Interactive controls carry accessible labels, keyboard focus is visible, and the palette "
     "maintains contrast in both themes.")
h2("8.3 The ten views")
table(["View", "What it does"],
      [["Overview (Command Centre)", "Plant-wide KPIs and validated evaluation metrics"],
       ["Diagnose", "Graph-topology RCA console with live P&ID and infographics"],
       ["Ask", "Cited knowledge copilot over the whole corpus"],
       ["Ingest", "Document ingestion and entity extraction"],
       ["Knowledge Graph", "Interactive multi-entity graph around any asset"],
       ["Live Monitor", "SPC deviations and predicted time-to-failure"],
       ["Compliance", "Clause-to-evidence gap detection per asset"],
       ["ROI", "Interactive business-impact calculator"],
       ["Capture", "Knowledge-cliff capture form and list"],
       ["Architecture", "Live system architecture diagram"]],
      [30, 70])
h2("8.4 The infographic system")
body("The diagnosis view is deliberately infographic, not textual. A causal-chain ribbon shows the root cause "
     "and symptom as connected faceplates; an ISO-10816 zone gauge places the current reading in its severity "
     "band; a trend chart shows the climb toward the alarm line; and an evidence-stacked confidence meter "
     "renders the score as its contributing factors. Each is a real, data-driven chart - the same numbers the "
     "engine computed - not decoration.")

h1("9. Evaluation and Validation")
body("The platform is validated against the brief's evaluation focus with measured, not claimed, numbers - "
     "surfaced live on the command-centre landing page and reproduced by an automated benchmark and test "
     "suite.")
table(["Metric", "Result", "How it is measured"],
      [["Benchmark answer accuracy", "100%", "10 gold Q&A auto-scored (focus, citation, no hallucination)"],
       ["Citation faithfulness", "100%", "Cited IDs verified against the graph"],
       ["Entity-extraction F1", "97%", "Precision/recall vs gold-labelled tags on sample docs"],
       ["Entity-link accuracy", "91%", "Extracted entities resolving to graph nodes"],
       ["KG linkage completeness", "100%", "Documents linked to equipment"],
       ["Graph-RCA vs keyword search", "100% vs 17%", "Root-cause identification rate, A/B"],
       ["Automated tests", "33 passing", "Offline pytest suite, no external services"]],
      [34, 20, 46])
body("The 100% versus 17% comparison is the empirical proof of the core thesis: reasoning over topology finds "
     "the upstream cause; keyword search returns the symptom.")
h2("9.1 Evaluation methodology")
body("Every metric is computed live and reproducibly. The benchmark scores each gold question on focus-asset "
     "detection, the presence of the expected root cause, a valid expected citation, a confidence floor, and "
     "the absence of any hallucinated citation - an answer passes only if all hold. Entity extraction is "
     "scored as precision, recall, and F1 against gold-labelled equipment tags on the sample documents. "
     "Knowledge-graph completeness is the share of documents linked to equipment. The graph-versus-search A/B "
     "compares, for each scenario, whether the engine reaches the upstream cause versus whether a top keyword "
     "hit lands on it.")
h2("9.2 Why this answers the brief")
body("The problem statement's Evaluation Focus names entity-extraction accuracy, answer quality on a domain "
     "benchmark, knowledge-graph linkage completeness, time-to-answer versus traditional search, and "
     "compliance-gap detection. Sanket reports a concrete, measured number for each - and surfaces them on the "
     "landing page so a reviewer sees them immediately, labelled 'measured, not claimed'.")

h1("10. Business Impact and ROI")
body("The value is modelled directly from the brief's own statistics. For a mid-size plant, reducing the time "
     "engineers spend searching and preventing even a fraction of unplanned downtime produces a compelling "
     "annual figure.")
table(["Lever", "Basis", "Modelled annual value"],
      [["Labour saved", "40 techs x 14 hrs/wk searching x 60% reduction x Rs 900/hr", "~Rs 1.57 crore"],
       ["Downtime avoided", "20 events/yr x Rs 15 lakh x 20% reduction", "~Rs 0.60 crore"],
       ["Total", "Combined", "~Rs 2.17 crore / year"]],
      [24, 52, 24])
body("The figures are interactive in the product's ROI view, so a plant can model its own assumptions. "
     "Critically, the value scales: because reasoning is bounded to the local k-hop neighbourhood, the cost per "
     "answer is independent of plant size - a 10,000-tag plant answers as fast as the 17-tag demo.")
h2("10.1 Value beyond the headline number")
bullets([
    "Safety: faster, complete-context root-cause reduces the chance of a repeat or escalated failure.",
    "Quality: continuous compliance and deviation flagging catch problems before they reach the customer.",
    "Institutional memory: captured expertise no longer walks out the door with a retirement.",
    "Onboarding: a new engineer can ask the graph what took a veteran years of tacit learning.",
    "Audit readiness: evidence packages are one click away, not a week of document hunting.",
])
body("These are the compounding, hard-to-quantify benefits the problem statement calls out - the reason it "
     "frames fragmentation as a safety and quality problem, not merely an efficiency one.")

h1("11. Scalability and Deployment")
h2("11.1 How it scales")
bullets([
    "Reasoning cost is bounded to the k-hop neighbourhood, not the plant size.",
    "Ingestion is batched with UNWIND and apoc.periodic.iterate - never row-by-row.",
    "The Neo4j path uses indexed lookups and a vector index for semantic search.",
    "Multi-plant partitioning and role-based access are natural extensions of the data model.",
])
h2("11.2 Deployment modes")
bullets([
    "Demo / offline: in-memory store + deterministic engine, zero external services (SANKET_FORCE_MEMSTORE=1).",
    "Full: Neo4j 5.x (via Docker) for the knowledge graph + a Groq API key for the LLM agent.",
    "The frontend is a single static file served by FastAPI - no build step.",
])
h2("11.3 Cost and latency")
body("A deterministic answer is sub-millisecond. An LLM-agent answer is bounded by a small number of tool "
     "rounds (roughly 3,200 tokens, on the order of a dollar per thousand queries on Groq). Entity extraction "
     "runs at roughly three milliseconds per document.")
h2("11.4 Reliability and graceful degradation")
body("The system is designed to keep working when a dependency fails. If Neo4j is unreachable, it falls back "
     "to the in-memory store; if no LLM key is present, the deterministic engine answers; the /health endpoint "
     "reports which mode is live and the store counts, so a broken state is caught before it reaches a user. "
     "The frontend shows clear degraded states rather than blank screens.")
h2("11.5 Observability and data governance")
body("Every query and tool trace can be logged for a reasoning replay, giving operators and auditors a "
     "complete record of how an answer was reached. Because the platform runs fully on-premise, no plant data "
     "needs to leave the site; data residency, retention, and access can be governed entirely within the "
     "organisation's own boundary.")

h1("12. Security, Trust and Enterprise Readiness")
bullets([
    "Trust by construction: computed confidence and verified citations prevent silent hallucination.",
    "Role awareness: an Operator / Engineer / Auditor switcher demonstrates role-scoped experiences; "
    "row-level scoping and SSO are the enterprise extensions.",
    "Auditability: every answer is reproducible (deterministic engine) and every claim traces to a document.",
    "Data residency: the platform runs fully on-premise; no data need leave the plant.",
    "Hardened basics: explicit CORS, robust health checks, and graceful degradation when a dependency is down.",
])

h1("13. Testing and Quality Assurance")
body("Correctness is engineered, not hoped for. A suite of 33 automated tests runs entirely offline (no "
     "database, no API key) and covers the store, the confidence engine, the citation verifier, the RCA "
     "engine, compliance, lessons, the ML predictor, ingestion, the copilot, the knowledge graph, evaluation, "
     "and every API endpoint. A deterministic benchmark harness scores answer quality on a gold question set. "
     "Because the core is deterministic, the same input always yields the same output - so a regression is "
     "caught immediately.")
h2("13.1 What the tests guarantee")
bullets([
    "The demo scenarios never silently break - each is asserted (focus asset, expected mention, valid citation).",
    "No hallucinated citations - the verifier is tested against a fabricated ID.",
    "Confidence is monotonic in evidence strength - strong evidence always scores higher than weak.",
    "Entity extraction excludes standards fragments (OISD-STD-130 is not mis-read as a tag).",
    "Every endpoint returns the expected status and shape.",
])
callout("Run it yourself: python -m pytest -q (33 tests) and python scripts/run_benchmark.py (10/10). No "
        "external services required.")

h1("14. Comparison and Differentiation")
body("Sanket occupies a different position from the tools a plant already has. The table below contrasts it "
     "with the three closest categories.")
table(["Capability", "CMMS dashboard", "Generic AI copilot", "Sanket AI"],
      [["Cross-system knowledge", "Single system", "Whatever was retrieved", "Unified graph, all systems"],
       ["Reasons over asset connectivity", "No", "No", "Yes - P&ID traversal"],
       ["Citations", "N/A", "Often unverified", "Verified against the graph"],
       ["Confidence", "N/A", "Model-asserted", "Computed from evidence"],
       ["Compliance mapping", "Manual", "No", "Automated clause-to-evidence"],
       ["Works offline / on-prem", "Varies", "Usually cloud", "Yes, zero external services"]],
      [28, 22, 24, 26])
body("The differentiation is not a longer feature list - it is a different substrate. Everything follows from "
     "reasoning over the plant's connectivity, with computed trust.")

h1("15. Risks, Limitations and Mitigations")
body("An honest assessment strengthens the case. The current prototype has deliberate scope boundaries; each "
     "has a clear mitigation and roadmap path.")
table(["Limitation", "Mitigation / roadmap"],
      [["Demo runs on a seeded corpus, not a live plant feed", "Ingestion pipeline is real; connect a folder/webhook and Neo4j for live data"],
       ["P&ID topology is authored, not yet parsed from drawings", "CV parsing (symbol + line detection) is the top ingestion roadmap item"],
       ["Entity extraction is regex + vocabulary (no deep NLP)", "Deterministic by design (measurable); an LLM refinement pass is optional"],
       ["Retrieval is keyword-ranked, not vector", "Vector index (BGE-M3) is already scaffolded on the Neo4j path"],
       ["LLM agent needs an API key and can be slower", "Deterministic engine is the trustworthy default; LLM is an enhancement"],
       ["Compliance clauses are a representative subset", "Full clause libraries are a data-only extension"]],
      [40, 60])

h1("16. Technology Stack")
table(["Layer", "Technology"],
      [["Language / runtime", "Python 3.13, async FastAPI + Uvicorn"],
       ["Knowledge graph", "Neo4j 5.x (optional) with an in-memory fallback store"],
       ["LLM / agent", "Groq llama-3.3-70b via LangGraph (optional; deterministic core works without it)"],
       ["ML", "scikit-learn RandomForest (UCI AI4I) as a predictive tool"],
       ["Frontend", "Single-file HTML - Cytoscape.js (graphs), Marked.js (markdown), SSE, SVG infographics"],
       ["Testing", "pytest - 33 offline tests; deterministic benchmark harness"],
       ["Ontology", "ISO 14224, ISA-95, ISO 10816; OISD / Factory Act / PESO / API / CPCB clauses"]],
      [26, 74])

h1("17. Roadmap and Future Additions")
body("Sanket already ships all five pillars end-to-end. The roadmap deepens each and hardens the platform for "
     "production. Items are grouped by theme; the highest-impact near-term work is listed first within each.")
h2("17.1 Ingestion and knowledge graph")
bullets([
    "Native PDF parsing with page-level provenance, and P&ID image parsing (computer vision: symbol and line "
    "detection) to digitise drawings automatically.",
    "OCR for scanned forms; spreadsheet and email-archive bulk import.",
    "Streaming, incremental ingestion (watch a folder or webhook) so the graph updates continuously.",
    "Entity resolution and de-duplication; per-entity extraction confidence with a human review queue.",
])
h2("17.2 Reasoning and analytics")
bullets([
    "Vector / semantic retrieval and conversational memory for the copilot.",
    "Fault-tree and Ishikawa auto-generation; FMEA and Bowtie templates.",
    "Predictive maintenance schedule optimisation and multi-equipment RCA.",
    "Live sensor-feed integration for real-time operating conditions.",
])
h2("17.3 Compliance and lessons-learned")
bullets([
    "Full clause-text libraries and agentic auto-audit (point at a unit -> complete evidence pack).",
    "Statistical process control for quality-deviation prediction before escalation.",
    "Integration with external incident databases; near-miss pattern mining.",
    "Proactive push notifications to field teams.",
])
h2("17.4 Scale, security and platform")
bullets([
    "Async pooling, a job queue for heavy extraction, multi-plant / multi-tenant partitioning.",
    "Role-based access control, SSO, full provenance and audit trails, PII redaction on ingestion.",
    "Mobile PWA hardening, QR-scan-to-history for field technicians, and a keyboard command palette.",
])
h2("17.5 Near-term priorities")
body("If the platform advanced in one direction next, it would be live document ingestion: real PDF parsing "
     "with provenance, computer-vision P&ID digitisation, and streaming updates so the graph stays current as "
     "records arrive. This closes the loop from a static demo corpus to a living plant brain, and it is the "
     "single change that most increases real-world value.")
h2("17.6 Deliverables status")
table(["Deliverable", "Status"],
      [["Working prototype", "Complete - 10-view platform, 33 tests passing, runs offline"],
       ["Architecture", "Complete - this document and the in-app live architecture view"],
       ["Presentation deck", "Prepared - rubric-aligned slide specification"],
       ["Demo video", "Scripted - a timed 6-minute script with speak/show cues"]],
      [34, 66])

h1("18. Conclusion")
body("Search gives you documents. Sanket AI gives you answers - cited, computed, and connected across every "
     "system a plant runs on. By making the plant's own physical topology the substrate the AI reasons over, "
     "it turns fragmented knowledge into a structural advantage: safer operations, faster decisions, and "
     "institutional knowledge that can no longer walk out the door. It is a working platform today, validated "
     "with measured metrics, and architected to scale. This is the unified asset and operations brain.")
callout("Sanket AI - Team IIITDards - ET AI Hackathon 2.0 - Problem Statement 8. Five pillars live, 33 tests "
        "green, runs with zero external services.")

h1("Appendix A: API Reference")
table(["Endpoint", "Purpose"],
      [["GET /health", "Status, RCA mode, store backend + counts"],
       ["GET /graph/equipment", "P&ID nodes + edges (Cytoscape)"],
       ["GET /graph/knowledge/{tag}", "Multi-entity knowledge graph around an asset"],
       ["GET /rca/stream?query=", "SSE diagnosis (tool calls, tokens, meta)"],
       ["POST /rca/query", "Non-streaming diagnosis (JSON)"],
       ["POST /intel/ask", "Cited Q&A copilot"],
       ["POST /intel/ingest/preview | commit", "Entity extraction; add to graph"],
       ["GET /intel/overview | evaluation", "Command-centre KPIs; validated metrics"],
       ["GET /intel/compliance/plant | {tag}", "Compliance roll-up; per-asset gaps"],
       ["GET /intel/lessons/warnings | patterns", "Proactive warnings; systemic patterns"],
       ["GET /intel/timeline | similar | deviations", "Timeline; similar incidents; SPC deviations"],
       ["GET /intel/roi | cost-model | audit/{tag}", "ROI; cost model; audit evidence pack"],
       ["POST /intel/knowledge/capture", "Knowledge-cliff capture"]],
      [42, 58])

h1("Appendix B: Demo Scenarios")
table(["Query", "Result"],
      [["P-101A pump 47 Hz vibration", "V-201 cavitation, 1 hop upstream, 97% confidence, cited"],
       ["K-501 compressor high vibration", "F-501 lube-oil filter blockage, 97% confidence"],
       ["HE-301 outlet temperature rising", "HE-FOL fouling / reduced heat transfer"],
       ["Which HIGH-criticality equipment is overdue?", "Structural + compliance answer"],
       ["What is the condition and history of P-101A?", "Cited copilot answer, 89% confidence, 4 sources"]],
      [40, 60])
body("Every scenario above runs against the seed corpus (17 assets, 82 documents, 52 inspection logs, 30 work "
     "orders, 7 compliance clauses, 6 sample documents) that ships with the project and is regenerated "
     "deterministically by scripts/generate_seed_data.py.")

h1("Appendix C: Glossary")
table(["Term", "Meaning"],
      [["P&ID", "Piping & Instrumentation Diagram - the map of a plant's equipment and their connections"],
       ["Knowledge graph", "A network of typed entities (equipment, documents, failure modes, people, regulations) and their relationships"],
       ["RCA", "Root-Cause Analysis - determining the underlying cause of a failure or symptom"],
       ["CMMS", "Computerised Maintenance Management System - stores work orders and maintenance history"],
       ["RAG", "Retrieval-Augmented Generation - an LLM answering from retrieved document chunks"],
       ["ISO 14224", "International standard for reliability and maintenance data, incl. failure-mode taxonomy"],
       ["ISA-95", "Standard for enterprise-control integration; defines the area/unit/equipment hierarchy"],
       ["ISO 10816", "Standard for evaluating machine vibration by zones (A good -> D unacceptable)"],
       ["Co-failure correlation", "How often one failure mode statistically precedes or accompanies another"],
       ["Confidence (computed)", "A score derived from evidence (documents, recency, severity, correlation, path)"],
       ["Citation faithfulness", "The share of cited document IDs that actually exist in the knowledge graph"],
       ["Store facade", "The abstraction that makes the graph backend (in-memory or Neo4j) interchangeable"],
       ["SPC", "Statistical Process Control - flagging readings that breach control/alarm limits"],
       ["Knowledge cliff", "The loss of undocumented expertise as experienced staff retire"],
       ["Cavitation", "Vapour-bubble collapse in a valve/pump that causes noise, erosion, and vibration"]],
      [24, 76])

h1("Appendix D: Standards and Ontology Reference")
body("Sanket's domain grounding is what makes its output credible to engineers. The platform references the "
     "following standards; each is used functionally, not decoratively.")
table(["Standard", "Role in Sanket"],
      [["ISO 14224", "Failure-mode taxonomy for pumps, valves, exchangers, compressors, motors, strainers, vessels; co-failure statistics"],
       ["ISA-95", "Area / unit / equipment hierarchy modelled as graph nodes"],
       ["ISO 10816-3", "Vibration severity zones (A-D) for the condition-monitoring gauge"],
       ["OISD-STD-130 / 144", "Inspection of rotating equipment and pressure vessels (India)"],
       ["Factories Act 1948", "Safe condition and fencing of machinery (India)"],
       ["PESO / SMPV(U) Rules", "Pressure-system integrity for hazardous fluids (India)"],
       ["API 610 / 617 / 614", "Rotating-equipment and lube-oil-system reference limits"],
       ["CPCB consent conditions", "Cooling-water discharge quality (India)"]],
      [26, 74])
h2("D.1 Example failure modes")
table(["Code", "Description", "Class"],
      [["PU-C-VIB", "Excessive vibration", "Centrifugal pump"],
       ["VA-C-CAV", "Cavitation", "Control valve"],
       ["HE-FOL", "Fouling / reduced heat transfer", "Heat exchanger"],
       ["CO-C-VIB", "High vibration / rotor instability", "Compressor"],
       ["ST-BLK", "Strainer / filter blockage", "Strainer"],
       ["EM-BRG", "Motor bearing failure", "Electric motor"]],
      [16, 52, 32])

out = "Sanket_AI_Project_Document.pdf"
pdf.output(out)
print(f"  [ok] wrote {out}  (pages: {pdf.page_no()})")
