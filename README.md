# Sanket AI — Asset Reasoning Brain

> **ET AI Hackathon 2.0 · Problem VIII — Industrial Knowledge Intelligence**
> A Unified Asset & Operations Brain that turns a plant's P&ID + CMMS history into a live reasoning engine.

**Live demo:** [sanket-ai-pearl.vercel.app](https://sanket-ai-pearl.vercel.app)

Sanket AI makes a plant's **physical topology the reasoning substrate**. When a pump vibrates, it traverses the P&ID equipment graph, pulls inspection logs and work orders for every upstream neighbour, correlates ISO-14224 co-failure statistics, and returns a **cited causal chain with a computed confidence** — not a document ranked by keyword similarity.

```
Failure query ─► identify asset ─► traverse P&ID upstream ─► pull CMMS evidence
             ─► ISO-14224 co-failure correlation ─► evidence-scored confidence
             ─► verified, cited root-cause  (V-201 cavitation → P-101A vibration, 97%)
```

---

## Why this is different

**RAG finds documents. It cannot reason about physical connectivity.** A centrifugal pump's 47 Hz vibration cannot be diagnosed without knowing that a control valve two nodes upstream is cavitating. Sanket makes plant topology the reasoning substrate, not just a metadata filter — and every number it reports is computed from evidence, not invented by an LLM.

The platform covers **all five pillars of the brief** — a genuine *unified brain*, not just an RCA agent:

| Pillar | What it does |
|---|---|
| **Universal Ingestion & Knowledge Graph** | Extracts entities (equipment tags, parameters, regulatory refs, personnel, dates) from any document — inspection reports, emails, OEM manuals, scanned forms, incident records — and links them into a unified multi-entity knowledge graph |
| **Expert Knowledge Copilot** | Cited Q&A across the whole corpus, with a computed confidence and direct links to source documents |
| **Maintenance & RCA** | Graph-topology root-cause analysis with cited causal chains + computed confidence |
| **Quality & Compliance** | Maps OISD / Factory Act / PESO / ISO / API / CPCB clauses to each asset's evidence, flags gaps, generates evidence packages |
| **Lessons-Learned / Failure Intelligence** | Projects the *next* likely failure per asset from co-failure signatures; surfaces systemic patterns |

Plus **predictive maintenance** (trained UCI AI4I classifier as an agent tool) and **Knowledge-Cliff Capture** — turning a retiring expert's know-how into a permanent, queryable graph node.

The UI is a **seven-view command centre**: Overview · Diagnose · Ask · Ingest · Knowledge Graph · Compliance · Capture — with **validated evaluation metrics on the landing page** (benchmark accuracy, citation faithfulness, entity-link accuracy, KG completeness, time-to-answer).

---

## Runs in 3 commands — no Docker, no database, no API key

The centrepiece: a **Neo4j-optional data layer**. If no database is reachable, Sanket loads an in-memory knowledge graph from seed data and answers with a **deterministic RCA engine** (real graph traversal, real evidence, computed confidence — just no LLM). It upgrades to Neo4j + the Groq LLM agent automatically the moment they're available.

```bash
python -m venv .venv && .venv/Scripts/activate      # (Linux/mac: source .venv/bin/activate)
pip install -r backend/requirements.txt
python scripts/generate_seed_data.py                # writes backend/data/*.json

# run fully offline (in-memory + deterministic RCA):
set SANKET_FORCE_MEMSTORE=1                          # (Linux/mac: export SANKET_FORCE_MEMSTORE=1)
uvicorn backend.main:app --port 8000
```

Open **http://localhost:8000** — the UI loads directly. Click a demo query → watch the graph flash upstream, the trace panel fire tools, citations open to real documents, and the metrics banner show answer-time vs. a ~4-hour manual search.

### Deploy on Vercel

This repository includes a root `app.py` entrypoint and `vercel.json`, so Vercel
can discover the FastAPI application and bundle the frontend, seed data, and ML
models with the Python function.

1. Push the repository to GitHub, GitLab, or Bitbucket and import it in Vercel.
2. Keep **Root Directory** set to the repository root and leave the Build and
   Output Directory fields empty (Framework Preset may be FastAPI or automatic).
3. In **Project Settings → Environment Variables**, add
   `SANKET_FORCE_MEMSTORE=1` for Production, Preview, and Development.
4. Deploy, then verify [`https://sanket-ai-pearl.vercel.app/health`](https://sanket-ai-pearl.vercel.app/health). It should report
   `status: ok` and `store.backend: in-memory`.

The UI is at the deployment root (which redirects to `/ui/index.html`). No
Neo4j or Groq key is required for the deterministic demo. To enable the LLM
agent, add `GROQ_API_KEY`. To use Neo4j, use a hosted Neo4j URI reachable from
Vercel—`bolt://localhost:7687` points back at the serverless function and will
not reach the Docker container on your computer.

You can also deploy from a terminal with Vercel CLI 48.1.8 or newer:

```bash
npx vercel@latest
npx vercel@latest --prod
```

Vercel functions have an ephemeral/read-only application filesystem. The seeded
demo data is safe because it is read-only, but in-memory knowledge captures and
ingested documents are not durable across cold starts. Use hosted Neo4j (or
another persistent database) before relying on those write endpoints in production.

### Full mode (Neo4j graph + Groq LLM agent)

```bash
cp .env.example .env          # set GROQ_API_KEY (free at console.groq.com/keys) + NEO4J_*
docker compose up -d neo4j    # or a local Neo4j 5.x (needs Java 17+)
python -m backend.ingestion.run_all --skip-csb
uvicorn backend.main:app --port 8000
```

`/health` reports which mode is live (`deterministic` vs `llm-agent`) and the store backend.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│ frontend/index.html — single file, mobile-first, zero build    │
│ Cytoscape graph · SSE stream · clickable citations → drawer     │
│ metrics banner · computed confidence · Compliance/Warnings tabs │
└──────────────────────────┬────────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼────────────────────────────────────┐
│ FastAPI (backend/main.py)                                       │
│  /rca/stream · /rca/query · /graph/* · /intel/* · /health       │
├─────────────────────────────────────────────────────────────────┤
│ Store facade (backend/graph/store.py)                           │
│   Neo4jStore  ⇄  MemStore   ← auto-selected, identical interface │
├─────────────────────────────────────────────────────────────────┤
│ RCA engine (deterministic + LLM) · confidence · citations       │
│ compliance · lessons · ml · report                              │
│ 11 agent tools · Groq llama-3.3-70b (when key present)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Status, RCA mode, store backend + counts |
| `GET /graph/equipment` | All nodes + edges (Cytoscape JSON) |
| `GET /graph/equipment/{tag}` | Asset detail + recent documents |
| `GET /graph/neighborhood/{tag}?depth=N` | N-hop subgraph |
| `POST /rca/query` | Non-streaming RCA (JSON: answer, confidence, citations, metrics) |
| `GET /rca/stream?query=…` | SSE — `tool_call` / `tool_result` / `token` / `meta` / `error`, ends `[DONE]` |
| `GET /intel/compliance/plant` · `/compliance/{tag}` | Compliance roll-up / per-asset gaps |
| `GET /intel/lessons/warnings` · `/lessons/patterns` | Proactive warnings / systemic patterns |
| `GET /intel/overdue` | Overdue inspections |
| `GET /intel/predict?...` | Predictive-maintenance classifier |
| `GET /intel/report/{tag}` | One-click asset intelligence report (markdown) |
| `GET /intel/documents/{id}` | Source document (powers clickable citations) |
| `POST /intel/knowledge/capture` | Knowledge-Cliff Capture — persist expert insight as a node |

---

## Trust & evaluation

- **Computed confidence** — `f(corroborating docs, recency, severity, ISO-14224 correlation, confirmed path)`. Every component is returned so the score is auditable (`backend/agent/confidence.py`).
- **Citation verification** — every cited document ID is checked against the graph; hallucinated IDs are flagged `[unverified]` (`backend/agent/citations.py`).
- **Benchmark** — `python scripts/run_benchmark.py` scores a gold Q&A set: **10/10 focus accuracy, 100% citation faithfulness, ~1 ms answer time.**
- **Tests** — `python -m pytest -q` → 20 tests, all offline (no external services).

---

## Demo scenarios

| Query | Result |
|---|---|
| *P-101A 47Hz vibration spike* | **V-201 cavitation, 97%** — cites INS-2025-0847 + WO-2025-1034; upstream path P-101A ← V-201 |
| *K-501 compressor high vibration* | **F-501 lube-oil filter blockage, 97%** — second circuit, oil-starvation chain |
| *Which HIGH-criticality equipment is overdue?* | structural + compliance answer |

---

## Project structure

```
backend/
  main.py                 FastAPI app + robust /health + static mount
  config.py               anchored 'plant now', Groq model fallbacks
  graph/
    store.py              Store facade: MemStore ⇄ Neo4jStore (the key abstraction)
    client.py             Neo4j driver singleton
  agent/
    rca_engine.py         deterministic RCA (no-LLM) — traversal + evidence + confidence
    rca_agent.py          LangGraph ReAct agent (Groq) — used when a key is set
    confidence.py         evidence-based confidence scoring
    citations.py          citation extraction + verification
    compliance.py         regulatory gap engine
    lessons.py            proactive failure warnings + systemic patterns
    ml.py                 predictive-maintenance classifier wrapper
    report.py             one-click asset report (markdown)
    prompts.py            system prompt (parallel tools, cite-only-real rule)
    tools/                traversal · documents · patterns · analytics (11 tools)
  api/routes/             rca · graph · intelligence
  data/                   seed graph, work orders, inspections, taxonomy, clauses, benchmark
frontend/index.html       full UI — single file, responsive, no build step
scripts/
  generate_seed_data.py   deterministic seed generator (17 assets, 30 WOs, 52 inspections)
  run_benchmark.py        domain-expert benchmark runner
tests/test_sanket.py      20 offline regression + unit tests
```

---

## Datasets

The demo runs entirely on the generated seed corpus (real ISO-14224 taxonomy + realistic CMMS records). Optional real datasets — U.S. CSB incident reports, Microsoft Azure PdM, UCI AI4I/Hydraulic — can be ingested into Neo4j via `get_datasets.sh` + `backend.ingestion.run_all` (require the optional heavy stack). The two trained UCI classifiers ship in `models/`.

---

## Hackathon context

**Event:** ET AI Hackathon 2.0 · **Problem VIII — Industrial Knowledge Intelligence**
**Core claim:** graph-topology reasoning collapses cross-system RCA from hours to seconds by making physical plant connectivity — not keyword similarity — the reasoning substrate.
