r"""Reverse-direction matching eval (Phase 5): a NEED is matched to listings by the same matching agent and the
same pre-filter code that sellers use.

    .venv\Scripts\python.exe scripts\eval_reverse.py

On a scratch copy of the database it runs the buyer flow for:
  - every seeded need (re-match an existing need: pre-filter -> matching agent -> fact check -> alerts), and
  - the demo buyer posts in data/answer_keys.json -> two_sided.buyer_posts (new text: extraction -> guard -> ...).
Scores against the answer keys: is the expected listing ranked first? For needs that no listing can fill, the
pre-filter must return 0 candidates and the run must make NO matching-agent call. Also checks that a buyer's
max price never appears in the saved need text, the alerts or the Marketplace board.
Writes output/eval_reverse.json.
"""

import asyncio
import json
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp(prefix="sx_rev_"))
DB = tmp / "w.db"
shutil.copyfile(REPO / "data" / "exchange.db", DB)
os.chmod(DB, stat.S_IWRITE | stat.S_IREAD)
os.environ.update(SURPLUS_DB=str(DB), SURPLUS_AUDIT=str(tmp / "audit.json"))
sys.path.insert(0, str(REPO / "backend"))
from agents import Exchange  # noqa: E402

KEYS = json.loads((REPO / "data" / "answer_keys.json").read_text(encoding="utf-8"))
CONCURRENCY = 4


def summarize(r: dict) -> dict:
    steps = {s["step"]: s for s in r["steps"]}
    m = steps.get("matching", {})
    ranked = m.get("ranked") or []
    calls = [a["agent"] for a in r.get("agent_calls", [])]
    return {"outcome": r["outcome"], "run_id": r["run_id"], "need_id": r.get("need_id"),
            "part": (steps.get("need_agent", {}).get("draft") or {}).get("part_number"),
            "candidates": steps.get("prefilter", {}).get("candidates"), "method": m.get("method"),
            "ranked": [x["listing_id"] for x in ranked], "scores": [x["score"] for x in ranked],
            "matching_calls": calls.count("matching_agent"), "alerts_sent": steps.get("alerts", {}).get("sent", 0),
            "alert_companies": steps.get("alerts", {}).get("companies", []),
            "requests": r["totals"]["requests"], "cost_usd": r["totals"]["cost_usd"]}


async def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sem = asyncio.Semaphore(CONCURRENCY)
    rows = []
    async with Exchange() as ex:
        async def seeded(k):
            async with sem:
                s = summarize(await ex.run_need_flow(need_id=k["need_id"]))
                if k["expect_no_candidates"]:
                    ok = s["candidates"] == 0 and s["matching_calls"] == 0
                else:
                    ok = bool(s["ranked"]) and s["ranked"][0] == k["expected_first_listing"]
                return {"case": f"need {k['need_id']}", "expected_first_listing": k["expected_first_listing"],
                        "expect_no_candidates": k["expect_no_candidates"], "pass": ok, **s}

        async def posted(p):
            async with sem:
                s = summarize(await ex.run_need_flow(text=p["text"], buyer_id=p["buyer_id"], max_price=p["max_price"]))
                if p["expect_no_candidates"]:
                    ok = s["candidates"] == 0 and s["matching_calls"] == 0
                else:
                    ok = bool(s["ranked"]) and s["ranked"][0] == p["expected_first_listing"]
                ok = ok and s["part"] == p["expected_part"] and sorted(s["alert_companies"]) == sorted(p["expected_alerts_to"])
                return {"case": p["name"], "expected_first_listing": p["expected_first_listing"],
                        "expect_no_candidates": p["expect_no_candidates"], "expected_part": p["expected_part"],
                        "expected_alerts_to": p["expected_alerts_to"], "max_price": p["max_price"], "pass": ok, **s}

        rows = await asyncio.gather(*[seeded(k) for k in KEYS["needs"]],
                                    *[posted(p) for p in KEYS["two_sided"]["buyer_posts"]])

    # Privacy: no buyer's max price in public text (need text, alerts, board)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    leaks = []
    sys.path.insert(0, str(REPO / "mcp_server"))
    os.environ["SURPLUS_ROLE"] = "system"
    import server  # noqa: E402  (same code the app runs, on the scratch copy)
    board = json.dumps(server.get_marketplace_board())
    for r in rows:
        if r.get("max_price") and r.get("need_id"):
            mp = r["max_price"]
            need_text = con.execute("SELECT raw_text FROM needs WHERE id=?", (r["need_id"],)).fetchone()[0]
            alerts = " ".join(x[0] for x in con.execute("SELECT message FROM notifications WHERE need_id=?", (r["need_id"],)))
            for where, text in (("need text", need_text), ("alerts", alerts), ("board", board)):
                if f"${mp}" in text or f"{mp}.0" in text or f"${mp:,.0f}" in text:
                    leaks.append(f"{r['case']}: max ${mp} appears in {where}")
    con.close()

    passed = sum(r["pass"] for r in rows)
    total_cost = round(sum(r["cost_usd"] for r in rows), 6)
    skipped = [r for r in rows if r["expect_no_candidates"]]
    for r in rows:
        print(f"[{'PASS' if r['pass'] else 'FAIL'}] {r['case']:<24} candidates {r['candidates']!s:>2} · ranked {r['ranked']} "
              f"(expected {r['expected_first_listing']}) · {r['method'] or 'no model call'} · {r['matching_calls']} matching call(s)"
              f" · {r['alerts_sent']} alert(s) · ${r['cost_usd']:.5f}")
    print(f"\n{passed}/{len(rows)} correct · {len(skipped)} need(s) with no candidates made "
          f"{sum(r['matching_calls'] for r in skipped)} matching calls · privacy leaks: {len(leaks)} · total ${total_cost:.4f}")
    for l in leaks:
        print("  LEAK", l)
    (REPO / "output" / "eval_reverse.json").write_text(json.dumps({
        "what": "Reverse matching (need -> listings) with the same matching agent and pre-filter code as the seller side",
        "passed": passed, "cases": len(rows), "privacy_leaks": leaks, "total_cost_usd": total_cost,
        "no_candidate_needs": len(skipped), "matching_calls_on_no_candidate_needs": sum(r["matching_calls"] for r in skipped),
        "results": rows}, indent=2), encoding="utf-8")
    print("Saved output/eval_reverse.json")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if passed == len(rows) and not leaks else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
