"""
Master ingestion runner — loads all datasets into Neo4j in the correct order.

Prerequisites:
  1. Neo4j running:     docker compose up -d neo4j
  2. .env configured:   cp .env.example .env  (fill in GROQ_API_KEY)
  3. Packages installed: pip install -r backend/requirements.txt
  4. Seed data:         python scripts/generate_seed_data.py
  5. Datasets:          bash get_datasets.sh  (optional — skippable for demo)

Run from repo root:
  python -m backend.ingestion.run_all
  python -m backend.ingestion.run_all --skip-csb    # skip PDF ingestion (saves API calls)
"""
import sys
import subprocess
from backend.graph.client import Neo4jClient


def apply_schema(db: Neo4jClient):
    print("Applying Neo4j schema (constraints + indexes + vector index)...")
    with open("backend/graph/schema.cypher") as f:
        statements = [s.strip() for s in f.read().split(";") if s.strip()]
    for stmt in statements:
        try:
            db.run(stmt)
        except Exception as e:
            print(f"  Note: {e}")
    print("  ✓ Schema applied")


def run_step(label: str, module: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, "-m", module],
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"  ✗ {label} failed (exit {result.returncode})")
        sys.exit(result.returncode)


if __name__ == "__main__":
    skip_csb = "--skip-csb" in sys.argv

    db = Neo4jClient.get()
    apply_schema(db)

    run_step("Step 1/5 — P&ID graph (equipment topology)",
             "backend.ingestion.load_pid_graph")

    run_step("Step 2/5 — Demo documents (work orders, inspection logs, ISO 14224 taxonomy)",
             "backend.ingestion.load_demo_docs")

    run_step("Step 3/5 — Azure PdM (machines, telemetry, failures, work orders, errors)",
             "backend.ingestion.process_azure_pdm")

    if not skip_csb:
        run_step("Step 4/5 — CSB incident reports (PDF ingestion + Groq entity extraction)",
                 "backend.ingestion.process_csb")
    else:
        print("\nStep 4/5 — CSB ingestion skipped (--skip-csb)")

    run_step("Step 5/5 — ML classifiers (AI4I + Hydraulic)",
             "backend.ingestion.train_classifiers")

    print("\n" + "="*60)
    print("  All ingestion complete.")
    print("  Verify in Neo4j Browser: http://localhost:7474")
    print("  Run: MATCH (n) RETURN labels(n), count(n) ORDER BY count(n) DESC")
    print("="*60)
