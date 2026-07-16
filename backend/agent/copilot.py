"""
Expert Knowledge Copilot.

Answers operational / maintenance / engineering / regulatory questions across the
whole document corpus — with source citations, a computed confidence score, and
direct links to the originating documents (the brief's pillar #2). Deterministic
retrieval + synthesis so it works with no LLM; upgrades to the agent when a key
is present.
"""
from __future__ import annotations

import re

from backend.agent.confidence import Evidence, score
from backend.agent import citations

TAG_RE = re.compile(r"\b([A-Z]{1,3}-\d{2,4}[A-Z]?)\b")


def answer(query: str, store) -> dict:
    tags = [t for t in dict.fromkeys(TAG_RE.findall(query.upper())) if store.get_equipment(t)]
    docs = _retrieve(query, store, tags)
    clauses = _match_clauses(query, store)

    body, ev_ids, sources = _synthesize(query, store, tags, docs, clauses)

    conf = score(Evidence(doc_ids=ev_ids, severities=[d.get("severity", "") for d in docs[:4]],
                          latest_date=max((d.get("date", "") for d in docs), default=""),
                          correlation=0.0, path_confirmed=bool(docs or clauses)))
    verified = citations.verify(body, store.document_ids())
    body = citations.annotate(body, store.document_ids())
    return {"answer": body, "confidence": conf["confidence"],
            "confidence_breakdown": conf["breakdown"], "citations": verified,
            "sources": sources, "focus_tag": tags[0] if tags else None}


def _retrieve(query, store, tags):
    docs = store.search(query, tags=tags or None, limit=6)
    if not docs and tags:                       # fall back to that asset's history
        docs = store.documents_for(tags[0], limit=6)
    return docs


def _match_clauses(query, store):
    q = query.lower()
    hits = []
    for c in store.compliance_clauses():
        hay = (c["standard"] + " " + c["title"] + " " + c["requirement"]).lower()
        if any(w in hay for w in q.split() if len(w) > 3) or c["standard"].lower() in q:
            hits.append(c)
    return hits[:3]


def _synthesize(query, store, tags, docs, clauses):
    lines, ev_ids, sources = [], [], []

    if tags:
        eq = store.get_equipment(tags[0])
        lines.append(f"## {tags[0]} — {eq.get('name','')}")
        lines.append(f"{eq.get('type','').replace('_',' ').title()} · {eq.get('criticality','')} criticality · "
                     f"area {eq.get('area','')}. {eq.get('description','')}\n")

    if docs:
        lines.append("**From the maintenance & inspection records:**")
        for d in docs[:4]:
            snip = (d.get("content") or d.get("title") or "").replace("\n", " ").strip()[:150]
            lines.append(f"- `[{d['id']}]` ({d.get('type','').replace('_',' ').title()}, {d.get('date','')}) — {snip}")
            ev_ids.append(d["id"])
            sources.append({"id": d["id"], "type": d.get("type", ""), "title": d.get("title", ""), "date": d.get("date", "")})
        lines.append("")

    if clauses:
        lines.append("**Applicable regulatory requirements:**")
        for c in clauses:
            lines.append(f"- **{c['standard']}** — {c['requirement']} _(gap severity: {c.get('severity_on_gap','')})_")
        lines.append("")

    if not docs and not clauses:
        lines.append("No matching records were found in the knowledge graph for that question. "
                     "Try naming an equipment tag (e.g. P-101A), a standard (e.g. OISD-STD-130), "
                     "or a failure mode (e.g. cavitation).")

    return "\n".join(lines), ev_ids, sources
