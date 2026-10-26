r"""Measure the buy-request flow's real cost (Phase 7): every seeded request's original text, posted again as a NEW
request by its own buyer (need agent -> compliance guard -> pre-filter -> matching agent -> alerts).

    .venv\Scripts\python.exe scripts\measure_need_posts.py

Runs in-process on a scratch copy of the database (the logged buy-request runs from earlier tests were only 3).
Writes output/need_post_runs.json with each run's real token totals; scripts/cost_report.py averages them.
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
tmp = Path(tempfile.mkdtemp(prefix="sx_needs_"))
DB = tmp / "w.db"
shutil.copyfile(REPO / "data" / "exchange.db", DB)
os.chmod(DB, stat.S_IWRITE | stat.S_IREAD)
os.environ.update(SURPLUS_DB=str(DB), SURPLUS_AUDIT=str(tmp / "audit.json"))
sys.path[:0] = [str(REPO / "backend")]

from agents import Exchange  # noqa: E402


async def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(REPO / "data" / "exchange.db")
    needs = con.execute("SELECT id, buyer_id, raw_text FROM needs ORDER BY id").fetchall()
    con.close()
    rows = []
    async with Exchange() as ex:
        sem = asyncio.Semaphore(4)

        async def one(nid, buyer, text):
            async with sem:
                r = await ex.run_need_flow(text=text, buyer_id=buyer)
                t = r["totals"]
                agents = [a["agent"] for a in r.get("agent_calls", [])]
                return {"seeded_need": nid, "buyer_id": buyer, "outcome": r["outcome"], "requests": t["requests"],
                        "input_tokens": t["input_tokens"], "cached_tokens": t["cached_tokens"],
                        "cache_write_tokens": t["cache_write_tokens"], "output_tokens": t["output_tokens"],
                        "total_tokens": t["total_tokens"], "cost_usd": t["cost_usd"],
                        "matching_called": "matching_agent" in agents}
        rows = await asyncio.gather(*[one(*n) for n in needs])
    for r in rows:
        print(f"need {r['seeded_need']:>2}: {r['outcome'][:40]:<40} {r['requests']} calls {r['total_tokens']:>6} tok ${r['cost_usd']:.6f}")
    total = sum(r["cost_usd"] for r in rows)
    (REPO / "output" / "need_post_runs.json").write_text(json.dumps(
        {"what": "Each seeded request's text posted again as a new buy request by its buyer (full need flow)",
         "runs": rows, "total_cost_usd": round(total, 6)}, indent=2), encoding="utf-8")
    print(f"\n{len(rows)} runs, ${total:.4f} total. Saved output/need_post_runs.json")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
