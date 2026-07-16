"""
Loads Microsoft Azure Predictive Maintenance dataset into Neo4j.

Input files (data/raw/azure_pdm/):
  PdM_machines.csv   — 1,000 machines with model + age
  PdM_telemetry.csv  — 8.7M hourly sensor readings (volt/rotate/pressure/vibration)
  PdM_failures.csv   — component failure events
  PdM_maint.csv      — scheduled maintenance records
  PdM_errors.csv     — error log events

Run: python -m backend.ingestion.process_azure_pdm
"""
import json
import sys
import os
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.graph.client import Neo4jClient

DATA = "data/raw/azure_pdm"

FAILURE_DESC = {
    "comp1": "Component 1 failure — electrical/hydraulic actuator",
    "comp2": "Component 2 failure — rotating element (bearing/gear)",
    "comp3": "Component 3 failure — sealing system",
    "comp4": "Component 4 failure — control/instrumentation system",
}


def load_machines(db: Neo4jClient):
    df = pd.read_csv(f"{DATA}/PdM_machines.csv")
    for _, r in tqdm(df.iterrows(), total=len(df), desc="Equipment nodes"):
        db.run(
            """
            MERGE (e:Equipment {tag: $tag})
            SET e.model = $model,
                e.age_years = $age,
                e.source = 'azure_pdm',
                e.type = 'INDUSTRIAL_MACHINE'
            """,
            tag=f"M-{r.machineID:03d}",
            model=str(r.model),
            age=int(r.age),
        )
    print(f"  ✓ {len(df)} equipment nodes")


def load_telemetry(db: Neo4jClient):
    # 8.7M rows — never stored raw; aggregate to per-machine summary
    print("  Aggregating 8.7M telemetry rows (~30s)...")
    telem = pd.read_csv(f"{DATA}/PdM_telemetry.csv", parse_dates=["datetime"])

    summary = (
        telem.groupby("machineID")
        .agg(
            volt_mean=("volt", "mean"),
            volt_std=("volt", "std"),
            rotate_mean=("rotate", "mean"),
            rotate_std=("rotate", "std"),
            pressure_mean=("pressure", "mean"),
            pressure_std=("pressure", "std"),
            vibration_mean=("vibration", "mean"),
            vibration_std=("vibration", "std"),
            vibration_max=("vibration", "max"),
        )
        .round(3)
    )

    for machine_id, stats in tqdm(summary.iterrows(), total=len(summary), desc="Sensor profiles"):
        db.run(
            """
            MATCH (e:Equipment {tag: $tag})
            SET e.sensor_profile = $profile
            """,
            tag=f"M-{machine_id:03d}",
            profile=json.dumps(stats.to_dict()),
        )
    print(f"  ✓ Sensor profiles on {len(summary)} machines")


def load_failures(db: Neo4jClient):
    df = pd.read_csv(f"{DATA}/PdM_failures.csv", parse_dates=["datetime"])
    for _, r in tqdm(df.iterrows(), total=len(df), desc="Failure records"):
        db.run(
            """
            MERGE (fm:FailureMode {code: $code})
            SET fm.description = $desc, fm.source = 'azure_pdm'
            WITH fm
            MATCH (e:Equipment {tag: $tag})
            MERGE (e)-[:RECORDED_FAILURE {date: $date}]->(fm)
            """,
            code=r.failure,
            desc=FAILURE_DESC.get(r.failure, r.failure),
            tag=f"M-{r.machineID:03d}",
            date=str(r.datetime.date()),
        )
    print(f"  ✓ {len(df)} failure events linked")


def load_maintenance(db: Neo4jClient):
    df = pd.read_csv(f"{DATA}/PdM_maint.csv", parse_dates=["datetime"])
    for _, r in tqdm(df.iterrows(), total=len(df), desc="Work orders"):
        wo_id = f"WO-AZ-{r.machineID}-{r.datetime.strftime('%Y%m%d')}"
        db.run(
            """
            MERGE (d:Document {id: $id})
            SET d.type = 'WORK_ORDER',
                d.date = $date,
                d.content = $content,
                d.source = 'azure_pdm'
            WITH d
            MATCH (e:Equipment {tag: $tag})
            MERGE (d)-[:DESCRIBES]->(e)
            """,
            id=wo_id,
            date=str(r.datetime.date()),
            content=f"Scheduled maintenance on machine {r.machineID}: replaced {r.comp}. Date: {r.datetime}.",
            tag=f"M-{r.machineID:03d}",
        )
    print(f"  ✓ {len(df)} work orders created")


def load_errors(db: Neo4jClient):
    df = pd.read_csv(f"{DATA}/PdM_errors.csv", parse_dates=["datetime"])
    for _, r in tqdm(df.iterrows(), total=len(df), desc="Error logs"):
        db.run(
            """
            MERGE (d:Document {id: $id})
            SET d.type = 'ERROR_LOG',
                d.date = $date,
                d.error_id = $err,
                d.content = $content,
                d.source = 'azure_pdm'
            WITH d
            MATCH (e:Equipment {tag: $tag})
            MERGE (d)-[:DESCRIBES]->(e)
            """,
            id=f"ERR-AZ-{r.machineID}-{r.datetime.strftime('%Y%m%d%H%M')}",
            date=str(r.datetime.date()),
            err=r.errorID,
            content=f"Error code {r.errorID} detected on machine {r.machineID} at {r.datetime}.",
            tag=f"M-{r.machineID:03d}",
        )
    print(f"  ✓ {len(df)} error logs created")


if __name__ == "__main__":
    db = Neo4jClient.get()
    print("Loading Azure PdM dataset into Neo4j...")
    load_machines(db)
    load_telemetry(db)
    load_failures(db)
    load_maintenance(db)
    load_errors(db)
    print("\nAzure PdM ingestion complete.")
