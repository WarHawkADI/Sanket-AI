import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from backend.api.routes import rca, graph, intelligence
from backend.graph.store import get_store
from backend.agent.rca_agent import llm_available
from backend.config import now

app = FastAPI(
    title="Sanket AI — Asset Reasoning Brain",
    description="Industrial Knowledge Intelligence: graph-topology RCA, compliance, and lessons-learned",
    version="2.0.0",
)

# CORS: explicit origins (credentialed wildcard is invalid per the CORS spec)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("SANKET_CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rca.router, prefix="/rca", tags=["rca"])
app.include_router(graph.router, prefix="/graph", tags=["graph"])
app.include_router(intelligence.router, prefix="/intel", tags=["intelligence"])


@app.get("/health")
def health():
    """Backend + data + LLM status — enough to catch a broken demo before you're on stage."""
    try:
        h = get_store().health()
    except Exception as exc:
        h = {"backend": "error", "ok": False, "error": str(exc)}
    mode = "llm-agent" if llm_available() else "deterministic"
    return {
        "status": "ok" if h.get("ok") else "degraded",
        "rca_mode": mode,
        "model": "llama-3.3-70b-versatile (Groq)" if mode == "llm-agent" else "deterministic engine (no API key)",
        "store": h,
        "plant_now": now().isoformat(),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/ui/index.html")


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
