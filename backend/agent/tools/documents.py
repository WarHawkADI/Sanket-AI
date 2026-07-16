"""CMMS document tools (work orders, inspection logs, semantic/keyword search)."""
import os
import sys
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from langchain_core.tools import tool
from backend.graph.store import get_store


def _doc_block(d, body_len=450):
    head = f"\n[{d['id']}] {d.get('type','')} — {d.get('date','')}"
    meta = []
    if d.get("priority"):
        meta.append(f"Priority: {d['priority']}")
    if d.get("severity"):
        meta.append(f"Severity: {d['severity']}")
    if d.get("status"):
        meta.append(f"Status: {d['status']}")
    lines = [head + ("  |  " + " · ".join(meta) if meta else "")]
    if d.get("title"):
        lines.append(f"  {d['title']}")
    lines.append(f"  {(d.get('content') or '')[:body_len]}")
    return "\n".join(lines)


@tool
def get_failure_history(tag: str, days: int = 730) -> str:
    """Get the past failure and maintenance history for a specific equipment tag.
    Returns work orders, inspection logs, and incident reports for this equipment."""
    docs = get_store().documents_for(tag, limit=10)
    if not docs:
        return f"No failure history found for {tag}."
    return "\n".join([f"Failure/maintenance history for {tag}:"] + [_doc_block(d) for d in docs])


@tool
def get_inspection_logs(tag: str) -> str:
    """Get inspection log records for a specific equipment tag.
    Returns inspection findings, severity ratings, and recommendations in date order."""
    docs = get_store().documents_for(tag, types=["INSPECTION_LOG"], limit=6)
    if not docs:
        return f"No inspection logs found for {tag}."
    return "\n".join([f"Inspection logs for {tag}:"] + [_doc_block(d, 500) for d in docs])


@tool
def get_work_orders(tag: str) -> str:
    """Get CMMS work orders for a specific equipment tag.
    Returns work order findings, actions taken, priority, and status."""
    docs = get_store().documents_for(tag, types=["WORK_ORDER"], limit=6)
    if not docs:
        return f"No work orders found for {tag}."
    return "\n".join([f"Work orders for {tag}:"] + [_doc_block(d, 500) for d in docs])


@tool
def semantic_search_near(query: str, tags: List[str]) -> str:
    """Search for documents related to a symptom or failure, constrained to specific equipment.
    Use this to find relevant incident reports or maintenance records matching a description.
    tags: list of equipment tag IDs to search within (e.g. ['P-101A', 'V-201'])"""
    docs = get_store().search(query, tags=tags, limit=5)
    if not docs:
        return f"No documents found for '{query}' near equipment {tags}."
    return "\n".join([f"Documents related to '{query}' near {tags}:"] + [_doc_block(d, 400) for d in docs])
