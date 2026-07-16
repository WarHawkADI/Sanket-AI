"""RCA endpoints — deterministic engine by default, LLM agent when a Groq key is set."""
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.agent.rca_engine import deterministic_rca
from backend.agent.rca_agent import llm_available
from backend.agent import citations
from backend.graph.store import get_store
from backend.api.models import RCAQuery, RCAResponse

router = APIRouter()


@router.post("/query", response_model=RCAResponse)
async def rca_query(request: RCAQuery):
    """Non-streaming RCA. Uses the LLM agent if available, else the deterministic engine."""
    try:
        if llm_available():
            result = await _run_llm(request.query)
        else:
            result = await asyncio.to_thread(deterministic_rca, request.query)
        return RCAResponse(
            query=request.query, response=result["answer"], mode=result["mode"],
            focus_tag=result.get("focus_tag"), causal=result.get("causal"),
            confidence=result.get("confidence"),
            confidence_breakdown=result.get("confidence_breakdown", []),
            citations=result.get("citations", {}), metrics=result.get("metrics", {}),
            trace=result.get("trace", []),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stream")
async def rca_stream(query: str):
    """SSE streaming RCA. Emits tool_call / tool_result / token / meta / error, ends with [DONE]."""
    if llm_available():
        return StreamingResponse(_stream_llm(query), media_type="text/event-stream")
    return StreamingResponse(_stream_deterministic(query), media_type="text/event-stream")


def _sse(obj) -> str:
    return f"data: {json.dumps(obj)}\n\n"


async def _stream_deterministic(query: str) -> AsyncGenerator[str, None]:
    """Replay the deterministic investigation as a live stream (trace → answer → meta)."""
    try:
        result = await asyncio.to_thread(deterministic_rca, query)
        # replay tool trace so the graph flashes + trace panel fills, just like the agent
        for step in result["trace"]:
            yield _sse({"type": "tool_call", "tool": step["tool"], "input": json.dumps(step["input"])})
            await asyncio.sleep(0.18)
            yield _sse({"type": "tool_result", "tool": step["tool"]})
        # stream the answer in word chunks for the typing effect
        answer = result["answer"]
        buf = ""
        for i, ch in enumerate(answer):
            buf += ch
            if ch == " " or i == len(answer) - 1:
                yield _sse({"type": "token", "content": buf})
                buf = ""
                if i % 6 == 0:
                    await asyncio.sleep(0.006)
        yield _sse({"type": "meta", "mode": result["mode"], "confidence": result.get("confidence"),
                    "confidence_breakdown": result.get("confidence_breakdown", []),
                    "metrics": result.get("metrics", {}), "citations": result.get("citations", {}),
                    "focus_tag": result.get("focus_tag"), "causal": result.get("causal")})
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})
    finally:
        yield "data: [DONE]\n\n"


async def _stream_llm(query: str) -> AsyncGenerator[str, None]:
    from langchain_core.messages import HumanMessage
    from backend.agent.rca_agent import get_agent
    answer_buf = []
    trace = []
    try:
        agent = get_agent()
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=query)]}, version="v2",
            config={"recursion_limit": 25},
        ):
            evt = event["event"]
            if evt == "on_chat_model_stream":
                token = event["data"]["chunk"].content
                if token:
                    answer_buf.append(token)
                    yield _sse({"type": "token", "content": token})
            elif evt == "on_tool_start":
                name = event.get("name", "")
                inp = str(event["data"].get("input", {}))[:300]
                trace.append(name)
                yield _sse({"type": "tool_call", "tool": name, "input": inp})
            elif evt == "on_tool_end":
                yield _sse({"type": "tool_result", "tool": event.get("name", "")})
        # post-process: verify citations + emit metrics
        answer = "".join(answer_buf)
        store = get_store()
        verified = citations.verify(answer, store.document_ids())
        yield _sse({"type": "meta", "mode": "llm-agent",
                    "citations": verified,
                    "metrics": {"tool_calls": len(trace), "citations": len(verified["valid"]),
                                "citation_faithfulness": verified["faithfulness"],
                                "manual_baseline_minutes": 240}})
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})
    finally:
        yield "data: [DONE]\n\n"


async def _run_llm(query: str) -> dict:
    from langchain_core.messages import HumanMessage
    from backend.agent.rca_agent import get_agent
    agent = get_agent()
    result = await agent.ainvoke({"messages": [HumanMessage(content=query)]})
    answer = result["messages"][-1].content
    store = get_store()
    verified = citations.verify(answer, store.document_ids())
    answer = citations.annotate(answer, store.document_ids())
    return {"answer": answer, "mode": "llm-agent", "focus_tag": None,
            "confidence": None, "confidence_breakdown": [], "citations": verified,
            "metrics": {"citations": len(verified["valid"]),
                        "citation_faithfulness": verified["faithfulness"],
                        "manual_baseline_minutes": 240}, "trace": []}
