"""
Unified data-access layer for Sanket AI.

Two interchangeable backends behind one interface:

  • Neo4jStore  — production path, backed by the Neo4j knowledge graph.
  • MemStore    — zero-dependency in-memory graph loaded from backend/data/*.json.

`get_store()` probes Neo4j once; if it is unreachable it transparently falls
back to MemStore.  This is what lets the whole application — graph view, RCA
agent, compliance engine, metrics — boot and demo on a laptop with **no Docker,
no Neo4j and no API keys**, and upgrade to the graph backend automatically the
moment a database is available.

Every method returns plain dicts/lists so the two backends are drop-in equal.
"""
from __future__ import annotations

import json
import os
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ─────────────────────────────────────────────────────────────────────────────
#  Data loading helpers
# ─────────────────────────────────────────────────────────────────────────────
def _load(name: str, default):
    path = DATA_DIR / name
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _tokenize(text: str) -> set:
    return {t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if len(t) > 2}


# ─────────────────────────────────────────────────────────────────────────────
#  In-memory backend
# ─────────────────────────────────────────────────────────────────────────────
class MemStore:
    """Pure-Python graph built from the seed JSON files."""

    backend = "in-memory"

    def __init__(self):
        graph = _load("demo_pid_graph.json", {"equipment": [], "connections": []})
        self.equipment: dict[str, dict] = {}
        for eq in graph.get("equipment", []):
            self.equipment[eq["tag"]] = {
                "tag": eq["tag"],
                "name": eq.get("name", ""),
                "type": eq.get("type", ""),
                "criticality": eq.get("criticality", "MEDIUM"),
                "area": eq.get("area", ""),
                "description": eq.get("description", ""),
                "pid_source": graph.get("pid_id", "DEMO"),
                "props": eq,
            }

        # directed flow edges (CONNECTED_TO); sensors kept separate
        self.edges: list[dict] = []
        for c in graph.get("connections", []):
            if c.get("connection_type") == "MECHANICAL_SENSOR":
                continue
            self.edges.append({
                "source": c["from_tag"],
                "target": c["to_tag"],
                "pipe_tag": c.get("pipe_tag") or "",
                "medium": c.get("medium") or "",
                "flow_direction": c.get("flow_direction") or "",
                "diameter_in": c.get("nominal_diameter_in") or 0,
            })

        # documents (work orders + inspection logs) with their equipment link
        self.documents: list[dict] = []
        for wo in _load("work_orders.json", []):
            findings = wo.get("findings", "")
            action = wo.get("action_taken", "")
            self.documents.append({
                "id": wo["id"], "type": "WORK_ORDER", "subtype": wo.get("type", ""),
                "title": wo.get("title", ""),
                "date": wo.get("date_raised") or "", "content": f"Findings: {findings}\nAction taken: {action}",
                "priority": wo.get("priority", ""), "status": wo.get("status", ""),
                "severity": "", "tag": wo.get("equipment_tag", ""),
                "failure_mode": wo.get("iso14224_failure_mode"),
                "technician": wo.get("technician", ""),
            })
        for log in _load("inspection_logs.json", []):
            findings = log.get("findings", "")
            rec = log.get("recommendation", "")
            self.documents.append({
                "id": log["id"], "type": "INSPECTION_LOG", "subtype": log.get("inspection_type", ""),
                "title": f"{log.get('equipment_tag','')} — {log.get('inspection_type','')}",
                "date": log.get("date", ""), "content": f"Findings: {findings}\nRecommendation: {rec}",
                "priority": "", "status": "", "severity": log.get("severity", ""),
                "tag": log.get("equipment_tag", ""),
                "failure_mode": log.get("iso14224_failure_mode_detected"),
                "inspector": log.get("inspector", ""),
                "next_inspection": log.get("next_inspection", ""),
            })

        # failure-mode taxonomy
        tax = _load("iso14224_taxonomy.json", {"equipment_classes": [], "co_failure_statistics": []})
        self.failure_modes: dict[str, dict] = {}
        self.class_modes: dict[str, list] = {}
        for cls in tax.get("equipment_classes", []):
            codes = []
            for fm in cls.get("failure_modes", []):
                self.failure_modes[fm["code"]] = {
                    "code": fm["code"], "description": fm.get("description", ""),
                    "mechanism": ", ".join(fm.get("mechanisms", [])),
                    "frequency": fm.get("iso14224_frequency", ""),
                    "equipment_class": cls["class"],
                }
                codes.append(fm["code"])
            self.class_modes[cls["class"]] = codes
        self.co_failures: list[dict] = tax.get("co_failure_statistics", [])

        # compliance clauses (new pillar) and captured tribal knowledge
        self.clauses: list[dict] = _load("compliance_clauses.json", [])
        self.telemetry_map: dict = _load("telemetry.json", {})
        self.samples: list[dict] = _load("sample_documents.json", [])
        self.tribal: list[dict] = []  # runtime knowledge-cliff captures

        # precompute doc token sets for keyword search
        for d in self.documents:
            d["_tokens"] = _tokenize(f"{d['title']} {d['content']}")

    # ---- health ------------------------------------------------------------
    def health(self) -> dict:
        return {
            "backend": self.backend, "ok": len(self.equipment) > 0,
            "equipment": len(self.equipment), "documents": len(self.documents),
            "failure_modes": len(self.failure_modes), "clauses": len(self.clauses),
        }

    # ---- equipment / topology ---------------------------------------------
    def get_equipment(self, tag: str) -> Optional[dict]:
        return self.equipment.get(tag)

    def all_equipment(self) -> list[dict]:
        return [e for e in self.equipment.values() if e.get("pid_source")]

    def all_connections(self) -> list[dict]:
        return list(self.edges)

    def _bfs(self, tag: str, depth: int, upstream: bool) -> list[dict]:
        depth = max(1, min(int(depth), 5))
        # adjacency
        adj: dict[str, list] = {}
        for e in self.edges:
            a, b = (e["target"], e["source"]) if upstream else (e["source"], e["target"])
            adj.setdefault(a, []).append(b)
        seen = {tag}
        out, q = [], deque([(tag, 0)])
        while q:
            node, hops = q.popleft()
            if hops >= depth:
                continue
            for nb in adj.get(node, []):
                if nb in seen:
                    continue
                seen.add(nb)
                eq = self.equipment.get(nb, {"tag": nb})
                out.append({**{k: eq.get(k, "") for k in ("tag", "name", "type", "criticality", "description")},
                            "hops": hops + 1})
                q.append((nb, hops + 1))
        out.sort(key=lambda r: r["hops"])
        return out

    def traverse(self, tag: str, direction: str, depth: int = 3) -> list[dict]:
        return self._bfs(tag, depth, upstream=(direction == "upstream"))

    def neighborhood(self, tag: str, depth: int = 2) -> tuple[list, list]:
        depth = max(1, min(int(depth), 5))
        # undirected BFS
        adj: dict[str, set] = {}
        for e in self.edges:
            adj.setdefault(e["source"], set()).add(e["target"])
            adj.setdefault(e["target"], set()).add(e["source"])
        seen = {tag}
        q = deque([(tag, 0)])
        while q:
            node, h = q.popleft()
            if h >= depth:
                continue
            for nb in adj.get(node, set()):
                if nb not in seen:
                    seen.add(nb)
                    q.append((nb, h + 1))
        nodes = [self.equipment[t] for t in seen if t in self.equipment]
        edges = [e for e in self.edges if e["source"] in seen and e["target"] in seen]
        return nodes, edges

    # ---- documents ---------------------------------------------------------
    def documents_for(self, tag: str, types: Optional[Iterable[str]] = None, limit: int = 10) -> list[dict]:
        types = set(types) if types else None
        docs = [d for d in self.documents
                if (d["tag"] == tag or tag in d.get("linked_tags", []))
                and (types is None or d["type"] in types)]
        docs.sort(key=lambda d: d["date"], reverse=True)
        return docs[:limit]

    def personnel(self) -> list[str]:
        names = set()
        for d in self.documents:
            for k in ("inspector", "technician", "author"):
                v = d.get(k)
                if v and "Auto-generated" not in v:
                    names.add(v)
        return sorted(names)

    def add_document(self, doc: dict, tags: list[str]) -> dict:
        doc["tag"] = tags[0] if tags else ""
        doc["linked_tags"] = tags
        doc["_tokens"] = _tokenize(f"{doc.get('title','')} {doc.get('content','')}")
        self.documents.append(doc)
        return doc

    def get_document(self, doc_id: str) -> Optional[dict]:
        return next((d for d in self.documents if d["id"] == doc_id), None)

    def document_ids(self) -> set:
        return {d["id"] for d in self.documents}

    def search(self, query: str, tags: Optional[list[str]] = None, limit: int = 5) -> list[dict]:
        q_tokens = _tokenize(query)
        pool = [d for d in self.documents if (tags is None or d["tag"] in tags)]
        scored = []
        for d in pool:
            overlap = len(q_tokens & d["_tokens"])
            if overlap:
                scored.append((overlap, d))
        scored.sort(key=lambda x: (x[0], x[1]["date"]), reverse=True)
        return [d for _, d in scored[:limit]]

    # ---- failure modes / patterns -----------------------------------------
    def failure_modes_for(self, equipment_type: str) -> list[dict]:
        order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
        modes = [self.failure_modes[c] for c in self.class_modes.get(equipment_type, [])]
        modes.sort(key=lambda m: order.get(m["frequency"], 4))
        return modes

    def co_failure(self, tags: list[str]) -> tuple[list, list]:
        # failure-mode correlations for the equipment classes present in `tags`
        classes = {self.equipment[t]["type"] for t in tags if t in self.equipment}
        active_codes = set()
        for c in classes:
            active_codes.update(self.class_modes.get(c, []))
        patterns = []
        for s in self.co_failures:
            if s["primary"] in active_codes:
                patterns.append(s)
        patterns.sort(key=lambda s: s.get("correlation", 0), reverse=True)
        # shared documents between tag pairs
        shared = []
        for i, a in enumerate(tags):
            for b in tags[i + 1:]:
                docs = [d["id"] for d in self.documents if d["tag"] in (a, b)]
                # documents that literally mention the other tag
                cross = [d["id"] for d in self.documents
                         if d["tag"] == a and b in d["content"]] + \
                        [d["id"] for d in self.documents
                         if d["tag"] == b and a in d["content"]]
                if cross:
                    shared.append({"tag1": a, "tag2": b, "shared_docs": len(cross), "example_docs": cross[:3]})
        return patterns, shared

    # ---- compliance / lessons / tribal knowledge --------------------------
    def compliance_clauses(self) -> list[dict]:
        return list(self.clauses)

    def telemetry(self, tag: str):
        return self.telemetry_map.get(tag)

    def sample_documents(self) -> list[dict]:
        return list(self.samples)

    def overdue_inspections(self, as_of: str) -> list[dict]:
        rows = []
        for d in self.documents:
            nxt = d.get("next_inspection")
            if nxt and nxt < as_of:
                rows.append({"tag": d["tag"], "doc_id": d["id"], "due": nxt,
                             "severity": d.get("severity", ""), "title": d["title"]})
        rows.sort(key=lambda r: r["due"])
        return rows

    def capture_knowledge(self, entry: dict) -> None:
        self.tribal.append(entry)
        # tribal knowledge is queryable as a document immediately
        doc = {
            "id": entry["id"], "type": "TRIBAL_KNOWLEDGE", "title": entry.get("title", ""),
            "date": entry.get("date", ""), "content": entry.get("content", ""),
            "priority": "", "status": "", "severity": "",
            "tag": entry.get("equipment_tag", ""), "failure_mode": None,
            "author": entry.get("author", ""),
        }
        doc["_tokens"] = _tokenize(f"{doc['title']} {doc['content']}")
        self.documents.append(doc)


