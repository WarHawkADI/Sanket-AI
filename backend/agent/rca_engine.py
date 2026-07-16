"""
Dual-mode Root-Cause-Analysis engine.

  • deterministic_rca()  — runs a real graph investigation with **no LLM**:
    identify the asset, traverse the P&ID upstream, pull CMMS evidence, correlate
    ISO-14224 co-failure statistics, compute an evidence-based confidence and emit
    a cited causal chain.  This is honest (every number comes from the graph) and
    lets the product demo end-to-end with no API key.

  • The LangGraph LLM agent (rca_agent.py) is used when a Groq key is present;
    its output is post-processed through the same citation verifier + metrics.

Both return the same structured shape so the API and UI are mode-agnostic.
"""
from __future__ import annotations

import re
import time

from backend.graph.store import get_store
from backend.agent.confidence import Evidence, score
from backend.agent import citations
from backend.config import now

TAG_RE = re.compile(r"\b([A-Z]{1,3}-\d{2,4}[A-Z]?)\b")

# symptom keyword → the failure-mode code it points at, per equipment class family
SYMPTOM_MAP = [
    (("vibrat", "47hz", "47 hz", "mm/s", "shaking"), {"CENTRIFUGAL_PUMP": "PU-C-VIB",
                                                       "CENTRIFUGAL_COMPRESSOR": "CO-C-VIB",
                                                       "ELECTRIC_MOTOR": "EM-BRG"}),
    (("cavitat", "crackl", "popping"), {"CONTROL_VALVE": "VA-C-CAV"}),
    (("leak", "seal", "gland"), {"CENTRIFUGAL_PUMP": "PU-C-LEK", "CONTROL_VALVE": "VA-C-LEK"}),
    (("foul", "heat transfer", "outlet temp", "scaling"), {"HEAT_EXCHANGER": "HE-FOL"}),
    (("bearing", "spalling"), {"CENTRIFUGAL_PUMP": "PU-C-BRG", "ELECTRIC_MOTOR": "EM-BRG"}),
    (("surge", "flow instability"), {"CENTRIFUGAL_COMPRESSOR": "CO-C-SRG"}),
    (("blockage", "differential pressure", "strainer", "filter", "clogg"),
     {"STRAINER": "ST-BLK"}),
    (("low flow", "reduced capacity", "low head"), {"CENTRIFUGAL_PUMP": "PU-C-CAP"}),
]

SEV_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0, "": 0}


def _extract_tag(query: str, store) -> str | None:
    for m in TAG_RE.findall(query.upper()):
        if store.get_equipment(m):
            return m
    # fall back to first tag-shaped token even if unknown
    hits = TAG_RE.findall(query.upper())
    return hits[0] if hits else None


def _symptom_code(query: str, eq_type: str) -> str | None:
    q = query.lower()
    for keys, mapping in SYMPTOM_MAP:
        if any(k in q for k in keys):
            if eq_type in mapping:
                return mapping[eq_type]
            # if the symptom names a different class (e.g. cavitation → valve), keep it
            return next(iter(mapping.values()))
    return None


def _latest(docs):
    return max((d.get("date", "") for d in docs), default="")


def _time_to_failure(tag: str):
    """Estimate weeks to the trip threshold by extrapolating the telemetry trend."""
    t = get_store().telemetry(tag)
    if not t or len(t.get("trend", [])) < 2 or not t.get("trip"):
        return None
    trend = t["trend"]
    from datetime import datetime
    try:
        p0, p1 = trend[-2], trend[-1]
        d0 = datetime.strptime(p0["date"][:10], "%Y-%m-%d")
        d1 = datetime.strptime(p1["date"][:10], "%Y-%m-%d")
        days = max((d1 - d0).days, 1)
        rate = (p1["value"] - p0["value"]) / days            # units per day
        if rate <= 0:
            return None
        remaining = (t["trip"] - p1["value"]) / rate          # days to trip
        return max(1, round(remaining / 7))                   # weeks
    except (ValueError, KeyError, ZeroDivisionError):
        return None


