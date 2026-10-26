r"""Cost check by hand (evidence consistency): recompute costs from token_usage with the gpt-6-luna price table typed in
here (not read from the app), and compare with what the app shows and reports.

    .venv\Scripts\python.exe scripts\verify_costs.py

1. One fresh seller run and one negotiation, through the real backend on a scratch database: Hartwell posts the
   Siemens example, confirms the suggested floor, the negotiation with Riverbend starts by itself. For each run, every
   token_usage row is re-priced by hand and summed; that must equal (a) the logged cost, (b) the cost meter's source
   (/api/runs/{id} totals for the seller run; the negotiation view's cost for the negotiation).
2. Every run that output/tokenomics.json averages: its logged cost must equal its token counts re-priced by hand, and
   tokenomics.json's averages must equal the mean of those runs.
Writes output/cost_check.json and output/cost_check.md.
"""

import asyncio
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from test_negotiation import Backend  # noqa: E402

PRICE = {"input": 0.10, "cached": 0.01, "cache_write": 0.125, "output": 0.50}  # USD per 1M tokens (course price table)
TOL = 1e-6
SIEMENS = ("clearing out old S7-300 stuff after line 2 retrofit to 1500s. have 3x CPU 315-2DP (6ES7 315-2AG10), pulled "
           "wrking last month, fw 2.6, few scuffs on housing. no MMCs. ~$1425 ea. pickup dayton or we ship")


def by_hand(inp: int, cached: int, write: int, out: int) -> float:
    return (inp * PRICE["input"] + cached * PRICE["cached"] + write * PRICE["cache_write"] + out * PRICE["output"]) / 1e6


def show(inp, cached, write, out) -> str:
    return (f"{inp:,} × $0.10 + {cached:,} × $0.01 + {write:,} × $0.125 + {out:,} × $0.50 (per 1M) = "
            f"${by_hand(inp, cached, write, out):.8f}")


async def live_runs() -> dict:
    out = {}
    async with Backend(8768) as b:
        r = await b.flow("/api/seller-flow/start", {"text": SIEMENS, "seller_id": 1})
        seller_run = r["run_id"]
        floor = next(s for s in r["steps"] if s["step"] == "floor")
        _, conf = await b.call("POST", "/api/limits", {"company_id": 1, "value": floor["value"], "listing_id": r["listing_id"]}, viewer=1)
        nid = conf["started"][0]["negotiation_id"]
        v = await b.wait(nid, 1)
        _, meter = await b.call("GET", f"/api/runs/{seller_run}?company_id=1", viewer=1)
        for label, run_id, shown in (("seller run (Hartwell posts the Siemens CPUs)", seller_run, meter["totals"]["cost_usd"]),
                                     (f"negotiation #{nid} (Hartwell vs Riverbend, {v['status']} in {v['rounds_used']} rounds)",
                                      v["run_id"], v["cost"]["cost_usd"])):
            rows = b.q("SELECT agent, requests, input_tokens, cached_tokens, cache_write_tokens, output_tokens, cost_usd "
                       "FROM token_usage WHERE run_id=? ORDER BY id", run_id)
            hand = sum(by_hand(x["input_tokens"], x["cached_tokens"], x["cache_write_tokens"], x["output_tokens"]) for x in rows)
            logged = sum(x["cost_usd"] for x in rows)
            out[label] = {"run_id": run_id, "token_usage_rows": [
                x | {"by_hand": show(x["input_tokens"], x["cached_tokens"], x["cache_write_tokens"], x["output_tokens"])} for x in rows],
                "by_hand_usd": round(hand, 8), "logged_usd": round(logged, 8), "shown_in_ui_usd": shown,
                "match": abs(hand - logged) < TOL and abs(hand - shown) < TOL}
    return out


def tokenomics_sources() -> dict:
    p3 = json.loads((REPO / "output" / "phase3_stress.json").read_text(encoding="utf-8"))["raw"]
    tok = json.loads((REPO / "output" / "tokenomics.json").read_text(encoding="utf-8"))
    needs = json.loads((REPO / "output" / "need_post_runs.json").read_text(encoding="utf-8"))["runs"]
    groups = {
        "seller_flow": [v["result"]["totals"] for k, v in p3.items() if k.startswith("coverage:") and str(v["result"]["outcome"]).startswith("listed")],
        "buy_request": needs,
        "negotiation (Phase 3 part, full token split)": [v["result"]["totals"] for k, v in p3.items() if k.startswith("neg:")],
    }
    out = {}
    for name, runs in groups.items():
        bad = [r for r in runs if abs(by_hand(r["input_tokens"], r["cached_tokens"], r["cache_write_tokens"], r["output_tokens"]) - r["cost_usd"]) > TOL]
        out[name] = {"runs": len(runs), "runs_whose_logged_cost_differs_from_hand": len(bad),
                     "mean_cost_usd": round(statistics.mean(r["cost_usd"] for r in runs), 6)}
    for key, name in (("seller_flow", "seller_flow"), ("buy_request", "buy_request")):
        out[name]["tokenomics_json_avg_usd"] = tok["per_run"][key]["avg_cost_usd"]
        out[name]["average_matches"] = abs(out[name]["mean_cost_usd"] - tok["per_run"][key]["avg_cost_usd"]) < TOL
    return out


async def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    live = await live_runs()
    src = tokenomics_sources()
    ok = all(x["match"] for x in live.values()) and all(x["runs_whose_logged_cost_differs_from_hand"] == 0 for x in src.values()) \
        and all(x.get("average_matches", True) for x in src.values())
    (REPO / "output" / "cost_check.json").write_text(json.dumps({"prices_per_1m_usd": PRICE, "live_runs": live,
                                                                 "tokenomics_sources": src, "all_match": ok}, indent=2), encoding="utf-8")
    md = ["# Cost check by hand", "", "Prices typed into `scripts/verify_costs.py` (not read from the app): input $0.10, cached input $0.01, "
          "cache write $0.125, output $0.50 per 1M tokens. `input` below is the uncached part.", ""]
    for label, x in live.items():
        md += [f"## {label}", "", "| Agent | Calls | Input | Cached | Cache write | Output | Logged cost | By hand |", "|---|---|---|---|---|---|---|---|"]
        md += [f"| {r['agent']} | {r['requests']} | {r['input_tokens']:,} | {r['cached_tokens']:,} | {r['cache_write_tokens']:,} | {r['output_tokens']:,} | "
               f"${r['cost_usd']:.8f} | {r['by_hand']} |" for r in x["token_usage_rows"]]
        md += ["", f"**By hand ${x['by_hand_usd']:.8f} · logged ${x['logged_usd']:.8f} · shown in the app ${x['shown_in_ui_usd']} → "
               f"{'match' if x['match'] else 'MISMATCH'}**", ""]
    md += ["## Every run behind tokenomics.json", "", "| Group | Runs | Logged ≠ hand | Mean cost | tokenomics.json avg | Same |", "|---|---|---|---|---|---|"]
    md += [f"| {k} | {v['runs']} | {v['runs_whose_logged_cost_differs_from_hand']} | ${v['mean_cost_usd']:.6f} | "
           f"{('$%.6f' % v['tokenomics_json_avg_usd']) if 'tokenomics_json_avg_usd' in v else '—'} | {('yes' if v.get('average_matches') else 'NO') if 'average_matches' in v else '—'} |"
           for k, v in src.items()]
    md += ["", f"**All checks match: {ok}**"]
    (REPO / "output" / "cost_check.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
