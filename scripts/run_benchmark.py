"""
Domain-expert benchmark runner.

Scores the deterministic RCA engine on a gold question set — focus-asset
detection, expected root-cause mention, citation presence, confidence floor —
and reports accuracy + mean citation faithfulness + mean answer time.  This is
the "query answer quality on a domain-expert benchmark" evaluation the brief
asks for, turned into a number you can put on a slide.

Run:  SANKET_FORCE_MEMSTORE=1 python scripts/run_benchmark.py
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SANKET_FORCE_MEMSTORE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent.rca_engine import deterministic_rca  # noqa: E402

BENCH = Path("backend/data/benchmark.json")


def run():
    data = json.loads(BENCH.read_text(encoding="utf-8"))
    qs = data["questions"]
    passed = 0
    faith, times = [], []
    rows = []

    for q in qs:
        r = deterministic_rca(q["query"])
        ans = r["answer"].lower()
        checks = []
        # focus detection
        checks.append(("focus", r.get("focus_tag") == q["expect_focus"]))
        # expected mentions
        for m in q.get("expect_mentions", []):
            checks.append((f"mentions:{m}", m.lower() in ans))
        # citation presence
        if q.get("expect_citation"):
            checks.append((f"cite:{q['expect_citation']}",
                           q["expect_citation"] in r["citations"]["valid"]))
        # confidence floor
        if q.get("min_confidence") is not None and r.get("confidence") is not None:
            checks.append(("confidence", r["confidence"] >= q["min_confidence"]))
        # no hallucinated citations, ever
        checks.append(("no_hallucination", len(r["citations"]["hallucinated"]) == 0))

        ok = all(v for _, v in checks)
        passed += ok
        faith.append(r["citations"]["faithfulness"])
        times.append(r["metrics"]["answer_seconds"])
        fails = [name for name, v in checks if not v]
        rows.append((q["id"], ok, r.get("focus_tag"), r.get("confidence"), fails))

    print(f"\n{'ID':<5}{'PASS':<6}{'FOCUS':<9}{'CONF':<6}FAILED CHECKS")
    print("-" * 60)
    for qid, ok, focus, conf, fails in rows:
        print(f"{qid:<5}{'✓' if ok else '✗':<6}{str(focus):<9}{str(conf):<6}{', '.join(fails)}")

    n = len(qs)
    print("-" * 60)
    print(f"Accuracy:            {passed}/{n} = {passed/n:.0%}")
    print(f"Mean citation faith: {sum(faith)/n:.1%}")
    print(f"Mean answer time:    {sum(times)/n*1000:.1f} ms  (manual baseline ~4 hours)")
    return passed == n


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
