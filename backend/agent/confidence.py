"""
Evidence-based confidence scoring.

The confidence attached to an RCA hypothesis is **computed from evidence**, not
invented by the language model.  This is the single most important trust feature
of the system: when a judge asks "how did you get 87%?", there is a real answer.

Score = f(corroborating documents, recency, finding severity, ISO-14224
co-failure correlation, confirmed physical path).  Every component is returned
in the breakdown so the UI can show exactly why.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


def _days_since(d: str, today: date) -> int:
    for fmt in ("%Y-%m-%d", "%Y"):
        try:
            return (today - datetime.strptime(d[:10], fmt).date()).days
        except (ValueError, TypeError):
            continue
    return 10_000  # unknown/very old


@dataclass
class Evidence:
    """Structured evidence supporting one hypothesis."""
    doc_ids: list[str] = field(default_factory=list)
    severities: list[str] = field(default_factory=list)   # e.g. ["HIGH", "MEDIUM"]
    latest_date: str = ""                                   # ISO date of most recent supporting doc
    correlation: float = 0.0                                # ISO-14224 co-failure correlation (0–1)
    path_confirmed: bool = False                            # upstream physical path found in the P&ID


# component weights (documented so the formula is auditable)
W_BASE = 25
W_PER_DOC = 9          # up to 4 docs → +36
W_SEVERITY_HIGH = 12
W_SEVERITY_MEDIUM = 6
W_RECENT_90 = 8
W_RECENT_365 = 4
W_CORRELATION = 18     # correlation(0–1) × 18
W_PATH = 8
CAP = 97               # never claim certainty


def score(ev: Evidence, today: date | None = None) -> dict:
    """Return {'confidence': int, 'level': str, 'breakdown': [...]}."""
    if today is None:
        from backend.config import now
        today = now()
    parts = []
    total = W_BASE
    parts.append(("base rate", W_BASE))

    n_docs = min(len(set(ev.doc_ids)), 4)
    if n_docs:
        pts = n_docs * W_PER_DOC
        total += pts
        parts.append((f"{n_docs} corroborating document(s)", pts))

    sev = {s.upper() for s in ev.severities}
    if "HIGH" in sev:
        total += W_SEVERITY_HIGH
        parts.append(("HIGH-severity finding", W_SEVERITY_HIGH))
    elif "MEDIUM" in sev:
        total += W_SEVERITY_MEDIUM
        parts.append(("MEDIUM-severity finding", W_SEVERITY_MEDIUM))

    if ev.latest_date:
        age = _days_since(ev.latest_date, today)
        if age <= 90:
            total += W_RECENT_90
            parts.append(("evidence < 90 days old", W_RECENT_90))
        elif age <= 365:
            total += W_RECENT_365
            parts.append(("evidence < 1 year old", W_RECENT_365))

    if ev.correlation:
        pts = round(ev.correlation * W_CORRELATION)
        total += pts
        parts.append((f"ISO-14224 co-failure corr {ev.correlation:.2f}", pts))

    if ev.path_confirmed:
        total += W_PATH
        parts.append(("confirmed upstream physical path", W_PATH))

    conf = max(5, min(total, CAP))
    level = "HIGH" if conf >= 75 else "MEDIUM" if conf >= 55 else "LOW"
    return {"confidence": conf, "level": level,
            "breakdown": [{"factor": f, "points": p} for f, p in parts]}


def explain(result: dict) -> str:
    """One-line human explanation of a score, e.g. for tooltips/logs."""
    bits = ", ".join(f"{b['factor']} (+{b['points']})" for b in result["breakdown"])
    return f"{result['confidence']}% [{result['level']}] = {bits}"
