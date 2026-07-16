"""
Intelligence endpoints beyond RCA — the wider "Unified Brain":
compliance, lessons-learned, predictive maintenance, overdue tracking,
document retrieval, knowledge-cliff capture, and report export.
"""
from fastapi import APIRouter, HTTPException

from backend.graph.store import get_store
from backend.agent import compliance, lessons, ml, report, ingest, copilot, overview, insights
from backend.api.models import KnowledgeCapture, AskQuery, IngestRequest
from backend.config import now

router = APIRouter()


@router.get("/timeline/{tag}")
def timeline(tag: str):
    """Chronological event stream for an asset (temporal layer)."""
    return insights.timeline(get_store(), tag)


@router.get("/similar/{tag}")
def similar(tag: str):
    """Records on other equipment sharing this asset's failure modes."""
    return insights.similar_incidents(get_store(), tag)


@router.get("/deviations")
def deviations():
    """Live quality/SPC deviations — assets breaching their alarm limit."""
    return insights.deviations(get_store())


@router.get("/roi")
def roi(assets: int = 500, technicians: int = 40, search_hours_per_week: float = 14,
        time_reduction_pct: float = 60, loaded_rate_inr: float = 900,
        downtime_events_per_year: int = 20, downtime_cost_inr: float = 1500000,
        downtime_reduction_pct: float = 20):
    """Business-impact / ROI model."""
    return insights.roi(assets, technicians, search_hours_per_week, time_reduction_pct,
                        loaded_rate_inr, downtime_events_per_year, downtime_cost_inr, downtime_reduction_pct)


@router.get("/cost-model")
def cost_model():
    """Scalability cost/latency model."""
    return insights.cost_model(get_store())


@router.get("/audit/{tag}")
def audit(tag: str):
    """Auto-generated compliance evidence package (markdown)."""
    md = insights.audit_pack(get_store(), tag)
    if md is None:
        raise HTTPException(status_code=404, detail=f"Equipment {tag} not found")
    return {"tag": tag, "markdown": md}


@router.get("/overview")
def plant_overview():
    """Command-centre: plant-wide KPIs across every pillar."""
    return overview.plant_overview(get_store())


@router.get("/evaluation")
def evaluation():
    """Validated Evaluation-Focus metrics: benchmark, entity extraction, KG completeness."""
    return overview.evaluation(get_store())


@router.post("/ask")
def ask(req: AskQuery):
    """Expert Knowledge Copilot — cited Q&A over the whole corpus."""
    return copilot.answer(req.query, get_store())


@router.get("/samples")
def samples():
    """Heterogeneous sample documents for the ingestion demo."""
    return {"documents": get_store().sample_documents()}


@router.post("/ingest/preview")
def ingest_preview(req: IngestRequest):
    """Extract entities from raw document text (no commit)."""
    return ingest.preview(req.text, get_store())


@router.post("/ingest/commit")
def ingest_commit(req: IngestRequest):
    """Extract + add the document to the knowledge graph, linked to its equipment."""
    return ingest.commit(req.text, req.title, req.doc_type, get_store())


@router.get("/knowledge/list")
def knowledge_list():
    """Captured tribal/expert knowledge nodes."""
    return {"captures": getattr(get_store(), "tribal", [])}


@router.get("/compliance/plant")
def compliance_plant():
    """Plant-wide compliance roll-up with per-asset gaps."""
    return compliance.audit_plant(get_store())


@router.get("/compliance/{tag}")
def compliance_asset(tag: str):
    """Compliance status for a single asset."""
    a = compliance.audit_equipment(get_store(), tag)
    if a.get("error"):
        raise HTTPException(status_code=404, detail=a["error"])
    return a


@router.get("/lessons/warnings")
def lessons_warnings():
    """Proactive failure warnings projected from co-failure statistics."""
    return {"as_of": now().isoformat(), "warnings": lessons.proactive_warnings(get_store())}


@router.get("/lessons/patterns")
def lessons_patterns():
    """Systemic failure-mode patterns across the whole corpus."""
    return {"patterns": lessons.systemic_patterns(get_store())}


@router.get("/telemetry/{tag}")
def telemetry(tag: str):
    """Condition-monitoring readings for an asset — powers the HMI zone gauge + trend chart."""
    t = get_store().telemetry(tag)
    if not t:
        raise HTTPException(status_code=404, detail=f"No telemetry for {tag}")
    return {"tag": tag, **t}


@router.get("/overdue")
def overdue():
    """Inspections whose next-due date has passed as of the plant's 'now'."""
    rows = get_store().overdue_inspections(now().isoformat())
    return {"as_of": now().isoformat(), "count": len(rows), "items": rows}


@router.get("/documents/{doc_id}")
def get_document(doc_id: str):
    """Retrieve a source document — powers clickable citations in the UI."""
    d = get_store().get_document(doc_id)
    if not d:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return {k: v for k, v in d.items() if k != "_tokens"}


@router.post("/knowledge/capture")
def capture_knowledge(entry: KnowledgeCapture):
    """Knowledge-Cliff Capture: persist a retiring expert's insight as a queryable node."""
    store = get_store()
    if not store.get_equipment(entry.equipment_tag):
        raise HTTPException(status_code=404, detail=f"Equipment {entry.equipment_tag} not found")
    import uuid
    doc_id = f"TRIBAL-{uuid.uuid4().hex[:8].upper()}"
    store.capture_knowledge({
        "id": doc_id, "title": entry.title, "content": entry.content,
        "author": entry.author, "date": entry.date or now().isoformat(),
        "equipment_tag": entry.equipment_tag,
    })
    return {"status": "captured", "id": doc_id, "equipment_tag": entry.equipment_tag}


@router.get("/predict")
def predict(air_temp_k: float, process_temp_k: float, rotational_speed_rpm: float,
            torque_nm: float, tool_wear_min: float):
    """Predictive-maintenance classifier over live sensor readings."""
    return ml.predict(air_temp_k, process_temp_k, rotational_speed_rpm, torque_nm, tool_wear_min)


@router.get("/report/{tag}")
def asset_report(tag: str):
    """One-click asset intelligence report (markdown) — RCA + compliance + history."""
    md = report.asset_report(get_store(), tag)
    if md is None:
        raise HTTPException(status_code=404, detail=f"Equipment {tag} not found")
    return {"tag": tag, "markdown": md}
