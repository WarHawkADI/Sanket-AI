"""P&ID graph endpoints — Cytoscape-ready JSON, backend-agnostic via the Store."""
from fastapi import APIRouter, HTTPException
from backend.graph.store import get_store
from backend.agent import overview
from backend.api.models import GraphData

router = APIRouter()


@router.get("/knowledge/{tag}")
def knowledge_graph(tag: str, depth: int = 2):
    """Multi-entity knowledge graph around an asset (Equipment/Document/FailureMode/Person/Regulation)."""
    kg = overview.knowledge_graph(get_store(), tag, depth)
    if not kg["nodes"]:
        raise HTTPException(status_code=404, detail=f"Equipment {tag} not found")
    return kg


def _node(e, focus=None):
    return {"data": {
        "id": e["tag"], "label": e["tag"], "name": e.get("name", "") or "",
        "type": e.get("type", "") or "", "criticality": e.get("criticality", "MEDIUM") or "MEDIUM",
        "area": e.get("area", "") or "", "description": e.get("description", "") or "",
        **({"is_focus": e["tag"] == focus} if focus else {}),
    }}


def _edge(c):
    return {"data": {
        "id": f"{c['source']}->{c['target']}", "source": c["source"], "target": c["target"],
        "pipe_tag": c.get("pipe_tag", "") or "", "medium": c.get("medium", "") or "",
        "flow_direction": c.get("flow_direction", "") or "",
    }}


@router.get("/equipment", response_model=GraphData)
def get_all_equipment():
    """All equipment nodes + connections for the graph view."""
    store = get_store()
    nodes = [_node(e) for e in store.all_equipment()]
    edges = [_edge(c) for c in store.all_connections()]
    return GraphData(nodes=nodes, edges=edges)


@router.get("/equipment/{tag}")
def get_equipment_detail(tag: str):
    """Full detail for one asset: properties + recent documents."""
    store = get_store()
    eq = store.get_equipment(tag)
    if not eq:
        raise HTTPException(status_code=404, detail=f"Equipment {tag} not found")
    docs = store.documents_for(tag, limit=20)
    return {"equipment": {k: v for k, v in eq.items() if k not in ("props", "_tokens")},
            "documents": [{k: d.get(k) for k in ("id", "type", "subtype", "title", "date",
                                                 "severity", "priority", "status")} for d in docs]}


@router.get("/neighborhood/{tag}", response_model=GraphData)
def get_neighborhood(tag: str, depth: int = 2):
    """Equipment within N hops of a tag + their connections (for path highlighting)."""
    store = get_store()
    if not store.get_equipment(tag):
        raise HTTPException(status_code=404, detail=f"Equipment {tag} not found")
    nodes_raw, edges_raw = store.neighborhood(tag, depth)
    return GraphData(nodes=[_node(e, focus=tag) for e in nodes_raw],
                     edges=[_edge(c) for c in edges_raw])
