"""
Quality & Regulatory Compliance Intelligence.

Maps regulatory clauses (OISD, Factory Act, PESO, CPCB, ISO, API) against each
asset's actual inspection/monitoring evidence in the knowledge graph, and flags
gaps — the "auto-generated compliance evidence package" the brief asks for.

A gap = an applicable clause for which the asset has **no acceptable evidence
document within the clause's maximum interval**.
"""
from __future__ import annotations

from datetime import date, datetime


def _parse(d: str):
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def audit_equipment(store, tag: str, as_of: date | None = None) -> dict:
    """Compliance status for one asset: which clauses are met vs. gapped."""
    if as_of is None:
        from backend.config import now
        as_of = now()
    eq = store.get_equipment(tag)
    if not eq:
        return {"tag": tag, "error": "equipment not found", "clauses": []}
    etype = eq.get("type", "")
    docs = store.documents_for(tag, limit=200)

    results = []
    for clause in store.compliance_clauses():
        if etype not in clause.get("applies_to", []):
            continue
        need = set(clause.get("evidence_required", []))
        window = clause.get("max_interval_days", 365)
        # acceptable evidence = a doc whose subtype/title matches a required type,
        # dated within the interval before as_of
        latest = None
        for d in docs:
            sub = (d.get("subtype") or "").upper()
            title = (d.get("title") or "").upper()
            if any(n.upper() in sub or n.upper() in title for n in need):
                dt = _parse(d.get("date", ""))
                if dt and (as_of - dt).days <= window:
                    if latest is None or dt > latest[0]:
                        latest = (dt, d["id"])
        status = "COMPLIANT" if latest else "GAP"
        results.append({
            "clause_id": clause["id"], "standard": clause["standard"],
            "title": clause["title"], "authority": clause["authority"],
            "requirement": clause["requirement"], "status": status,
            "severity": clause.get("severity_on_gap", "MEDIUM") if status == "GAP" else "-",
            "evidence": latest[1] if latest else None,
            "evidence_date": latest[0].isoformat() if latest else None,
            "interval_days": window,
        })
    gaps = [r for r in results if r["status"] == "GAP"]
    return {
        "tag": tag, "type": etype, "name": eq.get("name", ""),
        "clauses_checked": len(results), "gaps": len(gaps),
        "compliant": len(results) - len(gaps), "results": results,
    }


def audit_plant(store, as_of: date | None = None) -> dict:
    """Plant-wide roll-up across every asset with a P&ID presence."""
    if as_of is None:
        from backend.config import now
        as_of = now()
    per_asset, total_gaps, high_gaps = [], 0, 0
    for eq in store.all_equipment():
        a = audit_equipment(store, eq["tag"], as_of)
        if a.get("clauses_checked"):
            per_asset.append(a)
            total_gaps += a["gaps"]
            high_gaps += sum(1 for r in a["results"]
                             if r["status"] == "GAP" and r["severity"] == "HIGH")
    per_asset.sort(key=lambda a: a["gaps"], reverse=True)
    checked = sum(a["clauses_checked"] for a in per_asset)
    compliant = sum(a["compliant"] for a in per_asset)
    return {
        "as_of": as_of.isoformat(),
        "assets_audited": len(per_asset),
        "checks": checked, "compliant": compliant, "gaps": total_gaps,
        "high_severity_gaps": high_gaps,
        "compliance_rate": round(compliant / checked, 3) if checked else 1.0,
        "assets": per_asset,
    }
