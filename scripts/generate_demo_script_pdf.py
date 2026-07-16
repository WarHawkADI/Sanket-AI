"""
Generates the Sanket AI demo-video script as a professional PDF.
Run:  python scripts/generate_demo_script_pdf.py
Output: Sanket_AI_Demo_Script.pdf  (project root)
"""
from fpdf import FPDF

ACCENT = (47, 98, 207)       # blue
DARK = (24, 30, 44)
GREY = (90, 100, 115)
LIGHT = (238, 242, 249)
OKG = (21, 130, 95)
WARN = (176, 110, 12)


def s(t: str) -> str:
    """ASCII-safe (core PDF fonts are latin-1)."""
    rep = {"₹": "Rs ", "→": "->", "—": " - ", "–": "-", "‘": "'",
           "’": "'", "“": '"', "”": '"', "…": "...", "×": "x",
           "°": " deg", "µ": "u", "•": "-", "≈": "~", "®": "(R)",
           "‑": "-", "é": "e", "⁄": "/"}
    for a, b in rep.items():
        t = t.replace(a, b)
    return t.encode("latin-1", "replace").decode("latin-1")


SEGMENTS = [
    {"time": "0:00 - 0:35", "title": "OPENING HOOK  |  The Problem", "dur": "35s",
     "speak": "An engineer gets an alarm - a critical pump is vibrating. To diagnose it, she has to open "
              "seven disconnected systems: P&IDs in one, work orders in another, inspection logs in a third. "
              "In asset-intensive industry, professionals spend 35% of their time just searching for information "
              "that already exists - and that fragmentation drives up to 22% of unplanned downtime. The knowledge "
              "exists. It's just scattered. Sanket AI is the brain that connects it.",
     "show": ["Title card over a dark P&ID backdrop: \"Sanket AI - Industrial Knowledge Intelligence\".",
              "Quick 3-second montage suggesting scattered systems (tabs / folders flicking).",
              "Fade into the Sanket AI Command Centre loading."],
     "tip": "Keep the tone calm and serious. Land the two numbers (35%, 22%) - they are the brief's own."},

    {"time": "0:35 - 1:05", "title": "THE INSIGHT  |  Why this is different", "dur": "30s",
     "speak": "Most tools would answer with a keyword search. But search finds documents - it can't reason about "
              "a pipe. A pump's vibration can't be explained without knowing that a valve two nodes upstream is "
              "cavitating. So we made the plant's physical topology the thing the AI reasons over - not a filter, "
              "the substrate.",
     "show": ["Command Centre in view. Slowly pan across the KPI tiles (17 assets, 82 documents, 37% compliance).",
              "Hover the 'Validated evaluation metrics' row so it is clearly visible."],
     "tip": "This is your one-sentence differentiator. Say 'the substrate' with weight."},

    {"time": "1:05 - 1:35", "title": "COMMAND CENTRE  |  One brain, five capabilities", "dur": "30s",
     "speak": "This is the command centre. One brain, five capabilities - ingestion, a knowledge copilot, "
              "root-cause analysis, compliance, and failure intelligence - across 17 assets and 82 live documents. "
              "And these numbers are measured, not claimed: 100% on our benchmark, 100% citation faithfulness, "
              "91% entity-link accuracy.",
     "show": ["Cursor-circle the five pillar cards at the bottom ('Five capabilities, one brain').",
              "Cursor-circle the evaluation-metrics row.",
              "Click 'Run a diagnosis' (or the Diagnose icon in the left rail)."],
     "tip": "Reviewers reward validated metrics - linger half a second on that row."},

    {"time": "1:35 - 3:05", "title": "FLAGSHIP DEMO  |  Root-Cause Analysis (the core)", "dur": "90s",
     "speak": "Let's diagnose that alarm - P-101A, 47-hertz vibration. Watch what happens. Sanket doesn't search; "
              "it traverses the P&ID. It walks upstream from the pump, pulls every inspection log and work order for "
              "the neighbours, and correlates ISO-14224 failure statistics. In under four seconds it finds the real "
              "cause - and it is not the pump. It's V-201, a control valve one hop upstream, cavitating - and that "
              "cavitation transmits as vibration downstream. Every claim is cited to a real document. And this "
              "confidence, 97%, isn't invented by the model - it's computed from evidence: four corroborating "
              "documents, a high-severity finding, the ISO correlation, and a confirmed physical path. Here's the "
              "live sensor - vibration in ISO-10816 Zone C, climbing toward the trip line. Left alone, this pump "
              "trips in about five weeks.",
     "show": ["In Diagnose, click the 'Pump vibration' sample query, then Analyze.",
              "Narrate as the trace panel fires tools and the P&ID lights up: P-101A red, V-201 amber, red causal path.",
              "Causal-chain ribbon appears: V-201 (root cause) -> P-101A (symptom), r 0.72.",
              "Point at the metric strip (answer time, nodes, docs, cited).",
              "Scroll to the ISO-10816 zone gauge + vibration trend (rising into the alarm line).",
              "Scroll to the confidence meter; hover the evidence breakdown chips.",
              "Click one amber citation chip -> the source-document drawer slides open. Close it."],
     "tip": "This is the money shot. Slow down. Let the graph animation and the confidence breakdown breathe."},

    {"time": "3:05 - 3:55", "title": "PILLAR 1  |  Ingestion + Knowledge Graph", "dur": "50s",
     "speak": "Where does this knowledge come from? Any document. Here's a raw inspection report - it could be a "
              "PDF, an email, or a scanned form. Sanket extracts the entities the moment it lands: equipment tags, "
              "dates, parameters, personnel, and regulatory references - and links them into the knowledge graph, "
              "at 97% F-one. And this is that graph: not just equipment, but documents, failure modes, the people "
              "who recorded them, and the regulations that govern them - one connected brain.",
     "show": ["Left rail -> Ingest. Click a sample document (Inspection Report), then 'Extract entities'.",
              "Show the extracted entity chips; point out the green ones (linked to the graph).",
              "Left rail -> Graph. The knowledge graph renders: P-101A at centre, rings of Equipment / Documents / "
              "Failure modes / People / Regulations.",
              "Click one node to open its detail panel."],
     "tip": "Emphasise the heterogeneity ('PDF, email, scanned form') - that is the brief's Pillar 1."},

    {"time": "3:55 - 4:45", "title": "PILLARS 2 & 4  |  Copilot + Compliance", "dur": "50s",
     "speak": "Any engineer - or a field technician on a phone - can just ask. 'What is the condition and history "
              "of P-101A?' A cited answer in seconds, drawn from the whole corpus. And compliance is continuous: "
              "Sanket maps OISD, the Factory Act, PESO and ISO clauses against every asset's actual evidence, and "
              "flags the gaps automatically. This plant is at 37%, with nine high-severity gaps - and one click "
              "generates the audit evidence package.",
     "show": ["Left rail -> Ask. Click the chip 'What is the condition and history of P-101A?' -> cited answer + sources.",
              "Left rail -> Comply. Show plant compliance 37% and the gaps grid.",
              "Click an asset (e.g. K-501) -> clause-by-clause status with evidence / gaps."],
     "tip": "Say 'on a phone' while the answer renders - it plants the mobile / field-tech point."},

    {"time": "4:45 - 5:10", "title": "PILLAR 5  |  The Knowledge Cliff", "dur": "25s",
     "speak": "And the hardest problem of all: a quarter of India's experienced engineers retire this decade, "
              "taking undocumented know-how with them. Sanket captures it. A retiring foreman's trick - 'always "
              "re-clearance the impeller after a cavitation event' - becomes a permanent graph node, instantly "
              "queryable by the next shift.",
     "show": ["Left rail -> Capture. Fill the short form (tag P-101A, the foreman's tip) and submit.",
              "The capture appears in the list on the right - now part of the graph."],
     "tip": "This is the emotional core of the brief. Deliver it with conviction."},

    {"time": "5:10 - 5:35", "title": "BUSINESS IMPACT  |  What it's worth", "dur": "25s",
     "speak": "What is it worth? For a mid-size plant, cutting search time and preventing even a fraction of "
              "downtime is worth over two crore rupees a year - and it scales, because the reasoning cost is "
              "independent of plant size.",
     "show": ["Left rail -> ROI. Show the Rs 2.17 Cr headline and the labour / downtime split.",
              "Optional: flash the Arch view for 2 seconds ('runs with zero external services')."],
     "tip": "The rupee number is the Business-Impact (25%) moment. State it plainly and confidently."},

    {"time": "5:35 - 6:00", "title": "CLOSING HOOK  |  The vision", "dur": "25s",
     "speak": "Search gives you documents. Sanket gives you answers - cited, computed, and connected across every "
              "system a plant runs on. It turns fragmented knowledge into a structural advantage: safer, faster, "
              "and impossible to lose. This is the unified asset and operations brain. This is Sanket AI.",
     "show": ["Return to the Command Centre.",
              "End title card: 'Sanket AI - Industrial Knowledge Intelligence' + tagline + 'Team IIITDards - Problem Statement 8'."],
     "tip": "Match the opening's tone. End on the product name, silent for one beat, then cut."},
]