# ─────────────────────────────────────────────────────────────────────────────
#  Neo4j backend (same interface, Cypher-backed)
# ─────────────────────────────────────────────────────────────────────────────
class Neo4jStore:
    backend = "neo4j"

    def __init__(self, client):
        self.db = client
        self._mem = MemStore()  # taxonomy / clauses reused for enrichment + co-failure fallback

    def health(self) -> dict:
        try:
            eq = self.db.run("MATCH (e:Equipment) RETURN count(e) AS c")[0]["c"]
            docs = self.db.run("MATCH (d:Document) RETURN count(d) AS c")[0]["c"]
            fm = self.db.run("MATCH (f:FailureMode) RETURN count(f) AS c")[0]["c"]
            return {"backend": self.backend, "ok": eq > 0, "equipment": eq,
                    "documents": docs, "failure_modes": fm, "clauses": len(self._mem.clauses)}
        except Exception as exc:
            return {"backend": self.backend, "ok": False, "error": str(exc),
                    "equipment": 0, "documents": 0, "failure_modes": 0, "clauses": 0}

    def get_equipment(self, tag):
        rows = self.db.run("MATCH (e:Equipment {tag:$tag}) RETURN e", tag=tag)
        if not rows:
            return None
        e = dict(rows[0]["e"])
        e["props"] = e
        return e

    def all_equipment(self):
        rows = self.db.run(
            "MATCH (e:Equipment) WHERE e.pid_source IS NOT NULL "
            "RETURN e.tag AS tag, e.name AS name, e.type AS type, e.criticality AS criticality, "
            "e.area AS area, e.description AS description ORDER BY e.tag")
        return [dict(r) for r in rows]

    def all_connections(self):
        rows = self.db.run(
            "MATCH (a:Equipment)-[r:CONNECTED_TO]->(b:Equipment) "
            "WHERE a.pid_source IS NOT NULL AND b.pid_source IS NOT NULL "
            "RETURN a.tag AS source, b.tag AS target, r.pipe_tag AS pipe_tag, "
            "r.medium AS medium, r.flow_direction AS flow_direction")
        return [dict(r) for r in rows]

    def traverse(self, tag, direction, depth=3):
        depth = max(1, min(int(depth), 5))
        arrow = "<-[:CONNECTED_TO*1..%d]-" if direction == "upstream" else "-[:CONNECTED_TO*1..%d]->"
        arrow = arrow % depth
        rows = self.db.run(
            f"MATCH path = (s:Equipment {{tag:$tag}}){arrow}(n:Equipment) "
            "RETURN n.tag AS tag, n.name AS name, n.type AS type, n.criticality AS criticality, "
            "n.description AS description, length(path) AS hops ORDER BY hops", tag=tag)
        return [dict(r) for r in rows]

    def neighborhood(self, tag, depth=2):
        depth = max(1, min(int(depth), 5))
        rows = self.db.run(
            f"MATCH (c:Equipment {{tag:$tag}}) "
            f"MATCH p=(c)-[:CONNECTED_TO*0..{depth}]-(n:Equipment) "
            "WITH collect(DISTINCT n) AS ns UNWIND ns AS e "
            "RETURN e.tag AS tag, e.name AS name, e.type AS type, e.criticality AS criticality, "
            "e.area AS area, e.description AS description, e.pid_source AS pid_source", tag=tag)
        nodes = [dict(r) for r in rows]
        tags = [n["tag"] for n in nodes]
        erows = self.db.run(
            "MATCH (a:Equipment)-[r:CONNECTED_TO]->(b:Equipment) "
            "WHERE a.tag IN $tags AND b.tag IN $tags "
            "RETURN a.tag AS source, b.tag AS target, r.pipe_tag AS pipe_tag, r.medium AS medium",
            tags=tags)
        return nodes, [dict(r) for r in erows]

    def documents_for(self, tag, types=None, limit=10):
        rows = self.db.run(
            "MATCH (e:Equipment {tag:$tag})<-[:DESCRIBES]-(d:Document) "
            "RETURN d.id AS id, d.type AS type, d.title AS title, d.date AS date, d.content AS content, "
            "d.priority AS priority, d.status AS status, d.severity AS severity, "
            "d.next_inspection AS next_inspection ORDER BY d.date DESC LIMIT $limit",
            tag=tag, limit=limit)
        docs = [dict(r) for r in rows]
        if types:
            types = set(types)
            docs = [d for d in docs if d["type"] in types]
        return docs

    def get_document(self, doc_id):
        rows = self.db.run("MATCH (d:Document {id:$id}) RETURN d", id=doc_id)
        return dict(rows[0]["d"]) if rows else None

    def document_ids(self):
        rows = self.db.run("MATCH (d:Document) RETURN d.id AS id")
        return {r["id"] for r in rows}

    def search(self, query, tags=None, limit=5):
        if tags:
            rows = self.db.run(
                "MATCH (d:Document)-[:DESCRIBES]->(e:Equipment) WHERE e.tag IN $tags "
                "RETURN DISTINCT d.id AS id, d.type AS type, d.title AS title, d.date AS date, "
                "d.content AS content, d.tag AS tag ORDER BY d.date DESC LIMIT 50", tags=tags)
        else:
            rows = self.db.run(
                "MATCH (d:Document) RETURN d.id AS id, d.type AS type, d.title AS title, "
                "d.date AS date, d.content AS content ORDER BY d.date DESC LIMIT 200")
        # rank in Python with the same keyword scorer as MemStore (backend-agnostic behaviour)
        q_tokens = _tokenize(query)
        scored = []
        for r in rows:
            d = dict(r)
            overlap = len(q_tokens & _tokenize(f"{d.get('title','')} {d.get('content','')}"))
            if overlap:
                scored.append((overlap, d))
        scored.sort(key=lambda x: (x[0], x[1].get("date", "")), reverse=True)
        return [d for _, d in scored[:limit]]

    def failure_modes_for(self, equipment_type):
        rows = self.db.run(
            "MATCH (fm:FailureMode) WHERE fm.equipment_class=$t "
            "RETURN fm.code AS code, fm.description AS description, fm.mechanism AS mechanism, "
            "fm.iso14224_frequency AS frequency, fm.equipment_class AS equipment_class", t=equipment_type)
        modes = [dict(r) for r in rows]
        if not modes:  # taxonomy may only live in seed files
            return self._mem.failure_modes_for(equipment_type)
        order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
        modes.sort(key=lambda m: order.get(m["frequency"], 4))
        return modes

    def co_failure(self, tags):
        return self._mem.co_failure(tags)  # correlation stats are reference data

    def compliance_clauses(self):
        return self._mem.compliance_clauses()

    def telemetry(self, tag):
        return self._mem.telemetry(tag)

    def sample_documents(self):
        return self._mem.sample_documents()

    def personnel(self):
        rows = self.db.run("MATCH (d:Document) WHERE d.inspector IS NOT NULL OR d.technician IS NOT NULL "
                           "RETURN DISTINCT coalesce(d.inspector, d.technician) AS n")
        return sorted({r["n"] for r in rows if r["n"] and "Auto-generated" not in r["n"]})

    def add_document(self, doc, tags):
        self.db.run(
            "MERGE (d:Document {id:$id}) SET d.type=$type, d.title=$title, d.date=$date, d.content=$content, "
            "d.source='ingested' WITH d UNWIND $tags AS tg MATCH (e:Equipment {tag:tg}) MERGE (d)-[:DESCRIBES]->(e)",
            id=doc["id"], type=doc.get("type", "INGESTED"), title=doc.get("title", ""),
            date=doc.get("date", ""), content=doc.get("content", ""), tags=tags)
        return doc

    def overdue_inspections(self, as_of):
        rows = self.db.run(
            "MATCH (e:Equipment)<-[:DESCRIBES]-(d:Document) WHERE d.next_inspection < $d "
            "RETURN d.tag AS tag, d.id AS doc_id, d.next_inspection AS due, d.severity AS severity, "
            "d.title AS title ORDER BY d.next_inspection", d=as_of)
        return [dict(r) for r in rows] or self._mem.overdue_inspections(as_of)

    def capture_knowledge(self, entry):
        self.db.run(
            "MERGE (d:Document {id:$id}) SET d.type='TRIBAL_KNOWLEDGE', d.title=$title, d.date=$date, "
            "d.content=$content, d.author=$author, d.source='knowledge_cliff' "
            "WITH d MATCH (e:Equipment {tag:$tag}) MERGE (d)-[:DESCRIBES]->(e)",
            id=entry["id"], title=entry.get("title", ""), date=entry.get("date", ""),
            content=entry.get("content", ""), author=entry.get("author", ""),
            tag=entry.get("equipment_tag", ""))


# ─────────────────────────────────────────────────────────────────────────────
#  Backend selection
# ─────────────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_store():
    """Return a Neo4jStore if the database is reachable, else a MemStore.

    Set SANKET_FORCE_MEMSTORE=1 to always use the in-memory backend (demo/offline).
    """
    if os.getenv("SANKET_FORCE_MEMSTORE") == "1":
        return MemStore()
    try:
        from backend.graph.client import Neo4jClient
        client = Neo4jClient.get()
        client.driver.verify_connectivity()
        store = Neo4jStore(client)
        if store.health().get("equipment", 0) > 0:
            return store
        # DB reachable but empty → prefer seeded in-memory data for a working demo
        return MemStore()
    except Exception:
        return MemStore()


def reset_store():
    get_store.cache_clear()
