"""
RCA LangGraph agent — Groq LLM + 11 knowledge-graph tools.

Used when a Groq API key is configured.  When no key is present the API falls
back to the deterministic engine (rca_engine.py) so the product still works.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools.traversal import traverse_upstream, traverse_downstream
from backend.agent.tools.documents import (
    get_failure_history, get_inspection_logs, get_work_orders, semantic_search_near,
)
from backend.agent.tools.patterns import get_failure_modes, get_co_failure_patterns
from backend.agent.tools.analytics import structural_query, predict_failure_mode, check_compliance
from backend.config import GROQ_MODELS

TOOLS = [
    traverse_upstream, traverse_downstream,
    get_failure_history, get_inspection_logs, get_work_orders,
    get_failure_modes, get_co_failure_patterns, semantic_search_near,
    structural_query, predict_failure_mode, check_compliance,
]

_agent = None


def llm_available() -> bool:
    key = os.getenv("GROQ_API_KEY", "")
    return bool(key) and not key.startswith("gsk_PLACEHOLDER")


def get_agent():
    """Build (once) a ReAct agent, trying each configured Groq model in turn."""
    global _agent
    if _agent is not None:
        return _agent

    from langchain_groq import ChatGroq
    from langgraph.prebuilt import create_react_agent

    last_err = None
    for model in GROQ_MODELS:
        try:
            llm = ChatGroq(model=model, temperature=0, api_key=os.getenv("GROQ_API_KEY"))
            _agent = create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)
            _agent._sanket_model = model  # noqa: for /health reporting
            return _agent
        except Exception as exc:
            last_err = exc
            continue
    raise RuntimeError(f"Could not initialise any Groq model {GROQ_MODELS}: {last_err}")


if __name__ == "__main__":
    from langchain_core.messages import HumanMessage
    from dotenv import load_dotenv
    from backend.config import DEMO_QUERY

    load_dotenv()
    result = get_agent().invoke({"messages": [HumanMessage(content=DEMO_QUERY)]})
    print(result["messages"][-1].content)