CHECKLIST = [
    "Run offline & seeded: set SANKET_FORCE_MEMSTORE=1, then uvicorn backend.main:app --port 8000.",
    "Record at 1440p or 1080p, browser at 100% zoom, cursor movements slow and deliberate.",
    "Pre-stage each segment with a deep-link (below) so transitions are instant - no fumbling.",
    "Do the flagship RCA live and unedited - the graph animation + streaming is the proof it is real.",
    "Keep total voiceover ~700 words; rehearse to hit 6:00 exactly. Trim adjectives, not demos.",
    "Backup: keep a pre-recorded run of the RCA in case of any hiccup on the day.",
    "Optional lower-thirds captions for the key numbers: 35%, 22%, 97%, Rs 2.17 Cr, 100% faithful.",
]

DEEPLINKS = [
    ("Flagship RCA (auto-runs)", "/ui/index.html?q=P-101A%2047Hz%20vibration%20spike.%20Find%20root%20cause."),
    ("Copilot answer (auto-runs)", "/ui/index.html?ask=What%20is%20the%20condition%20and%20history%20of%20P-101A"),
    ("Any view", "/ui/index.html?view=  (overview | diagnose | ingest | graph | comply | monitor | roi | capture | architecture)"),
]


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, s("Sanket AI - Demo Video Script (6:00)"), align="L")
        self.cell(0, 8, s("ET AI Hackathon 2.0"), align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, s(f"Page {self.page_no()}"), align="C")


