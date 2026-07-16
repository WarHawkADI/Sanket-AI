"""
Ingests CSB (U.S. Chemical Safety Board) incident report PDFs into Neo4j.

For each PDF:
  1. PyMuPDF extracts text page by page
  2. Pages are grouped into ~4-page chunks
  3. Groq (llama-3.1-8b-instant) extracts structured entities via structured output
  4. BGE-M3 embeds each chunk for semantic search
  5. Document + FailureMode + Equipment nodes created in Neo4j

Run: python -m backend.ingestion.process_csb
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional

import fitz  # pymupdf
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.graph.client import Neo4jClient

PDF_DIR = Path("data/raw/csb_reports")
CACHE_DIR = Path("data/cache/csb")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

embedder = SentenceTransformer("BAAI/bge-m3")

_llm = None


def _get_extractor():
    global _llm
    if _llm is None:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0,
            api_key=os.getenv("GROQ_API_KEY"),
        )
        _llm = llm.with_structured_output(IncidentExtraction)
    return _llm


class IncidentExtraction(BaseModel):
    title: str = Field(description="Incident title or short description")
    date: str = Field(default="", description="Incident date (YYYY-MM-DD or year)")
    industry: str = Field(default="", description="Industry sector (e.g. refining, chemical)")
    equipment_involved: list[str] = Field(default_factory=list, description="Equipment items mentioned")
    failure_modes: list[str] = Field(default_factory=list, description="How each piece of equipment failed")
    root_causes: list[str] = Field(default_factory=list, description="Underlying root causes identified")
    consequences: list[str] = Field(default_factory=list, description="Fire, explosion, fatality, injury, release")
    recommendations: list[str] = Field(default_factory=list, description="CSB safety recommendations issued")


def extract_entities(text: str, doc_id: str) -> dict:
    cache_path = CACHE_DIR / f"{doc_id}.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    extractor = _get_extractor()
    result: IncidentExtraction = extractor.invoke(
        "Extract incident information from this industrial accident report section. "
        "Focus on equipment failures, root causes, and safety recommendations.\n\n"
        + text[:4000]
    )
    result_dict = result.model_dump()

    with open(cache_path, "w") as f:
        json.dump(result_dict, f, indent=2)
    return result_dict


def chunk_pdf(pdf_path: Path, pages_per_chunk: int = 4) -> list[tuple[str, str]]:
    doc = fitz.open(str(pdf_path))
    chunks, group_num, group_text = [], 1, ""
    for i, page in enumerate(doc):
        group_text += page.get_text()
        if (i + 1) % pages_per_chunk == 0 or i == len(doc) - 1:
            if group_text.strip():
                chunks.append((f"{pdf_path.stem}-c{group_num:03d}", group_text.strip()))
            group_num += 1
            group_text = ""
    doc.close()
    return chunks


def ingest_pdf(pdf_path: Path, db: Neo4jClient):
    chunks = chunk_pdf(pdf_path)
    print(f"  {pdf_path.name}: {len(chunks)} chunks")

    for doc_id, text in tqdm(chunks, desc=f"  {pdf_path.stem}", leave=False):
        entities = extract_entities(text, doc_id)
        if not entities or (not entities.get("failure_modes") and not entities.get("root_causes")):
            continue

        embedding = embedder.encode(text[:2000], normalize_embeddings=True).tolist()
        full_content = text[:3000]

        # Document node
        db.run(
            """
            MERGE (d:Document {id: $id})
            SET d.type       = 'INCIDENT_REPORT',
                d.title      = $title,
                d.date       = $date,
                d.industry   = $industry,
                d.content    = $content,
                d.embedding  = $embedding,
                d.source     = 'csb'
            """,
            id=doc_id,
            title=entities.get("title", ""),
            date=entities.get("date", ""),
            industry=entities.get("industry", ""),
            content=full_content,
            embedding=embedding,
        )

        # FailureMode nodes
        for fm in entities.get("failure_modes", []):
            fm_code = fm.lower().replace(" ", "_")[:50]
            db.run(
                """
                MERGE (fm:FailureMode {code: $code})
                SET fm.description = $desc, fm.source = 'csb'
                WITH fm
                MATCH (d:Document {id: $doc_id})
                MERGE (d)-[:RECORDS_FAILURE]->(fm)
                """,
                code=fm_code,
                desc=fm,
                doc_id=doc_id,
            )

        # Root cause nodes (stored as FailureMode with cause_ prefix)
        for rc in entities.get("root_causes", []):
            rc_code = "cause_" + rc.lower().replace(" ", "_")[:44]
            db.run(
                """
                MERGE (fm:FailureMode {code: $code})
                SET fm.description = $desc,
                    fm.is_root_cause = true,
                    fm.source = 'csb'
                WITH fm
                MATCH (d:Document {id: $doc_id})
                MERGE (d)-[:IDENTIFIES_ROOT_CAUSE]->(fm)
                """,
                code=rc_code,
                desc=rc,
                doc_id=doc_id,
            )

        # Equipment nodes mentioned
        for eq in entities.get("equipment_involved", []):
            eq_tag = eq.upper().replace(" ", "-")[:30]
            db.run(
                """
                MERGE (e:Equipment {tag: $tag})
                ON CREATE SET e.name = $name, e.source = 'csb'
                WITH e
                MATCH (d:Document {id: $doc_id})
                MERGE (d)-[:DESCRIBES]->(e)
                """,
                tag=eq_tag,
                name=eq,
                doc_id=doc_id,
            )


if __name__ == "__main__":
    pdfs = list(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {PDF_DIR}. Run the CSB download commands first.")
        sys.exit(1)

    db = Neo4jClient.get()
    print(f"Found {len(pdfs)} CSB PDFs. Starting ingestion (cached results skip API calls)...")
    for pdf in pdfs:
        ingest_pdf(pdf, db)

    print("\nCSB ingestion complete.")
