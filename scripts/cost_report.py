r"""Tokenomics (Phase 7): cost per run, per user per month, and at 100 / 10,000 users, from REAL logged runs.

    .venv\Scripts\python.exe scripts\cost_report.py

No model calls. Every number comes from token counts the app logged during earlier test runs (each run's token_usage
totals, saved in these files):
  - seller flows:  output/phase3_stress.json (coverage runs: listing -> compliance -> matching -> pricing)
  - buy requests:  output/need_post_runs.json (21 real runs, scripts/measure_need_posts.py); re-matches: eval_reverse.json
  - negotiations:  output/phase3_stress.json (18) + output/negotiation_suite.json (Phase 6) + output/eval_demo_pair.json
  - cost-cutting:  output/prefilter_experiment.json (SQL pre-filter vs. every company)
Prices: gpt-6-luna via Portkey, $0.10 / 1M input, $0.01 / 1M cached input, $0.125 / 1M cache write, $0.50 / 1M output.
Writes output/tokenomics.json and output/tokenomics.md.
"""

import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "output"
sys.path.insert(0, str(REPO / "backend"))
import config  # noqa: E402

# Illustrative usage of one active plant on the exchange (stated assumptions, not measured)
PER_USER_MONTH = {"seller_flows": 10, "buy_requests": 4, "negotiations": 6}
USER_SCALES = [1, 100, 10_000]


