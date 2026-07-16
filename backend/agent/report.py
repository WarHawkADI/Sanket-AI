"""
One-click asset intelligence report (markdown) — the "compliance evidence
package" / exportable RCA the brief asks for.  Combines the deterministic RCA,
regulatory compliance status, and recent maintenance history into a single
document a field engineer or auditor can hand over.
"""
from __future__ import annotations

from backend.agent import compliance
from backend.config import now


def asset_report(store, tag: str) -> str | None:
    eq = store.get_equipment(tag)
    if not eq:
        return None

    from backend.agent.rca_engine import deterministic_rca
    docs = store.documents_for(tag, limit=8)
    comp = compliance.audit_equipment(store, tag)

    L = []
    L.append(f"# Asset Intelligence Report — {tag}")
    L.append(f"**{eq.get('name','')}**  ·  {eq.get('type','').replace('_',' ').title()}  ·  "
             f"criticality {eq.get('criticality','')}  ·  area {eq.get('area','')}")
    L.append(f"_Generated {now().isoformat()} · Sanket AI_\n")
    if eq.get("description"):
        L.append(f"> {eq['description']}\n")

    # Compliance summary
    L.append("## Regulatory Compliance")
    if comp.get("results"):
        L.append(f"{comp['compliant']}/{comp['clauses_checked']} clauses met · **{comp['gaps']} gap(s)**\n")
        L.append("| Standard | Requirement | Status | Evidence |")
        L.append("|---|---|---|---|")
        for r in comp["results"]:
            ev = r["evidence"] or "—"
            status = "✅ OK" if r["status"] == "COMPLIANT" else f"⚠️ GAP ({r['severity']})"
            L.append(f"| {r['standard']} | {r['title']} | {status} | {ev} |")
        L.append("")
    else:
        L.append("_No regulatory clauses mapped to this equipment type._\n")

    # Recent history
    L.append("## Recent Maintenance & Inspection History")
    if docs:
        L.append("| ID | Type | Date | Severity | Title |")
        L.append("|---|---|---|---|---|")
        for d in docs:
            L.append(f"| {d['id']} | {d.get('type','')} | {d.get('date','')} | "
                     f"{d.get('severity','') or d.get('priority','')} | {d.get('title','')} |")
        L.append("")
    else:
        L.append("_No history on record._\n")

    return "\n".join(L)
