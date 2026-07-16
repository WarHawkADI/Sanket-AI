"""
Regression + unit tests for Sanket AI. All run against the in-memory store with
no external services (SANKET_FORCE_MEMSTORE=1), so the demo can never silently
break the night before judging.

Run:  python -m pytest -q
"""
import os
from datetime import date

os.environ["SANKET_FORCE_MEMSTORE"] = "1"
os.environ["SANKET_NOW"] = "2025-06-15"

import pytest
from fastapi.testclient import TestClient

from backend.graph.store import get_store, reset_store
from backend.agent.confidence import Evidence, score
from backend.agent import citations, compliance, lessons, ml, report, ingest, copilot, overview, insights
from backend.agent.rca_engine import deterministic_rca
from backend.main import app


@pytest.fixture(scope="module")
def store():
    reset_store()
    return get_store()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── store ───────────────────────────────────────────────────────────────────
def test_store_loads(store):
    h = store.health()
    assert h["backend"] == "in-memory"
    assert h["equipment"] >= 15 and h["documents"] >= 60 and h["clauses"] >= 5


def test_upstream_traversal(store):
    tags = [r["tag"] for r in store.traverse("P-101A", "upstream", 3)]
    assert "V-201" in tags and "ST-101" in tags and "TK-401" in tags


def test_downstream_traversal(store):
    tags = [r["tag"] for r in store.traverse("V-201", "downstream", 3)]
    assert "P-101A" in tags and "HE-301" in tags


def test_documents_and_search(store):
    assert store.documents_for("V-201", ["INSPECTION_LOG"])
    hits = store.search("cavitation vibration", tags=["V-201"])
    assert any("cavitation" in (d["content"].lower()) for d in hits)


# ── confidence ──────────────────────────────────────────────────────────────
def test_confidence_monotonic():
    strong = score(Evidence(["a", "b", "c"], ["HIGH", "HIGH"], "2025-06-01", 0.72, True), date(2025, 6, 15))
    weak = score(Evidence(["a"], ["LOW"], "2023-01-01", 0.0, False), date(2025, 6, 15))
    assert strong["confidence"] > weak["confidence"]
    assert strong["level"] == "HIGH" and strong["confidence"] <= 97
    assert weak["confidence"] >= 5


# ── citations ───────────────────────────────────────────────────────────────
def test_citation_verifier(store):
    ids = store.document_ids()
    real = next(iter(ids))
    text = f"cause [{real}] and fabricated [INS-9999-0000]."
    v = citations.verify(text, ids)
    assert real in v["valid"] and "INS-9999-0000" in v["hallucinated"]
    assert 0 <= v["faithfulness"] <= 1
    assert "[unverified]" in citations.annotate(text, ids)


# ── deterministic RCA ───────────────────────────────────────────────────────
def test_rca_hero_query():
    r = deterministic_rca("P-101A centrifugal pump showing 47Hz vibration spike. Find root cause.")
    assert r["focus_tag"] == "P-101A"
    assert "V-201" in r["answer"]
    assert r["confidence"] >= 80
    assert r["citations"]["hallucinated"] == []
    assert r["citations"]["valid"]
    assert r["metrics"]["nodes_traversed"] >= 2


def test_rca_second_scenario():
    r = deterministic_rca("K-501 compressor high vibration, what is the cause?")
    assert r["focus_tag"] == "K-501"
    assert "F-501" in r["answer"]


def test_rca_unknown_asset_is_graceful():
    r = deterministic_rca("why is the maintenance backlog so high")
    assert r["focus_tag"] is None
    assert r["citations"]["hallucinated"] == []
    assert "answer" in r


# ── compliance ──────────────────────────────────────────────────────────────
def test_compliance_asset(store):
    a = compliance.audit_equipment(store, "K-501")
    assert a["clauses_checked"] >= 3
    assert a["gaps"] >= 1


def test_compliance_plant(store):
    p = compliance.audit_plant(store)
    assert p["assets_audited"] >= 5
    assert 0.0 <= p["compliance_rate"] <= 1.0


# ── lessons ─────────────────────────────────────────────────────────────────
def test_lessons_warnings(store):
    w = lessons.proactive_warnings(store)
    assert isinstance(w, list) and w
    assert {"tag", "current_failure", "projected_failure", "correlation"} <= set(w[0])


def test_lessons_patterns(store):
    p = lessons.systemic_patterns(store)
    assert p and all("failure_mode" in x for x in p)


# ── ml ──────────────────────────────────────────────────────────────────────
def test_ml_predict():
    r = ml.predict(300.0, 312.0, 1320.0, 55.0, 210.0)
    assert 0.0 <= r["failure_probability"] <= 1.0
    assert r["source"] in ("ai4i_random_forest", "heuristic")


# ── report ──────────────────────────────────────────────────────────────────
def test_report(store):
    md = report.asset_report(store, "P-101A")
    assert md and "Asset Intelligence Report" in md and "Compliance" in md


# ── API ─────────────────────────────────────────────────────────────────────
def test_health_endpoint(client):
    d = client.get("/health").json()
    assert d["status"] == "ok" and d["store"]["equipment"] >= 15


def test_graph_endpoint(client):
    d = client.get("/graph/equipment").json()
    assert len(d["nodes"]) >= 15 and len(d["edges"]) >= 10


def test_rca_query_endpoint(client):
    d = client.post("/rca/query", json={"query": "P-101A 47Hz vibration"}).json()
    assert d["focus_tag"] == "P-101A" and d["confidence"] >= 80
    assert d["citations"]["hallucinated"] == []


