"""
Central configuration + the anchored 'plant present'.

The seeded scenario is authored around mid-2025 (the live P-101A vibration
readings are dated June 2025).  So the system's notion of "now" is anchored
there, keeping compliance windows, overdue tracking and evidence-recency scoring
coherent with the demo corpus.  Override with SANKET_NOW=YYYY-MM-DD (e.g. wire it
to real wall-clock time once live data is flowing).
"""
import os
from datetime import date, datetime


def now() -> date:
    val = os.getenv("SANKET_NOW")
    if val:
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date(2025, 6, 15)


# demo query used across UI + tests
DEMO_QUERY = "P-101A centrifugal pump showing 47Hz vibration spike. Find root cause."

# LLM model ids with fallbacks (Groq deprecates model names periodically)
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]
