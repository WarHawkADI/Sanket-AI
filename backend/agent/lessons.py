"""
Lessons-Learned & Failure-Intelligence engine.

Scans the whole document corpus for active failure signatures and, using the
ISO-14224 co-failure statistics, projects the *next* likely failure for each
asset — pushing proactive warnings before the condition recurs.  This is the
"identify systemic patterns invisible to any individual review" pillar.
"""
from __future__ import annotations

from datetime import date, datetime

SEV_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0, "": 0}


def _recent(d: str, as_of: date, days: int) -> bool:
    try:
        return (as_of - datetime.strptime(d[:10], "%Y-%m-%d").date()).days <= days
    except (ValueError, TypeError):
        return False


def proactive_warnings(store, as_of: date | None = None, window_days: int = 400) -> list[dict]:
    """For each asset showing an active failure mode, project the likely next
    failure from co-failure statistics and rank by (severity × correlation)."""
    if as_of is None:
        from backend.config import now
        as_of = now()

    stats = _all_co_stats(store)

    warnings = []
    for eq in store.all_equipment():
        docs = store.documents_for(eq["tag"], limit=200)
        # most severe recent doc that records a failure mode
        active = None
        for d in sorted(docs, key=lambda x: (SEV_RANK.get((x.get("severity") or "").upper(), 0),
                                             x.get("date", "")), reverse=True):
            if d.get("failure_mode") and _recent(d.get("date", ""), as_of, window_days):
                active = d
                break
        if not active:
            continue
        fm = active["failure_mode"]
        for s in stats:
            if s["primary"] == fm:
                sec = store_mode_desc(store, s["secondary"])
                warnings.append({
                    "tag": eq["tag"], "name": eq.get("name", ""),
                    "current_failure": fm, "current_evidence": active["id"],
                    "current_severity": active.get("severity", ""),
                    "projected_failure": s["secondary"], "projected_description": sec,
                    "correlation": s["correlation"],
                    "occurrences_per_100_plant_years": s.get("occurrences_per_100_plant_years"),
                    "note": s.get("note", ""),
                    "priority": round(SEV_RANK.get((active.get("severity") or "").upper(), 1)
                                      * s["correlation"], 3),
                })
    warnings.sort(key=lambda w: w["priority"], reverse=True)
    return warnings


def systemic_patterns(store) -> list[dict]:
    """Aggregate failure-mode frequency across the corpus → the plant's top recurring modes."""
    counts: dict[str, dict] = {}
    for d in store.documents_for_all() if hasattr(store, "documents_for_all") else _all_docs(store):
        fm = d.get("failure_mode")
        if not fm:
            continue
        c = counts.setdefault(fm, {"failure_mode": fm, "count": 0, "high": 0, "assets": set()})
        c["count"] += 1
        c["assets"].add(d.get("tag", ""))
        if (d.get("severity") or "").upper() == "HIGH":
            c["high"] += 1
    out = [{"failure_mode": v["failure_mode"], "occurrences": v["count"],
            "high_severity": v["high"], "assets_affected": len([a for a in v["assets"] if a])}
           for v in counts.values()]
    out.sort(key=lambda x: (x["high_severity"], x["occurrences"]), reverse=True)
    return out


# ── helpers that work against either backend ────────────────────────────────
def _all_docs(store):
    if hasattr(store, "documents"):            # MemStore
        return store.documents
    return store.search("", limit=1000) or []  # Neo4jStore best-effort


def _all_co_stats(store):
    if hasattr(store, "co_failures"):
        return store.co_failures
    if hasattr(store, "_mem"):
        return store._mem.co_failures
    return []


def store_mode_desc(store, code):
    fm = getattr(store, "failure_modes", None)
    if isinstance(fm, dict) and code in fm:
        return fm[code].get("description", code)
    if hasattr(store, "_mem") and code in store._mem.failure_modes:
        return store._mem.failure_modes[code]["description"]
    return code
