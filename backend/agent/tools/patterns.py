"""Failure-mode taxonomy & co-failure pattern tools."""
import os
import sys
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from langchain_core.tools import tool
from backend.graph.store import get_store


@tool
def get_failure_modes(equipment_type: str) -> str:
    """Get known failure modes from the ISO 14224 taxonomy for a specific equipment type.
    equipment_type examples: CENTRIFUGAL_PUMP, CONTROL_VALVE, HEAT_EXCHANGER,
    CENTRIFUGAL_COMPRESSOR, ELECTRIC_MOTOR, STRAINER, STORAGE_VESSEL.
    Returns failure mode codes, descriptions, mechanisms, and frequency ratings."""
    modes = get_store().failure_modes_for(equipment_type)
    if not modes:
        return (f"No failure modes found for '{equipment_type}'. Valid types include: "
                "CENTRIFUGAL_PUMP, CONTROL_VALVE, HEAT_EXCHANGER, CENTRIFUGAL_COMPRESSOR, "
                "ELECTRIC_MOTOR, STRAINER, STORAGE_VESSEL")
    lines = [f"ISO 14224 failure modes for {equipment_type}:"]
    for m in modes:
        lines.append(f"\n[{m['code']}] {m['description']} (Frequency: {m.get('frequency') or 'N/A'})")
        if m.get("mechanism"):
            lines.append(f"  Mechanisms: {m['mechanism']}")
    return "\n".join(lines)


@tool
def get_co_failure_patterns(tags: List[str]) -> str:
    """Get historical co-failure patterns between a list of equipment tags.
    Finds ISO 14224 failure-mode correlations and shared maintenance records.
    tags: list of equipment tags (e.g. ['P-101A', 'V-201'])"""
    patterns, shared = get_store().co_failure(tags)
    if not patterns and not shared:
        return f"No co-failure patterns found for {tags}."
    lines = [f"Co-failure patterns for {tags}:"]
    if patterns:
        lines.append("\n  ISO 14224 failure-mode correlations:")
        for p in patterns:
            corr = f"{p['correlation']:.2f}" if p.get("correlation") is not None else "N/A"
            lines.append(f"  [{p['primary']}] -> [{p['secondary']}]  correlation {corr} | "
                         f"{p.get('occurrences_per_100_plant_years','N/A')}/100 plant-years")
            if p.get("note"):
                lines.append(f"    Note: {p['note']}")
    if shared:
        lines.append("\n  Shared maintenance/inspection records:")
        for r in shared:
            lines.append(f"  {r['tag1']} <-> {r['tag2']}: {r['shared_docs']} shared records — {r['example_docs']}")
    return "\n".join(lines)