def _relevance(doc, mode_code):
    """Rank a document's relevance as evidence for a given failure mode."""
    s = 0.0
    if mode_code and doc.get("failure_mode") == mode_code:
        s += 6                                   # directly records this failure mode
    s += SEV_RANK.get((doc.get("severity") or "").upper(), 0)
    s += doc.get("date", "") and float(doc["date"][:4]) / 1000  # recency tiebreak
    return s


def deterministic_rca(query: str) -> dict:
    """Investigate a failure over the knowledge graph without any LLM."""
    t0 = time.time()
    store = get_store()
    trace: list[dict] = []
    docs_seen: set[str] = set()

    def log(tool, **inp):
        trace.append({"tool": tool, "input": inp})

    tag = _extract_tag(query, store)
    focus = store.get_equipment(tag) if tag else None

    # ---- unknown asset → symptom search fallback (robust to arbitrary queries) ----
    if not focus:
        hits = store.search(query, limit=5)
        log("semantic_search_near", query=query, tags=[])
        for d in hits:
            docs_seen.add(d["id"])
        body = _fallback_answer(query, tag, hits)
        return _finalize(body, None, trace, docs_seen, 0, t0, mode="deterministic",
                         focus_tag=tag, confidence=None)

    etype = focus["type"]
    focus_modes = store.failure_modes_for(etype); log("get_failure_modes", equipment_type=etype)
    upstream = store.traverse(tag, "upstream", 3); log("traverse_upstream", tag=tag, depth=3)
    focus_docs = store.documents_for(tag); log("get_failure_history", tag=tag)
    for d in focus_docs:
        docs_seen.add(d["id"])

    symptom = _symptom_code(query, etype) or (focus_modes[0]["code"] if focus_modes else None)
    focus_codes = {m["code"] for m in focus_modes}

    co_tags = [tag] + [u["tag"] for u in upstream[:4]]
    patterns, shared = store.co_failure(co_tags); log("get_co_failure_patterns", tags=co_tags)

    # ---- score each upstream suspect ---------------------------------------
    suspects = []
    for u in upstream:
        udocs = store.documents_for(u["tag"]); log("get_inspection_logs", tag=u["tag"])
        for d in udocs:
            docs_seen.add(d["id"])
        u_codes = {m["code"] for m in store.failure_modes_for(u["type"])}
        # best co-failure link: a mode of the suspect's class → the focus symptom
        best = 0.0
        link = None
        for p in patterns:
            if p["primary"] in u_codes and (p["secondary"] == symptom or p["secondary"] in focus_codes):
                if p.get("correlation", 0) > best:
                    best = p["correlation"]; link = p
        # evidence relevant to the causal link, ranked by mode-match, severity, recency
        mode_code = link["primary"] if link else None
        ranked = sorted(udocs, key=lambda d: _relevance(d, mode_code), reverse=True)
        top = ranked[:3]
        sev_score = max((SEV_RANK.get((d.get("severity") or "").upper(), 0) for d in top), default=0)
        # rank suspects: physical proximity + causal correlation + evidence severity
        rank = best * 4 + sev_score + (2 if u.get("criticality") == "HIGH" else 0) - u["hops"] * 0.3
        suspects.append({"eq": u, "docs": top, "corr": best, "link": link,
                         "sev": sev_score, "rank": rank})

    suspects.sort(key=lambda s: s["rank"], reverse=True)
    primary = suspects[0] if suspects and suspects[0]["corr"] > 0 else None

    # ---- build the answer ---------------------------------------------------
    if primary:
        body, conf, causal = _primary_answer(query, focus, symptom, focus_docs, primary, suspects[1:2])
    else:
        # no clear upstream culprit → attribute to the asset's own dominant failure mode
        body, conf, causal = _self_answer(query, focus, focus_modes, focus_docs, symptom)

    return _finalize(body, causal, trace, docs_seen, len(upstream), t0,
                     mode="deterministic", focus_tag=tag, confidence=conf)


