"""
Citation extraction & verification.

Every document ID an answer cites must exist in the knowledge graph.  Anything
the model invents is flagged so it can be stripped or annotated before it ever
reaches the user.  "Source citations" you cannot trace back are worse than none.
"""
from __future__ import annotations

import re

# Doc-ID shapes we mint: INS-2025-0847, WO-2025-1034, ERR-AZ-..., TRIBAL-...,
# plus CSB chunk ids like report-c001.  Match inside optional [ ] or ` `.
CITATION_RE = re.compile(
    r"\b((?:INS|WO|MNT|ALM|RPT|ERR|TRIBAL|DOC|CSB)[-A-Za-z0-9]*-[A-Za-z0-9]+)\b"
)


def extract(text: str) -> list[str]:
    """Return all citation-shaped tokens in order, de-duplicated."""
    seen, out = set(), []
    for m in CITATION_RE.findall(text or ""):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def verify(text: str, valid_ids: set[str]) -> dict:
    """Split cited IDs into valid / hallucinated against the known ID set."""
    cited = extract(text)
    valid = [c for c in cited if c in valid_ids]
    invalid = [c for c in cited if c not in valid_ids]
    return {
        "cited": cited,
        "valid": valid,
        "hallucinated": invalid,
        "faithfulness": round(len(valid) / len(cited), 3) if cited else 1.0,
    }


def annotate(text: str, valid_ids: set[str]) -> str:
    """Mark any hallucinated citation inline so it can never masquerade as real.

    Valid IDs are left untouched (the frontend renders them as clickable chips);
    unverifiable ones get a visible ⚠ so a reviewer sees the model over-reached.
    """
    def repl(m):
        cid = m.group(1)
        return cid if cid in valid_ids else f"{cid} [unverified]"
    return CITATION_RE.sub(repl, text or "")
