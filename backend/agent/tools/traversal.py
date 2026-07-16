"""Graph-topology traversal tools (backend-agnostic via the Store facade)."""
import os
import sys
from typing import Union

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from langchain_core.tools import tool
from backend.graph.store import get_store


def _fmt(rows, tag, direction):
    if not rows:
        return f"No {direction} equipment found from {tag}."
    lines = [f"{direction.capitalize()} equipment from {tag}:"]
    for r in rows:
        lines.append(
            f"  [{r['hops']} hop(s)] {r['tag']} — {r.get('name','')} "
            f"({r.get('type','')}, criticality: {r.get('criticality','')})"
        )
    return "\n".join(lines)


@tool
def traverse_upstream(tag: str, depth: Union[int, str] = 3) -> str:
    """Follow fluid flow backward from an equipment tag to find upstream sources.
    Use this to find what equipment could be causing problems in the given equipment.
    Returns equipment tags, names, types, criticality, and hop distance."""
    rows = get_store().traverse(tag, "upstream", int(depth) if str(depth).isdigit() else 3)
    return _fmt(rows, tag, "upstream")


@tool
def traverse_downstream(tag: str, depth: Union[int, str] = 3) -> str:
    """Follow fluid flow forward from an equipment tag to find downstream equipment.
    Use this to understand what equipment is affected by the given equipment.
    Returns equipment tags, names, types, criticality, and hop distance."""
    rows = get_store().traverse(tag, "downstream", int(depth) if str(depth).isdigit() else 3)
    return _fmt(rows, tag, "downstream")
