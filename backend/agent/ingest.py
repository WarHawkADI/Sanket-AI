"""
Universal Document Ingestion & Entity Extraction.

Processes heterogeneous document text (inspection reports, emails, OEM manuals,
regulatory forms, incident records, handover notes) and extracts the entities
the brief names — equipment tags, process parameters, regulatory references,
personnel, dates — then links them into the knowledge graph.

Extraction is deterministic (regex + the graph's own vocabulary), so it runs
with no LLM and its accuracy is measurable. An LLM pass can refine it when a key
is present, but the demo never depends on one.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

TAG_RE = re.compile(r"\b([A-Z]{1,3}-\d{2,4}[A-Z]?)\b")
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
PARAM_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?(mm/s|Hz|°C|deg\s?C|bar|dB|rpm|%|K|µm|barg|m3/h)\b", re.IGNORECASE)
REG_RE = re.compile(
    r"\b(OISD[- ]STD[- ]?\d+|OISD[- ]?\d+|ISO\s?\d{3,5}(?:-\d)?|API\s?\d{3}|Factories?\s+Act(?:\s+1948)?"
    r"(?:\s+§?\s?\d+)?|PESO|SMPV(?:\(U\))?|CPCB|IS\s?\d{3,5}|TEMA)\b", re.IGNORECASE)


def extract_entities(text: str, store) -> dict:
    """Extract typed entities and note which resolve to existing graph nodes."""
    known_tags = {e["tag"] for e in store.all_equipment()}
    known_people = set(store.personnel())
    fm_terms = _failure_terms(store)

    # equipment tags (exclude standards fragments like STD-130 from OISD-STD-130)
    _NOT_TAG = {"STD", "ISO", "API", "IS", "TEMA", "SMPV", "OISD"}
    equipment = []
    for m in dict.fromkeys(TAG_RE.findall(text)):
        if m.split("-")[0] in _NOT_TAG:
            continue
        equipment.append({"value": m, "linked": m in known_tags,
                          "resolves_to": m if m in known_tags else None})

    # dates
    dates = list(dict.fromkeys(DATE_RE.findall(text)))

    # parameters (value + unit)
    parameters = [f"{v} {u}" for v, u in PARAM_RE.findall(text)]
    parameters = list(dict.fromkeys(parameters))

    # regulatory references
    regs = []
    for m in dict.fromkeys(x.strip() for x in REG_RE.findall(text)):
        canon = _canon_reg(m)
        regs.append({"value": m, "linked": canon in {c["standard"] for c in store.compliance_clauses()},
                     "resolves_to": canon})

    # personnel — match known names, plus role-tagged names (Inspector:/Reported by:/From:)
    personnel = []
    for name in known_people:
        if name.lower() in text.lower():
            personnel.append({"value": name, "linked": True})
    for m in re.findall(r"(?:Inspector|Reported by|Operator|Prepared by|Technician|From)\s*[:>]?\s*"
                        r"([A-Z][a-z]+\s[A-Z][a-z]+)", text):
        if not any(p["value"] == m for p in personnel):
            personnel.append({"value": m, "linked": m in known_people})

    # failure modes / mechanisms mentioned
    failure_modes = []
    low = text.lower()
    for term, code in fm_terms.items():
        if term in low and not any(f["value"] == term for f in failure_modes):
            failure_modes.append({"value": term, "resolves_to": code})

    return {"equipment": equipment, "dates": dates, "parameters": parameters,
            "regulatory": regs, "personnel": personnel, "failure_modes": failure_modes}


def preview(text: str, store) -> dict:
    """Extract entities + a linkage summary (the cross-document discovery signal)."""
    ents = extract_entities(text, store)
    total = sum(len(ents[k]) for k in ("equipment", "dates", "parameters", "regulatory", "personnel", "failure_modes"))
    linked = (sum(1 for e in ents["equipment"] if e["linked"])
              + sum(1 for r in ents["regulatory"] if r["linked"])
              + sum(1 for p in ents["personnel"] if p["linked"]))
    linkable = len(ents["equipment"]) + len(ents["regulatory"]) + len(ents["personnel"])
    return {"entities": ents, "entity_count": total,
            "linked_to_graph": linked, "linkable": linkable,
            "linkage_rate": round(linked / linkable, 3) if linkable else 0.0}


def commit(text: str, title: str, doc_type: str, store) -> dict:
    """Add the document to the knowledge graph, linked to every equipment it mentions."""
    ents = extract_entities(text, store)
    tags = [e["value"] for e in ents["equipment"] if e["linked"]]
    date = ents["dates"][0] if ents["dates"] else datetime.now().strftime("%Y-%m-%d")
    doc = {"id": "DOC-" + uuid.uuid4().hex[:8].upper(), "type": "INGESTED",
           "subtype": doc_type, "title": title or "Ingested document",
           "date": date, "content": text[:4000], "priority": "", "status": "", "severity": "",
           "source": "ingested"}
    store.add_document(doc, tags)
    return {"document": {k: doc.get(k) for k in ("id", "type", "subtype", "title", "date")},
            "linked_equipment": tags, "entities_extracted": preview(text, store)["entity_count"]}


# ── helpers ──────────────────────────────────────────────────────────────────
def _failure_terms(store) -> dict:
    """Map lowercase failure/mechanism terms → their ISO-14224 code."""
    terms = {}
    fm = getattr(store, "failure_modes", None)
    if isinstance(fm, dict):
        for code, m in fm.items():
            desc = (m.get("description") or "").lower()
            for w in ("cavitation", "vibration", "fouling", "bearing", "leak", "surge", "blockage", "corrosion"):
                if w in desc or w in (m.get("mechanism") or "").lower():
                    terms.setdefault(w, code)
    # always-on domain terms
    for w, c in {"cavitation": "VA-C-CAV", "vibration": "PU-C-VIB", "fouling": "HE-FOL",
                 "bearing": "PU-C-BRG", "blockage": "ST-BLK", "surge": "CO-C-SRG"}.items():
        terms.setdefault(w, c)
    return terms


def _canon_reg(raw: str) -> str:
    r = raw.upper().replace("  ", " ").strip()
    if r.startswith("OISD"):
        num = re.search(r"\d+", r)
        return f"OISD-STD-{num.group()}" if num else "OISD-STD"
    if r.startswith("ISO"):
        return "ISO " + re.search(r"\d{3,5}(?:-\d)?", r).group() if re.search(r"\d", r) else r
    if r.startswith("API"):
        return "API " + re.search(r"\d{3}", r).group()
    if "FACTOR" in r:
        return "Factories Act 1948 §21"
    if "PESO" in r or "SMPV" in r:
        return "PESO / SMPV(U) Rules"
    if "CPCB" in r:
        return "CPCB Consent Conditions"
    return raw