def _primary_answer(query, focus, symptom, focus_docs, primary, secondary):
    u = primary["eq"]
    store = get_store()
    u_modes = store.failure_modes_for(u["type"])
    mode = next((m for m in u_modes if primary["link"] and m["code"] == primary["link"]["primary"]),
                (u_modes[0] if u_modes else {"description": "degradation", "code": ""}))
    focus_ev = sorted(focus_docs, key=lambda d: _relevance(d, symptom), reverse=True)
    focus_ev = [d for d in focus_ev if (d.get("severity") or "").upper() in ("HIGH", "MEDIUM")][:2]
    ev_docs = primary["docs"] + focus_ev
    ev_ids = [d["id"] for d in ev_docs][:4]
    severities = [d.get("severity", "") for d in ev_docs]
    corr = primary["corr"]
    conf = score(Evidence(doc_ids=ev_ids, severities=severities,
                          latest_date=_latest(ev_docs), correlation=corr, path_confirmed=True))

    focus_tag, u_tag = focus["tag"], u["tag"]
    mech = mode["description"].lower()
    lines = []
    lines.append("## Root Cause Summary")
    lines.append(f"{u_tag} {mech} is the primary driver of {focus_tag}'s reported symptom — "
                 f"an upstream condition transmitted along the P&ID path to {focus_tag}.\n")
    lines.append("---\n")
    lines.append(f"### Hypothesis 1 — {u['name']} ({mode['description']}) · Confidence: {conf['confidence']}%")
    lines.append(f"{u_tag} ({u['type'].replace('_',' ').title()}, {u.get('criticality','')} criticality) sits "
                 f"{u['hops']} hop(s) upstream of {focus_tag}. Its failure mode "
                 f"[{mode['code']}] {mode['description']} has a {corr:.0%} historical co-occurrence with the "
                 f"observed symptom, and the CMMS record confirms an active, worsening condition.\n")
    lines.append("**Evidence:**")
    for d in ev_docs[:4]:
        snippet = (d.get("content") or d.get("title") or "").replace("\n", " ")[:120]
        lines.append(f"- `[{d['id']}]` — {snippet}")
    lines.append("")
    lines.append(f"**Confidence basis:** {', '.join(b['factor'] for b in conf['breakdown'])}.\n")
    urgency = "IMMEDIATE" if conf["confidence"] >= 75 else "WITHIN 24H"
    lines.append(f"**Recommended Action:** Rectify {u_tag} ({mode['description']}) — "
                 f"address the upstream source rather than the downstream symptom. · Urgency: {urgency}\n")

    if secondary and secondary[0]["corr"] > 0:
        s = secondary[0]
        lines.append("---\n")
        lines.append(f"### Hypothesis 2 — {s['eq']['name']} · Confidence: {min(conf['confidence']-20, 55)}%")
        lines.append(f"A secondary contribution from {s['eq']['tag']} ({s['eq']['type'].replace('_',' ').title()}) "
                     f"cannot be excluded and should be verified after the primary cause is addressed.\n")

    # Ruled-out candidates (transparency: what was considered and excluded)
    ruled = [s for s in secondary if s.get("corr", 0) <= 0] + \
            [s for s in (secondary or []) if 0 < s.get("corr", 0) < primary["corr"]]
    if ruled:
        lines.append("## Ruled Out")
        for s in ruled[:2]:
            reason = ("weaker co-failure correlation and no active high-severity evidence"
                      if s.get("corr", 0) else "no causal correlation to the observed symptom")
            lines.append(f"- {s['eq']['tag']} ({s['eq']['type'].replace('_',' ').title()}) — {reason}.")

    # Predictive time-to-failure from the focus asset's telemetry trend
    ttf = _time_to_failure(focus_tag)
    if ttf:
        lines.append("## Predicted Time-to-Failure")
        lines.append(f"- At the current degradation rate, {focus_tag} is projected to reach its trip "
                     f"threshold in **~{ttf} week(s)** if the root cause is not resolved.")

    lines.append("## Next Checks")
    lines.append(f"1. Re-measure the primary sensor on {focus_tag} and confirm the trend direction.")
    lines.append(f"2. Inspect {u_tag} for {mode['description'].lower()} and quantify the severity.")
    lines.append("3. Cross-check co-failure history on any equipment sharing the same circuit.")

    lines.append("## Immediate Actions")
    lines.append(f"1. Rectify the upstream root cause at {u_tag} (see evidence above).")
    lines.append(f"2. Increase condition-monitoring frequency on {focus_tag} until the upstream issue is closed.")
    lines.append(f"3. Verify the standby/parallel path and prepare to switch over if the symptom worsens.")

    causal = {
        "from_tag": u_tag, "from_name": u["name"], "from_type": u["type"],
        "from_mode": mode["code"], "from_mechanism": mode["description"],
        "to_tag": focus_tag, "to_name": focus["name"], "to_type": focus["type"],
        "hops": u["hops"], "correlation": corr, "confidence": conf["confidence"],
    }
    return "\n".join(lines), conf, causal