def load(name: str):
    p = OUT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def stats(rows: list[dict], label: str, source: str) -> dict:
    cost = [r["cost_usd"] for r in rows]
    tok = [r.get("total_tokens") for r in rows if r.get("total_tokens") is not None]
    out = {"what": label, "source": source, "runs": len(rows), "avg_cost_usd": round(statistics.mean(cost), 6),
           "median_cost_usd": round(statistics.median(cost), 6), "min_cost_usd": round(min(cost), 6), "max_cost_usd": round(max(cost), 6)}
    if tok:
        out["avg_tokens"] = round(statistics.mean(tok))
    split = [r for r in rows if r.get("input_tokens") is not None and r.get("cached_tokens") is not None]
    if split:
        inp = sum(r["input_tokens"] + r["cached_tokens"] + r.get("cache_write_tokens", 0) for r in split)
        out["avg_input_tokens"] = round(inp / len(split))
        out["avg_output_tokens"] = round(sum(r["output_tokens"] for r in split) / len(split))
        out["cached_share_of_input"] = round(sum(r["cached_tokens"] for r in split) / inp, 3) if inp else 0
    if any("requests" in r for r in rows):
        out["avg_model_requests"] = round(statistics.mean(r.get("requests", 0) for r in rows), 1)
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p3 = load("phase3_stress.json")["raw"]

    # ---- seller flows: full runs that reached matching and pricing
    seller = [v["result"]["totals"] for k, v in p3.items()
              if k.startswith("coverage:") and str(v["result"]["outcome"]).startswith("listed")]
    blocked = [v["result"]["totals"] for k, v in p3.items()
               if k.startswith("coverage:") and str(v["result"]["outcome"]).startswith(("blocked", "needs_review"))]
    per_agent: dict[str, list[float]] = {}
    for k, v in p3.items():
        if k.startswith("coverage:") and str(v["result"]["outcome"]).startswith("listed"):
            for a in v["result"]["agent_calls"]:
                per_agent.setdefault(a["agent"], []).append(a["cost_usd"])

    # ---- buy requests (new posts: need agent + guard + matching; re-matches: matching only)
    posts, rematch = [], []
    rev = load("eval_reverse.json") or {"results": []}
    for r in rev["results"]:
        (posts if r["case"].startswith(("Riverbend", "Tidewater")) else rematch).append(
            {"cost_usd": r["cost_usd"], "requests": r["requests"]})
    for name in ("two_sided_test.json", "phase5_stress.json"):
        d = load(name) or {}
        for e in d.get("tokens_per_alert_event", []):
            if e.get("run_kind") == "need_flow" and (e.get("requests") or 0) > 1:
                posts.append({"cost_usd": e["cost_usd"], "requests": e["requests"], "input_tokens": e["input_tokens"],
                              "cached_tokens": e["cached_tokens"], "output_tokens": e["output_tokens"],
                              "total_tokens": e["input_tokens"] + e["cached_tokens"] + e["output_tokens"]})
    measured = load("need_post_runs.json")
    if measured:  # 21 real buy requests (each seeded request's text, posted again): the main source
        posts = [{k: r[k] for k in ("cost_usd", "requests", "input_tokens", "cached_tokens", "cache_write_tokens",
                                    "output_tokens", "total_tokens")} for r in measured["runs"]]

    # ---- negotiations
    negs = [v["result"]["totals"] for k, v in p3.items() if k.startswith("neg:")]
    suite = load("negotiation_suite.json") or load("eval_negotiation.json") or {}
    for n in suite.get("negotiations", []):
        if n.get("cost_usd") and "cost cap" not in n.get("label", ""):
            negs.append({"cost_usd": n["cost_usd"], "total_tokens": n.get("tokens")})
    for r in (load("eval_demo_pair.json") or {}).get("runs", []):
        pass  # demo-pair runs are already counted in its spend; per-run cost lives in negotiation records above

    runs = {
        "seller_flow": stats(seller, "Seller flow: post -> listing agent -> compliance -> matching -> pricing -> outreach",
                             "phase3_stress.json coverage runs that were listed"),
        "buy_request": stats(posts, "Buy request (new post): need agent -> guard -> matching -> alerts",
                             "need_post_runs.json (21 real buy requests)" if measured else
                             "two_sided_test / phase5_stress alert events + eval_reverse new posts"),
        "rematch": stats(rematch, "Re-match an existing request (matching agent only)", "eval_reverse.json seeded needs"),
        "negotiation": stats(negs, "Negotiation (both agents, until deal / walk-away / cap)",
                             "phase3_stress.json (18) + negotiation_suite.json (Phase 6)"),
    }
    runs["seller_flow"]["by_agent_avg_cost_usd"] = {a: round(statistics.mean(c), 6) for a, c in per_agent.items()}
    runs["seller_flow"]["blocked_posts"] = {"runs": len(blocked), "avg_model_requests": round(statistics.mean(
        b["requests"] for b in blocked), 2) if blocked else None, "note": "bad records stopped by code before any model call cost $0"}

    unit = {"seller_flows": runs["seller_flow"]["avg_cost_usd"], "buy_requests": runs["buy_request"]["avg_cost_usd"],
            "negotiations": runs["negotiation"]["avg_cost_usd"]}
    per_user = round(sum(PER_USER_MONTH[k] * unit[k] for k in PER_USER_MONTH), 5)
    scale = [{"users": u, "per_month_usd": round(per_user * u, 2), "per_year_usd": round(per_user * u * 12, 2),
              "model_runs_per_month": u * sum(PER_USER_MONTH.values())} for u in USER_SCALES]

    pre = load("prefilter_experiment.json")
    trick = None
    if pre:
        matching_calls = PER_USER_MONTH["seller_flows"] + PER_USER_MONTH["buy_requests"]
        extra = (pre["no_prefilter"]["avg_cost_usd"] - pre["with_prefilter"]["avg_cost_usd"]) * matching_calls
        trick = {
            "name": "SQL pre-filter: code finds the compatible companies, the matching agent only ranks those",
            "with_prefilter": pre["with_prefilter"], "no_prefilter": pre["no_prefilter"],
            "token_reduction_per_matching_call": pre["token_reduction"], "cost_reduction_per_matching_call": pre["cost_reduction"],
            "quality": f"top-1 {pre['with_prefilter']['top1_correct']}/{pre['with_prefilter']['listings']} with vs. "
                       f"{pre['no_prefilter']['top1_correct']}/{pre['no_prefilter']['listings']} without; ungrounded picks "
                       f"{pre['with_prefilter']['ungrounded_picks']} vs. {pre['no_prefilter']['ungrounded_picks']}",
            "extra_cost_without_it_per_user_month_usd": round(extra, 5),
            "extra_cost_without_it_10000_users_year_usd": round(extra * 10_000 * 12, 2),
            "note": "The company list is only 50 here; without a pre-filter the prompt grows with every company that joins, "
                    "while the pre-filter keeps it at the compatible few.",
        }
    other_savings = [
        {"trick": "Code before models", "evidence": "phase3_stress.md test 4b: the 4 obvious bad records were blocked with 0 model requests; "
         "a buy request with no compatible listing skips the matching agent (eval_reverse: 3 needs, 0 matching calls)."},
        {"trick": "Prompt caching (Portkey / OpenAI)", "evidence": f"{runs['seller_flow'].get('cached_share_of_input', 0):.0%} of seller-flow input "
         "tokens were served from cache (billed at $0.01 / 1M instead of $0.10 / 1M)."},
        {"trick": "Code suggests the buyer's budget", "evidence": "no model call for the budget (Phase 6 follow-up); the seller's floor comes "
         "with the pricing agent call that already runs."},
    ]
    caps = {"MAX_MODEL_REQUESTS": config.MAX_MODEL_REQUESTS, "MAX_TOKENS_PER_RUN": config.MAX_TOKENS_PER_RUN,
            "MAX_NEGOTIATION_ROUNDS": config.MAX_NEGOTIATION_ROUNDS, "NEGOTIATION_MAX_COST_USD": config.NEGOTIATION_MAX_COST_USD,
            "SESSION_BUDGET_USD": config.SESSION_BUDGET_USD}

    out = {"model": config.MODEL_NAME, "prices_per_1m_tokens_usd": {"input": 0.10, "cached_input": 0.01, "cache_write": 0.125, "output": 0.50},
           "per_run": runs, "assumptions_per_user_month": PER_USER_MONTH, "cost_per_user_month_usd": per_user,
           "at_scale": scale, "cost_cutting_experiment": trick, "other_savings": other_savings, "caps": caps}
    (OUT / "tokenomics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = ["# Tokenomics", "", f"Model `{config.MODEL_NAME}` via Portkey. Every number below is from real logged runs (`scripts/cost_report.py`).", "",
          "| Run | Runs measured | Avg cost | Avg tokens | Avg model calls | Cached share of input |", "|---|---|---|---|---|---|"]
    for k, r in runs.items():
        md.append(f"| {r['what']} | {r['runs']} | ${r['avg_cost_usd']:.5f} | {r.get('avg_tokens', '—')} | {r.get('avg_model_requests', '—')} | "
                  f"{('%d%%' % round(100 * r['cached_share_of_input'])) if 'cached_share_of_input' in r else '—'} |")
    md += ["", f"**Per user per month** (assumption: {PER_USER_MONTH['seller_flows']} listings, {PER_USER_MONTH['buy_requests']} buy requests, "
           f"{PER_USER_MONTH['negotiations']} negotiations): **${per_user:.4f}**", "", "| Users | Per month | Per year |", "|---|---|---|"]
    md += [f"| {s['users']:,} | ${s['per_month_usd']:,.2f} | ${s['per_year_usd']:,.2f} |" for s in scale]
    if trick:
        md += ["", "## Cost-cutting experiment: the SQL pre-filter", "", "| | With pre-filter | Every company |", "|---|---|---|",
               f"| Companies sent to the matching agent | {trick['with_prefilter']['avg_candidates_sent']} | {trick['no_prefilter']['avg_candidates_sent']} |",
               f"| Avg tokens per matching call | {trick['with_prefilter']['avg_total_tokens']:,} | {trick['no_prefilter']['avg_total_tokens']:,} |",
               f"| Avg cost per matching call | ${trick['with_prefilter']['avg_cost_usd']:.6f} | ${trick['no_prefilter']['avg_cost_usd']:.6f} |",
               f"| Top-1 correct (18 labelled listings) | {trick['with_prefilter']['top1_correct']}/18 | {trick['no_prefilter']['top1_correct']}/18 |",
               f"| Picks code would reject as ungrounded | {trick['with_prefilter']['ungrounded_picks']} | {trick['no_prefilter']['ungrounded_picks']} |",
               "", f"Token reduction {trick['token_reduction_per_matching_call']:.0%}, cost reduction {trick['cost_reduction_per_matching_call']:.0%} per matching call. "
               + trick["note"]]
    md += ["", "## Other savings", ""] + [f"- **{s['trick']}:** {s['evidence']}" for s in other_savings]
    md += ["", "## Caps that stop overspending", "", "\n".join(f"- `{k}` = {v}" for k, v in caps.items())]
    (OUT / "tokenomics.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
