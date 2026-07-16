"""
Loads demo work orders, inspection logs, and ISO 14224 taxonomy into Neo4j.
Also generates BGE-M3 embeddings so semantic_search_near works on demo data.

Run: python -m backend.ingestion.load_demo_docs
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.graph.client import Neo4jClient

DATA_DIR = Path("backend/data")


_EMBEDDER = None


def _embed(text: str):
    """Embed text with BGE-M3 if available; return None otherwise.

    Embeddings are optional — the Store's keyword search works without them, so
    ingestion (and the whole demo) runs fine without the ~2.5GB sentence-transformers
    stack installed.
    """
    global _EMBEDDER
    if _EMBEDDER is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDER = SentenceTransformer("BAAI/bge-m3")
        except Exception:
            _EMBEDDER = False
            print("  (sentence-transformers not installed — skipping embeddings; keyword search still works)")
    if not _EMBEDDER:
        return None
    return _EMBEDDER.encode(text[:2000], normalize_embeddings=True).tolist()


def load_iso14224(db: Neo4jClient):
    with open(DATA_DIR / "iso14224_taxonomy.json") as f:
        taxonomy = json.load(f)

    for eq_class in taxonomy["equipment_classes"]:
        for fm in eq_class["failure_modes"]:
            db.run(
                """
                MERGE (fm:FailureMode {code: $code})
                SET fm.description = $desc,
                    fm.mechanism = $mechanism,
                    fm.iso14224_frequency = $freq,
                    fm.equipment_class = $eq_class,
                    fm.source = 'iso14224'
                """,
                code=fm["code"],
                desc=fm["description"],
                mechanism=", ".join(fm.get("mechanisms", [])),
                freq=fm.get("iso14224_frequency", ""),
                eq_class=eq_class["class"],
            )
            # Link equipment nodes of this type to the failure mode
            db.run(
                """
                MATCH (e:Equipment) WHERE e.type = $eq_type
                MATCH (fm:FailureMode {code: $code})
                MERGE (e)-[:HAS_KNOWN_FAILURE_MODE {frequency: $freq}]->(fm)
                """,
                eq_type=eq_class["class"],
                code=fm["code"],
                freq=fm.get("iso14224_frequency", "UNKNOWN"),
            )

    for stat in taxonomy.get("co_failure_statistics", []):
        db.run(
            """
            MATCH (fm1:FailureMode {code: $primary})
            MATCH (fm2:FailureMode {code: $secondary})
            MERGE (fm1)-[r:CO_OCCURS_WITH]->(fm2)
            SET r.correlation = $corr,
                r.occurrences_per_100_plant_years = $occ,
                r.note = $note
            """,
            primary=stat["primary"],
            secondary=stat["secondary"],
            corr=stat["correlation"],
            occ=stat["occurrences_per_100_plant_years"],
            note=stat.get("note", ""),
        )

    print("  ✓ ISO 14224 taxonomy + co-failure statistics")


def load_work_orders(db: Neo4jClient):
    with open(DATA_DIR / "work_orders.json") as f:
        work_orders = json.load(f)

    print(f"  Embedding {len(work_orders)} work orders (BGE-M3)...")
    for wo in work_orders:
        content = f"Findings: {wo.get('findings', '')}\nAction taken: {wo.get('action_taken', '')}"
        embedding = _embed(content)

        db.run(
            """
            MERGE (d:Document {id: $id})
            SET d.type      = 'WORK_ORDER',
                d.title     = $title,
                d.date      = $date,
                d.content   = $content,
                d.priority  = $priority,
                d.status    = $status,
                d.technician = $technician,
                d.embedding = $embedding,
                d.source    = 'demo'
            WITH d
            MATCH (e:Equipment {tag: $tag})
            MERGE (d)-[:DESCRIBES]->(e)
            """,
            id=wo["id"],
            title=wo["title"],
            date=wo["date_raised"] or "",
            content=content,
            priority=wo.get("priority", ""),
            status=wo.get("status", ""),
            technician=wo.get("technician", ""),
            embedding=embedding,
            tag=wo["equipment_tag"],
        )

        if wo.get("iso14224_failure_mode"):
            db.run(
                """
                MATCH (d:Document {id: $doc_id})
                MATCH (fm:FailureMode {code: $fm_code})
                MERGE (d)-[:RECORDS_FAILURE]->(fm)
                """,
                doc_id=wo["id"],
                fm_code=wo["iso14224_failure_mode"],
            )

    print(f"  ✓ {len(work_orders)} work orders")


def load_inspection_logs(db: Neo4jClient):
    with open(DATA_DIR / "inspection_logs.json") as f:
        inspection_logs = json.load(f)

    print(f"  Embedding {len(inspection_logs)} inspection logs (BGE-M3)...")
    for log in inspection_logs:
        content = f"Findings: {log.get('findings', '')}\nRecommendation: {log.get('recommendation', '')}"
        embedding = _embed(content)

        db.run(
            """
            MERGE (d:Document {id: $id})
            SET d.type      = 'INSPECTION_LOG',
                d.title     = $title,
                d.date      = $date,
                d.content   = $content,
                d.severity  = $severity,
                d.inspector = $inspector,
                d.embedding = $embedding,
                d.source    = 'demo'
            WITH d
            MATCH (e:Equipment {tag: $tag})
            MERGE (d)-[:DESCRIBES]->(e)
            """,
            id=log["id"],
            title=f"{log['equipment_tag']} — {log['inspection_type']}",
            date=log["date"],
            content=content,
            severity=log.get("severity", ""),
            inspector=log.get("inspector", ""),
            embedding=embedding,
            tag=log["equipment_tag"],
        )

        if log.get("iso14224_failure_mode_detected"):
            db.run(
                """
                MATCH (d:Document {id: $doc_id})
                MATCH (fm:FailureMode {code: $fm_code})
                MERGE (d)-[:RECORDS_FAILURE]->(fm)
                """,
                doc_id=log["id"],
                fm_code=log["iso14224_failure_mode_detected"],
            )

    print(f"  ✓ {len(inspection_logs)} inspection logs")


if __name__ == "__main__":
    missing = [f for f in ["iso14224_taxonomy.json", "work_orders.json", "inspection_logs.json"]
               if not (DATA_DIR / f).exists()]
    if missing:
        print(f"Missing files: {missing}. Run: python scripts/generate_seed_data.py")
        sys.exit(1)

    db = Neo4jClient.get()
    print("Loading demo documents into Neo4j...")
    load_iso14224(db)
    load_work_orders(db)
    load_inspection_logs(db)
    print("\nDemo document ingestion complete.")
    print("Verify: MATCH (d:Document) RETURN d.type, count(d) in Neo4j Browser")