def test_intel_endpoints(client):
    assert client.get("/intel/compliance/plant").status_code == 200
    assert client.get("/intel/lessons/warnings").status_code == 200
    assert client.get("/intel/overdue").status_code == 200
    assert client.get("/intel/report/P-101A").status_code == 200
    assert client.get("/graph/equipment/P-101A").status_code == 200
    assert client.get("/intel/documents/INS-2025-0847").status_code == 200
    assert client.get("/intel/documents/NOPE-0000").status_code == 404
    t = client.get("/intel/telemetry/P-101A")
    assert t.status_code == 200 and t.json()["current"] == 4.7 and len(t.json()["zones"]) == 4
    assert client.get("/intel/telemetry/NOPE").status_code == 404


def test_rca_causal_object(client):
    d = client.post("/rca/query", json={"query": "P-101A 47Hz vibration"}).json()
    assert d["causal"]["from_tag"] == "V-201" and d["causal"]["to_tag"] == "P-101A"


def test_knowledge_capture(client):
    r = client.post("/intel/knowledge/capture",
                    json={"equipment_tag": "P-101A", "title": "t", "content": "impeller reclearance tip"})
    assert r.status_code == 200 and r.json()["id"].startswith("TRIBAL-")


# ── ingestion / entity extraction ───────────────────────────────────────────
def test_entity_extraction(store):
    sample = store.sample_documents()[0]["text"]
    ents = ingest.extract_entities(sample, store)
    tags = [e["value"] for e in ents["equipment"]]
    assert "P-101A" in tags and "STD-130" not in tags       # standards fragment excluded
    assert any(r["resolves_to"] == "OISD-STD-130" for r in ents["regulatory"])
    assert ents["parameters"] and ents["dates"] and ents["personnel"]


def test_ingest_preview_and_commit(store):
    txt = store.sample_documents()[0]["text"]
    pv = ingest.preview(txt, store)
    assert pv["entity_count"] > 5 and pv["linkage_rate"] >= 0.8
    before = len(store.documents_for("P-101A", limit=99))
    res = ingest.commit(txt, "Test ingest", "Inspection", store)
    assert res["document"]["id"].startswith("DOC-") and "P-101A" in res["linked_equipment"]
    assert len(store.documents_for("P-101A", limit=99)) == before + 1


# ── copilot ─────────────────────────────────────────────────────────────────
def test_copilot(store):
    a = copilot.answer("what is the condition and history of P-101A?", store)
    assert a["focus_tag"] == "P-101A" and a["sources"] and a["confidence"] >= 40
    assert a["citations"]["hallucinated"] == []


# ── overview / evaluation / knowledge graph ─────────────────────────────────
def test_overview(store):
    o = overview.plant_overview(store)
    assert o["assets"]["total"] >= 15 and o["documents"]["total"] >= 60
    assert 0 <= o["compliance"]["rate"] <= 1 and o["top_failure_modes"]


def test_evaluation(store):
    e = overview.evaluation(store)
    assert e["benchmark"]["accuracy"] == 1.0 and e["benchmark"]["citation_faithfulness"] == 1.0
    assert e["entity_extraction"]["linkage_accuracy"] >= 0.9
    assert e["kg_completeness"]["documents_linked"] > 0.9


def test_knowledge_graph(store):
    kg = overview.knowledge_graph(store, "P-101A")
    cats = {n["data"]["category"] for n in kg["nodes"]}
    assert {"Equipment", "Document", "FailureMode", "Regulation"} <= cats
    assert len(kg["edges"]) > 10


def test_new_endpoints(client):
    assert client.get("/intel/overview").status_code == 200
    assert client.get("/intel/evaluation").status_code == 200
    assert client.get("/intel/samples").status_code == 200
    assert client.get("/graph/knowledge/P-101A").status_code == 200
    assert client.post("/intel/ask", json={"query": "P-101A history"}).status_code == 200
    p = client.post("/intel/ingest/preview", json={"text": "P-101A vibration 4.7 mm/s per OISD-STD-130"})
    assert p.status_code == 200 and p.json()["entity_count"] >= 3


# ── insights (timeline / similar / deviations / roi / cost / audit) ─────────
def test_insights(store):
    tl = insights.timeline(store, "P-101A")
    assert tl["events"] and all(e["date"] for e in tl["events"])
    sim = insights.similar_incidents(store, "P-101A")
    assert isinstance(sim["incidents"], list)
    dev = insights.deviations(store)
    assert dev["count"] >= 1 and all(d["value"] >= d["alarm"] for d in dev["deviations"])
    r = insights.roi(500, 40, 14, 60, 900, 20, 1500000, 20)
    assert r["total_annual_value_inr"] > 0 and r["total_annual_value_cr"] > 0
    assert insights.cost_model(store)["current_corpus"]["assets"] >= 15
    assert "Compliance Evidence Package" in insights.audit_pack(store, "K-501")


def test_eval_precision_recall(store):
    e = overview.evaluation(store)
    assert 0 <= e["entity_extraction"]["f1"] <= 1 and e["entity_extraction"]["precision"] >= 0.8
    assert e["graph_vs_search"]["graph_root_cause_rate"] > e["graph_vs_search"]["keyword_search_root_cause_rate"]


def test_kg_has_area_and_causality(store):
    kg = overview.knowledge_graph(store, "P-101A")
    cats = {n["data"]["category"] for n in kg["nodes"]}
    assert "Area" in cats
    assert any(e["data"]["rel"] == "CAUSES" for e in kg["edges"])


def test_rca_has_ruledout_and_ttf():
    r = deterministic_rca("P-101A 47Hz vibration spike")
    assert "Ruled Out" in r["answer"] and "Next Checks" in r["answer"]


def test_insight_endpoints(client):
    for ep in ["/intel/timeline/P-101A", "/intel/similar/P-101A", "/intel/deviations",
               "/intel/cost-model", "/intel/audit/K-501", "/intel/roi"]:
        assert client.get(ep).status_code == 200