pdf = PDF(format="A4")
pdf.set_auto_page_break(auto=True, margin=16)
pdf.set_margins(16, 16, 16)
W = 210 - 32  # usable width

# ---- COVER ----
pdf.add_page()
pdf.set_fill_color(*ACCENT)
pdf.rect(0, 0, 210, 62, "F")
pdf.set_xy(16, 18)
pdf.set_text_color(255, 255, 255)
pdf.set_font("Helvetica", "B", 26)
pdf.cell(0, 12, s("Sanket AI"), ln=1)
pdf.set_x(16)
pdf.set_font("Helvetica", "", 13)
pdf.cell(0, 8, s("Industrial Knowledge Intelligence - Demo Video Script"), ln=1)
pdf.set_x(16)
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, s("6:00 runtime  |  Team IIITDards  |  ET AI Hackathon 2.0  |  Problem Statement 8"), ln=1)

pdf.set_xy(16, 74)
pdf.set_text_color(*DARK)
pdf.set_font("Helvetica", "I", 11)
pdf.multi_cell(W, 6, s("Logline: A maintenance engineer opens seven systems to explain one pump alarm. "
                       "Sanket AI connects them - traversing the plant's own topology to return a cited, "
                       "computed root cause in seconds."))
pdf.ln(4)
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(*ACCENT)
pdf.cell(0, 7, s("HOW TO READ THIS SCRIPT"), ln=1)
pdf.set_text_color(*DARK)
pdf.set_font("Helvetica", "", 10)
pdf.multi_cell(W, 5.5, s("Each segment has a timecode, a SPEAK block (voiceover, read aloud), and a SHOW block "
                         "(exactly what to do on screen). TIP lines are delivery notes. A recording checklist and "
                         "deep-link cheat-sheet are on the last page."))
