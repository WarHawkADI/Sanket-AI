"""
Loads a P&ID equipment graph into Neo4j.

Two modes:
  --demo        Load the pre-parsed demo cooling water circuit (safe for live demo)
  --cv <image>  Run the Azure P&ID CV pipeline on a real P&ID image

Run:
  python -m backend.ingestion.load_pid_graph           # defaults to --demo
  python -m backend.ingestion.load_pid_graph --demo
  python -m backend.ingestion.load_pid_graph --cv path/to/pid.png
"""
import json
import sys
import os
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.graph.client import Neo4jClient

DEMO_GRAPH = Path("backend/data/demo_pid_graph.json")
AZURE_PID_PIPELINE = Path("data/raw/azure_pid/src/run_pipeline.py")


def load_graph_json(graph: dict, db: Neo4jClient):
    pid_id = graph["pid_id"]
    equipment = graph["equipment"]
    connections = graph["connections"]
    print(f"  P&ID: {graph['title']}")
    print(f"  Equipment: {len(equipment)} nodes, Connections: {len(connections)} edges")

    for eq in equipment:
        db.run(
            """
            MERGE (e:Equipment {tag: $tag})
            SET e.name           = $name,
                e.type           = $type,
                e.iso15926_class = $iso_class,
                e.isa95_level    = $isa95,
                e.area           = $area,
                e.criticality    = $criticality,
                e.description    = $desc,
                e.pid_source     = $pid_id
            """,
            tag=eq["tag"],
            name=eq["name"],
            type=eq["type"],
            iso_class=eq.get("iso15926_class", ""),
            isa95=eq.get("isa95_level", ""),
            area=eq.get("area", ""),
            criticality=eq.get("criticality", "MEDIUM"),
            desc=eq.get("description", ""),
            pid_id=pid_id,
        )

    for conn in connections:
        if conn.get("connection_type") == "MECHANICAL_SENSOR":
            db.run(
                """
                MATCH (a:Equipment {tag: $from_tag})
                MATCH (b:Equipment {tag: $to_tag})
                MERGE (a)-[:HAS_SENSOR]->(b)
                """,
                from_tag=conn["from_tag"],
                to_tag=conn["to_tag"],
            )
        else:
            db.run(
                """
                MATCH (a:Equipment {tag: $from_tag})
                MATCH (b:Equipment {tag: $to_tag})
                MERGE (a)-[r:CONNECTED_TO {pipe_tag: $pipe_tag}]->(b)
                SET r.medium         = $medium,
                    r.flow_direction = $flow_dir,
                    r.diameter_in    = $dia
                """,
                from_tag=conn["from_tag"],
                to_tag=conn["to_tag"],
                pipe_tag=conn.get("pipe_tag") or "",
                medium=conn.get("medium") or "",
                flow_dir=conn.get("flow_direction") or "",
                dia=conn.get("nominal_diameter_in") or 0,
            )

    print("  ✓ Graph loaded into Neo4j")


def run_cv_pipeline(image_path: str) -> dict:
    if not AZURE_PID_PIPELINE.exists():
        raise FileNotFoundError(
            "Azure P&ID pipeline not found. Clone it with:\n"
            "  git clone https://github.com/Azure-Samples/digitization-of-piping-and-instrument-diagrams"
            " data/raw/azure_pid"
        )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = tmp.name

    subprocess.run(
        ["python", str(AZURE_PID_PIPELINE), "--image", image_path, "--output", out_path],
        check=True,
    )
    with open(out_path) as f:
        return json.load(f)


if __name__ == "__main__":
    db = Neo4jClient.get()

    if "--cv" in sys.argv:
        idx = sys.argv.index("--cv")
        image_path = sys.argv[idx + 1]
        print(f"Running CV pipeline on {image_path}...")
        graph = run_cv_pipeline(image_path)
    else:
        if not DEMO_GRAPH.exists():
            print(f"Demo graph not found at {DEMO_GRAPH}. Run: python scripts/generate_seed_data.py")
            sys.exit(1)
        print("Loading pre-parsed demo P&ID graph (safe for demo)...")
        with open(DEMO_GRAPH) as f:
            graph = json.load(f)

    load_graph_json(graph, db)
