"""
Extra agent capabilities beyond graph traversal:

  • structural_query — answer arbitrary structural questions about the asset base
    (a safe, backend-agnostic alternative to raw NL→Cypher — no injection surface).
  • predict_failure_mode — call the trained predictive-maintenance classifier.
  • check_compliance — regulatory gap check for an asset.
"""
import os
import sys
from datetime import date
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from langchain_core.tools import tool
from backend.graph.store import get_store
from backend.agent import ml, compliance


@tool
def structural_query(criticality: Optional[str] = None, equipment_type: Optional[str] = None,
                     area: Optional[str] = None) -> str:
    """Answer structural questions about the plant's asset base by filtering equipment.
    Use for questions like 'which HIGH-criticality pumps are in Area A-01?'.
    Any argument may be omitted. criticality: HIGH/MEDIUM/LOW. equipment_type e.g. CENTRIFUGAL_PUMP.
    area e.g. A-01. Returns matching equipment tags with name, type, criticality and area."""
    rows = get_store().all_equipment()
    def ok(e):
        return ((not criticality or (e.get("criticality") or "").upper() == criticality.upper())
                and (not equipment_type or (e.get("type") or "").upper() == equipment_type.upper())
                and (not area or (e.get("area") or "").upper() == area.upper()))
    hits = [e for e in rows if ok(e)]
    if not hits:
        return "No equipment matches those filters."
    lines = [f"{len(hits)} equipment match:"]
    for e in hits:
        lines.append(f"  {e['tag']} — {e.get('name','')} ({e.get('type','')}, "
                     f"{e.get('criticality','')}, area {e.get('area','')})")
    return "\n".join(lines)


@tool
def predict_failure_mode(air_temp_k: float, process_temp_k: float, rotational_speed_rpm: float,
                         torque_nm: float, tool_wear_min: float) -> str:
    """Predict machine failure probability and likely failure mode from live sensor readings
    using the trained predictive-maintenance model. Provide air temperature (K),
    process temperature (K), rotational speed (rpm), torque (Nm) and tool wear (min)."""
    r = ml.predict(air_temp_k, process_temp_k, rotational_speed_rpm, torque_nm, tool_wear_min)
    modes = ", ".join(r["predicted_modes"]) if r["predicted_modes"] else "none flagged"
    return (f"Predictive-maintenance result [{r['source']}]:\n"
            f"  Failure probability: {r['failure_probability']*100:.1f}%\n"
            f"  Likely modes: {modes}\n  {r['note']}")


@tool
def check_compliance(tag: str) -> str:
    """Check an asset's regulatory compliance status (OISD / Factory Act / PESO / ISO / API / CPCB).
    Returns which clauses are met and which are gaps, with the standard and gap severity."""
    a = compliance.audit_equipment(get_store(), tag)
    if a.get("error"):
        return f"{tag}: {a['error']}"
    if not a["results"]:
        return f"No regulatory clauses apply to {tag} (type {a.get('type','?')})."
    lines = [f"Compliance for {tag} ({a['type']}): {a['compliant']}/{a['clauses_checked']} met, {a['gaps']} gap(s)"]
    for r in a["results"]:
        if r["status"] == "GAP":
            lines.append(f"  [GAP · {r['severity']}] {r['standard']} — {r['title']} "
                         f"(no acceptable evidence within {r['interval_days']}d)")
        else:
            lines.append(f"  [OK] {r['standard']} — {r['title']} (evidence {r['evidence']} @ {r['evidence_date']})")
    return "\n".join(lines)
