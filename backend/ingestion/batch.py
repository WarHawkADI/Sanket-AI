"""
Batched, scalable ingestion for the Neo4j backend.

Never write row-by-row. This loads documents in chunks with a single UNWIND per
batch (and `apoc.periodic.iterate` when APOC is available), which is the pattern
that lets ingestion scale from a 17-tag demo to a 10,000-tag plant. Used by the
Neo4j path; the in-memory store appends directly.

Usage:
    from backend.ingestion.batch import bulk_upsert_documents
    bulk_upsert_documents(neo4j_client, docs, batch_size=5000)
"""
from __future__ import annotations

from typing import Iterable

UPSERT_BATCH = """
UNWIND $rows AS row
MERGE (d:Document {id: row.id})
SET d.type = row.type, d.title = row.title, d.date = row.date,
    d.content = row.content, d.severity = row.severity, d.priority = row.priority,
    d.source = coalesce(row.source, 'batch')
WITH d, row
UNWIND row.tags AS tg
MATCH (e:Equipment {tag: tg})
MERGE (d)-[:DESCRIBES]->(e)
"""


def _chunks(seq, n):
    buf = []
    for x in seq:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf


def bulk_upsert_documents(client, documents: Iterable[dict], batch_size: int = 5000) -> int:
    """Upsert documents into Neo4j in batches. Returns the number written."""
    total = 0
    for chunk in _chunks(documents, batch_size):
        rows = [{
            "id": d["id"], "type": d.get("type", "DOCUMENT"), "title": d.get("title", ""),
            "date": d.get("date", ""), "content": (d.get("content") or "")[:4000],
            "severity": d.get("severity", ""), "priority": d.get("priority", ""),
            "source": d.get("source", "batch"),
            "tags": d.get("linked_tags") or ([d["tag"]] if d.get("tag") else []),
        } for d in chunk]
        client.run(UPSERT_BATCH, rows=rows)
        total += len(rows)
    return total


def bulk_upsert_apoc(client, documents: Iterable[dict], batch_size: int = 5000) -> int:
    """Same upsert via apoc.periodic.iterate — parallelisable, transaction-batched.
    Falls back to bulk_upsert_documents if APOC is unavailable."""
    rows = [{
        "id": d["id"], "type": d.get("type", "DOCUMENT"), "title": d.get("title", ""),
        "date": d.get("date", ""), "content": (d.get("content") or "")[:4000],
        "severity": d.get("severity", ""), "priority": d.get("priority", ""),
        "source": d.get("source", "batch"),
        "tags": d.get("linked_tags") or ([d["tag"]] if d.get("tag") else []),
    } for d in documents]
    try:
        client.run(
            "CALL apoc.periodic.iterate($outer, $inner, {batchSize:$bs, parallel:false, params:{rows:$rows}})",
            outer="UNWIND $rows AS row RETURN row",
            inner=("MERGE (d:Document {id: row.id}) "
                   "SET d.type=row.type, d.title=row.title, d.date=row.date, d.content=row.content, "
                   "d.severity=row.severity, d.priority=row.priority, d.source=coalesce(row.source,'batch') "
                   "WITH d, row UNWIND row.tags AS tg MATCH (e:Equipment {tag: tg}) MERGE (d)-[:DESCRIBES]->(e)"),
            rows=rows, bs=batch_size)
        return len(rows)
    except Exception:
        return bulk_upsert_documents(client, rows, batch_size)
