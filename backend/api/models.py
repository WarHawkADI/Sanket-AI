from pydantic import BaseModel
from typing import Any, Optional


class RCAQuery(BaseModel):
    query: str


class RCAResponse(BaseModel):
    query: str
    response: str
    mode: str = "deterministic"
    focus_tag: Optional[str] = None
    causal: Optional[dict[str, Any]] = None
    confidence: Optional[int] = None
    confidence_breakdown: list[dict[str, Any]] = []
    citations: dict[str, Any] = {}
    metrics: dict[str, Any] = {}
    trace: list[dict[str, Any]] = []


class GraphData(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class KnowledgeCapture(BaseModel):
    equipment_tag: str
    title: str
    content: str
    author: str = ""
    date: str = ""


class AskQuery(BaseModel):
    query: str


class IngestRequest(BaseModel):
    text: str
    title: str = ""
    doc_type: str = "Ingested document"