pdf.ln(3)
# structure summary bar
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(*ACCENT)
pdf.cell(0, 7, s("STRUCTURE"), ln=1)
pdf.set_font("Helvetica", "", 9.5)
pdf.set_text_color(*GREY)
for seg in SEGMENTS:
    pdf.set_x(16)
    pdf.cell(26, 5.5, s(seg["time"]))
    pdf.cell(0, 5.5, s(seg["title"].split("  |  ")[0] + "  -  " + seg["title"].split("  |  ")[-1]), ln=1)

# ---- SEGMENTS ----
pdf.add_page()
for seg in SEGMENTS:
    # header bar
    pdf.set_fill_color(*ACCENT)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(30, 9, s(" " + seg["time"]), fill=True)
    pdf.cell(W - 46, 9, s(seg["title"]), fill=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(16, 9, s(seg["dur"] + " "), fill=True, align="R", ln=1)
    pdf.ln(1.5)
    # SPEAK
    pdf.set_text_color(*ACCENT)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 6, s("SPEAK  (voiceover)"), ln=1)
    pdf.set_text_color(*DARK)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.multi_cell(W, 5.6, s(seg["speak"]))
    pdf.ln(1.5)
    # SHOW
    pdf.set_text_color(*OKG)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 6, s("SHOW  (on screen)"), ln=1)
    pdf.set_text_color(*DARK)
    pdf.set_font("Helvetica", "", 10)
    for a in seg["show"]:
        pdf.set_x(16)
        pdf.cell(5, 5.4, s("-"))
        pdf.multi_cell(W - 5, 5.4, s(a))
    # TIP
    if seg.get("tip"):
        pdf.ln(1)
        pdf.set_text_color(*WARN)
        pdf.set_font("Helvetica", "BI", 9.5)
        pdf.set_x(16)
        pdf.multi_cell(W, 5.2, s("TIP: " + seg["tip"]))
    pdf.ln(4)

# ---- LAST PAGE: checklist + deep links ----
pdf.add_page()
pdf.set_text_color(*ACCENT)
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 9, s("Recording checklist"), ln=1)
pdf.ln(1)
pdf.set_text_color(*DARK)
pdf.set_font("Helvetica", "", 10.5)
for c in CHECKLIST:
    pdf.set_x(16)
    pdf.cell(5, 5.6, s("-"))
    pdf.multi_cell(W - 5, 5.6, s(c))
    pdf.ln(0.5)

pdf.ln(4)
pdf.set_text_color(*ACCENT)
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 9, s("Deep-link cheat-sheet"), ln=1)
pdf.ln(1)
pdf.set_text_color(*DARK)
for label, url in DEEPLINKS:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_x(16)
    pdf.cell(0, 5.6, s(label), ln=1)
    pdf.set_font("Courier", "", 9)
    pdf.set_text_color(*GREY)
    pdf.set_x(16)
    pdf.multi_cell(W, 5, s(url))
    pdf.set_text_color(*DARK)
    pdf.ln(1)

pdf.ln(4)
pdf.set_draw_color(*ACCENT)
pdf.set_line_width(0.5)
pdf.line(16, pdf.get_y(), 16 + W, pdf.get_y())
pdf.ln(3)
pdf.set_font("Helvetica", "I", 9.5)
pdf.set_text_color(*GREY)
pdf.multi_cell(W, 5, s("Word count of voiceover ~700 words -> ~6:00 at a measured pace. Every SHOW action maps to "
                       "a real feature in the running product. Break a leg."))

out = "Sanket_AI_Demo_Script.pdf"
pdf.output(out)
print(f"  [ok] wrote {out} ({len(SEGMENTS)} segments)")