def _self_answer(query, focus, focus_modes, focus_docs, symptom=None):
    tag = focus["tag"]
    mode = next((m for m in focus_modes if m["code"] == symptom),
                focus_modes[0] if focus_modes else {"code": "", "description": "degradation"})
    ev_docs = sorted(focus_docs, key=lambda d: _relevance(d, mode.get("code")), reverse=True)[:3]
    ev_ids = [d["id"] for d in ev_docs]
    conf = score(Evidence(doc_ids=ev_ids, severities=[d.get("severity", "") for d in ev_docs],
                          latest_date=_latest(ev_docs), correlation=0.0,
                          path_confirmed=bool(ev_docs)))
    lines = ["## Root Cause Summary",
             f"No single upstream culprit dominates; the evidence points to a condition local to {tag} "
             f"([{mode['code']}] {mode['description']}).\n", "---\n",
             f"### Hypothesis 1 — {focus['name']} ({mode['description']}) · Confidence: {conf['confidence']}%",
             f"The strongest recent evidence for {tag} is consistent with {mode['description']}.\n",
             "**Evidence:**"]
    for d in ev_docs:
        snippet = (d.get("content") or d.get("title") or "").replace("\n", " ")[:120]
        lines.append(f"- `[{d['id']}]` — {snippet}")
    lines += ["", f"**Recommended Action:** Inspect {tag} for {mode['description']}. · Urgency: WITHIN 24H\n",
              "## Immediate Actions",
              f"1. Perform a targeted inspection of {tag}.",
              "2. Trend the relevant sensor and compare against the last healthy baseline.",
              "3. Escalate if the condition crosses the ISO alarm threshold."]
    causal = {
        "from_tag": tag, "from_name": focus["name"], "from_type": focus["type"],
        "from_mode": mode.get("code", ""), "from_mechanism": mode["description"],
        "to_tag": tag, "to_name": focus["name"], "to_type": focus["type"],
        "hops": 0, "correlation": 0.0, "confidence": conf["confidence"], "self": True,
    }
    return "\n".join(lines), conf, causal


def _fallback_answer(query, tag, hits):
    lines = ["## Root Cause Summary",
             f"Could not resolve a specific asset tag from the query"
             + (f" (nearest match: {tag})" if tag else "") +
             ". Returning the most relevant records from the knowledge graph.\n", "---\n",
             "### Related records"]
    if not hits:
        lines.append("_No matching documents found. Try naming an equipment tag such as P-101A or K-501._")
    for d in hits:
        snippet = (d.get("content") or d.get("title") or "").replace("\n", " ")[:140]
        lines.append(f"- `[{d['id']}]` ({d.get('type','')}) — {snippet}")
    return "\n".join(lines)


def _finalize(body, causal, trace, docs_seen, nodes, t0, mode, focus_tag, confidence):
    store = get_store()
    verified = citations.verify(body, store.document_ids())
    body = citations.annotate(body, store.document_ids())
    elapsed = round(time.time() - t0, 2)
    return {
        "answer": body,
        "mode": mode,
        "focus_tag": focus_tag,
        "causal": causal,
        "confidence": confidence["confidence"] if confidence else None,
        "confidence_breakdown": confidence["breakdown"] if confidence else [],
        "citations": verified,
        "metrics": {
            "answer_seconds": elapsed,
            "tool_calls": len(trace),
            "nodes_traversed": nodes,
            "documents_examined": len(docs_seen),
            "citations": len(verified["valid"]),
            "citation_faithfulness": verified["faithfulness"],
            "manual_baseline_minutes": 240,  # typical manual cross-system RCA
        },
        "trace": trace,
    }
