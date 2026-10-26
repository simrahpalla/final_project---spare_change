r"""Cost-cutting experiment (Phase 7): the SQL pre-filter vs. sending the matching agent every company.

    .venv\Scripts\python.exe scripts\prefilter_experiment.py

For each of the 18 labelled listings (data/answer_keys.json, expected_first_buyer set), the SAME matching agent ranks
buyers twice, on a scratch copy of the database:
  A. with pre-filter: only the companies code found compatible (search_buyers_for_listing, the app's normal path)
  B. no pre-filter:   all 49 other companies with their machines and open needs (list_buyer_profiles)
Measured per arm: input / cached / output tokens and cost of the matching call, top-1 accuracy against the answer key,
and how many of the agent's picks code would reject as ungrounded (record_matches: the buyer runs no compatible
machine and has no need the listing fills). Writes output/prefilter_experiment.json.
"""

import asyncio
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp(prefix="sx_pref_"))
DB = tmp / "w.db"
shutil.copyfile(REPO / "data" / "exchange.db", DB)
os.chmod(DB, stat.S_IWRITE | stat.S_IREAD)
os.environ.update(SURPLUS_DB=str(DB), SURPLUS_AUDIT=str(tmp / "audit.json"))
sys.path[:0] = [str(REPO / "backend")]

from agents import Exchange, RunState  # noqa: E402

KEYS = json.loads((REPO / "data" / "answer_keys.json").read_text(encoding="utf-8"))
LABELLED = [k for k in KEYS["listings"] if k["expected_first_buyer"] is not None and not k["is_bad_record"]]


def listing_block(found: dict) -> str:
    return "Listing:\n" + json.dumps({k: v for k, v in found["listing"].items() if k != "seller_text_untrusted"}, indent=1)


async def arm(ex: Exchange, listing_id: int, prefilter: bool, everyone: list[dict]) -> dict:
    found = await ex.call("search_buyers_for_listing", listing_id=listing_id)
    seller = found["listing"]["seller_id"]
    if prefilter:
        cands = found["candidates"]
        prompt = (listing_block(found) + f"\nCandidates ({found['candidate_count']} passed the pre-filter; top {len(cands)} shown):\n"
                  + json.dumps(cands, indent=1))
    else:
        cands = [c for c in everyone if c["buyer_id"] != seller]
        prompt = (listing_block(found) + f"\nCandidates (all {len(cands)} companies on the exchange, NOT pre-filtered: decide "
                  "yourself which ones could use this part from their machines and open needs):\n" + json.dumps(cands, indent=1))
    state = RunState(kind="experiment", subject=f"listing:{listing_id}:{'A' if prefilter else 'B'}")
    result, _ = await ex._run_agent(state, "matching_agent", ex.matcher, prompt)
    picks = [m.model_dump() for m in result.matches]
    saved = await ex.call("record_matches", direction="seller_to_buyer", run_id=state.run_id,
                          matches=[{**m, "listing_id": listing_id} for m in picks])
    t = state.totals()
    return {"top": [m["buyer_id"] for m in picks], "ungrounded": len(saved.get("rejected", [])),
            "candidates_sent": len(cands), "input_tokens": t["input_tokens"] + t["cached_tokens"] + t["cache_write_tokens"],
            "cached_tokens": t["cached_tokens"], "output_tokens": t["output_tokens"], "total_tokens": t["total_tokens"],
            "cost_usd": t["cost_usd"], "requests": t["requests"]}


async def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = []
    async with Exchange() as ex:
        everyone = (await ex.call("list_buyer_profiles"))["companies"]
        sem = asyncio.Semaphore(4)

        async def one(k):
            async with sem:
                a = await arm(ex, k["listing_id"], True, everyone)
                b = await arm(ex, k["listing_id"], False, everyone)
                exp = k["expected_first_buyer"]
                row = {"listing_id": k["listing_id"], "expected_first_buyer": exp,
                       "with_prefilter": a | {"top1_correct": bool(a["top"]) and a["top"][0] == exp},
                       "no_prefilter": b | {"top1_correct": bool(b["top"]) and b["top"][0] == exp}}
                print(f"listing {k['listing_id']:>2}: A {a['total_tokens']:>6} tok top {a['top'][:1]} | "
                      f"B {b['total_tokens']:>6} tok top {b['top'][:1]} (expected {exp}); B ungrounded {b['ungrounded']}", flush=True)
                return row
        rows = await asyncio.gather(*[one(k) for k in LABELLED])

    def summary(key):
        xs = [r[key] for r in rows]
        n = len(xs)
        return {"listings": n, "top1_correct": sum(x["top1_correct"] for x in xs), "top1_accuracy": round(sum(x["top1_correct"] for x in xs) / n, 3),
                "ungrounded_picks": sum(x["ungrounded"] for x in xs), "avg_candidates_sent": round(sum(x["candidates_sent"] for x in xs) / n, 1),
                "avg_input_tokens": round(sum(x["input_tokens"] for x in xs) / n), "avg_output_tokens": round(sum(x["output_tokens"] for x in xs) / n),
                "avg_total_tokens": round(sum(x["total_tokens"] for x in xs) / n), "avg_cost_usd": round(sum(x["cost_usd"] for x in xs) / n, 6),
                "total_cost_usd": round(sum(x["cost_usd"] for x in xs), 6)}
    a, b = summary("with_prefilter"), summary("no_prefilter")
    out = {"what": "Same matching agent, same 18 labelled listings: with the SQL pre-filter (A) vs. every company (B)",
           "with_prefilter": a, "no_prefilter": b,
           "tokens_saved_per_matching_call": b["avg_total_tokens"] - a["avg_total_tokens"],
           "token_reduction": round(1 - a["avg_total_tokens"] / b["avg_total_tokens"], 3) if b["avg_total_tokens"] else None,
           "cost_reduction": round(1 - a["avg_cost_usd"] / b["avg_cost_usd"], 3) if b["avg_cost_usd"] else None,
           "accuracy_change": round(a["top1_accuracy"] - b["top1_accuracy"], 3), "per_listing": rows}
    (REPO / "output" / "prefilter_experiment.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nA (pre-filter): {a['avg_total_tokens']} tokens, ${a['avg_cost_usd']:.6f}, top-1 {a['top1_correct']}/{a['listings']}, "
          f"ungrounded {a['ungrounded_picks']}")
    print(f"B (everyone):   {b['avg_total_tokens']} tokens, ${b['avg_cost_usd']:.6f}, top-1 {b['top1_correct']}/{b['listings']}, "
          f"ungrounded {b['ungrounded_picks']}")
    print("Saved output/prefilter_experiment.json")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
