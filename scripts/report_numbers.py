r"""The numbers ledger for report.html and slides.html.

    python scripts\report_numbers.py      # writes output/report_numbers.md

Every number the report or slides print is a key here, read from an evidence file in output/ (or, for external
numbers, a sourced row of output/impact_sources.md). report/report.md and slides/slides.md write {{key}};
build_report.py / build_slides.py replace each key with its value and refuse to build if a key is unknown.
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "output"


def _load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def _usd(x, d=2):
    return f"${x:,.{d}f}"


def build() -> dict:
    """key -> (display value, source file, field / how)."""
    N = {}

    def add(key, value, src, field):
        N[key] = (str(value), src, field)

    tok, saf, mat, neg = _load("tokenomics.json"), _load("safety_tests.json"), _load("eval_matching.json"), _load("eval_negotiation.json")
    imp, conc, smoke = _load("impact_model.json"), _load("concurrency_test.json"), _load("mcp_smoke.json")

    # ---- tokenomics
    p = tok["prices_per_1m_tokens_usd"]
    add("price_in", _usd(p["input"]), "tokenomics.json", "prices_per_1m_tokens_usd.input")
    add("price_cached", _usd(p["cached_input"]), "tokenomics.json", "prices_per_1m_tokens_usd.cached_input")
    add("price_write", _usd(p["cache_write"], 3), "tokenomics.json", "prices_per_1m_tokens_usd.cache_write")
    add("price_out", _usd(p["output"]), "tokenomics.json", "prices_per_1m_tokens_usd.output")
    for k, label in (("seller_flow", "sell"), ("buy_request", "buy"), ("negotiation", "neg")):
        r = tok["per_run"][k]
        add(f"{label}_runs", r["runs"], "tokenomics.json", f"per_run.{k}.runs")
        add(f"{label}_cost", _usd(r["avg_cost_usd"], 5), "tokenomics.json", f"per_run.{k}.avg_cost_usd")
        add(f"{label}_in", f"{r['avg_input_tokens']:,}", "tokenomics.json", f"per_run.{k}.avg_input_tokens (incl. cached and cache-write)")
        add(f"{label}_cached", f"{round(r['avg_input_tokens'] * r['cached_share_of_input']):,}", "tokenomics.json",
            f"per_run.{k}.avg_input_tokens × cached_share_of_input")
        add(f"{label}_cached_pct", f"{r['cached_share_of_input']:.0%}", "tokenomics.json", f"per_run.{k}.cached_share_of_input")
        add(f"{label}_out", f"{r['avg_output_tokens']:,}", "tokenomics.json", f"per_run.{k}.avg_output_tokens")
        add(f"{label}_req", r["avg_model_requests"], "tokenomics.json", f"per_run.{k}.avg_model_requests")
    r = tok["per_run"]["rematch"]
    add("rematch_cost", _usd(r["avg_cost_usd"], 5), "tokenomics.json", "per_run.rematch.avg_cost_usd")
    a = tok["assumptions_per_user_month"]
    add("assume_sell", a["seller_flows"], "tokenomics.json", "assumptions_per_user_month.seller_flows")
    add("assume_buy", a["buy_requests"], "tokenomics.json", "assumptions_per_user_month.buy_requests")
    add("assume_neg", a["negotiations"], "tokenomics.json", "assumptions_per_user_month.negotiations")
    add("user_month", _usd(tok["cost_per_user_month_usd"], 3), "tokenomics.json", "cost_per_user_month_usd")
    for s in tok["at_scale"]:
        u = s["users"]
        add(f"u{u}_month", _usd(s["per_month_usd"]), "tokenomics.json", f"at_scale[users={u}].per_month_usd")
        add(f"u{u}_year", _usd(s["per_year_usd"]), "tokenomics.json", f"at_scale[users={u}].per_year_usd")
    e = tok["cost_cutting_experiment"]
    w, n = e["with_prefilter"], e["no_prefilter"]
    add("pf_cand_with", w["avg_candidates_sent"], "tokenomics.json", "cost_cutting_experiment.with_prefilter.avg_candidates_sent")
    add("pf_cand_without", n["avg_candidates_sent"], "tokenomics.json", "cost_cutting_experiment.no_prefilter.avg_candidates_sent")
    add("pf_tok_with", f"{w['avg_total_tokens']:,}", "tokenomics.json", "cost_cutting_experiment.with_prefilter.avg_total_tokens")
    add("pf_tok_without", f"{n['avg_total_tokens']:,}", "tokenomics.json", "cost_cutting_experiment.no_prefilter.avg_total_tokens")
    add("pf_cost_with", _usd(w["avg_cost_usd"], 5), "tokenomics.json", "cost_cutting_experiment.with_prefilter.avg_cost_usd")
    add("pf_cost_without", _usd(n["avg_cost_usd"], 5), "tokenomics.json", "cost_cutting_experiment.no_prefilter.avg_cost_usd")
    add("pf_top1_with", f"{w['top1_correct']}/{w['listings']}", "tokenomics.json", "cost_cutting_experiment.with_prefilter.top1_correct / listings")
    add("pf_top1_without", f"{n['top1_correct']}/{n['listings']}", "tokenomics.json", "cost_cutting_experiment.no_prefilter.top1_correct / listings")
    add("pf_tok_cut", f"{e['token_reduction_per_matching_call']:.0%}", "tokenomics.json", "cost_cutting_experiment.token_reduction_per_matching_call")
    add("pf_cost_cut", f"{e['cost_reduction_per_matching_call']:.0%}", "tokenomics.json", "cost_cutting_experiment.cost_reduction_per_matching_call")
    c = tok["caps"]
    add("cap_requests", c["MAX_MODEL_REQUESTS"], "tokenomics.json", "caps.MAX_MODEL_REQUESTS")
    add("cap_tokens", f"{c['MAX_TOKENS_PER_RUN']:,}", "tokenomics.json", "caps.MAX_TOKENS_PER_RUN")
    add("cap_rounds", c["MAX_NEGOTIATION_ROUNDS"], "tokenomics.json", "caps.MAX_NEGOTIATION_ROUNDS")
    add("cap_neg_cost", _usd(c["NEGOTIATION_MAX_COST_USD"]), "tokenomics.json", "caps.NEGOTIATION_MAX_COST_USD")
    add("cap_session", _usd(c["SESSION_BUDGET_USD"]), "tokenomics.json", "caps.SESSION_BUDGET_USD")
    add("blocked_runs", tok["per_run"]["seller_flow"]["blocked_posts"]["runs"], "tokenomics.json", "per_run.seller_flow.blocked_posts.runs (0 model requests each)")

    # ---- the traced run (audit trail, one real run on 2026-10-26)
    audit = _load("audit_trail.json")
    ends = {x["run_id"]: json.loads(x["result"]) for x in audit if x.get("action") == "run_end" and x["run_id"] in ("bb3d14b89de2", "fe8ce4b551be", "808f89078e9c")}
    t1, t2, t3 = ends["bb3d14b89de2"], ends["fe8ce4b551be"], ends["808f89078e9c"]
    add("trace_sell_cost", _usd(t1["cost_usd"], 5), "audit_trail.json", "run_end of run bb3d14b89de2 .cost_usd")
    add("trace_sell_req", t1["requests"], "audit_trail.json", "run_end bb3d14b89de2 .requests")
    add("trace_sell_in", f"{t1['input_tokens']:,}", "audit_trail.json", "run_end bb3d14b89de2 .input_tokens (uncached)")
    add("trace_sell_cached", f"{t1['cached_tokens']:,}", "audit_trail.json", "run_end bb3d14b89de2 .cached_tokens")
    add("trace_sell_out", f"{t1['output_tokens']:,}", "audit_trail.json", "run_end bb3d14b89de2 .output_tokens")
    add("trace_neg_cost", _usd(t2["cost_usd"], 5), "audit_trail.json", "run_end fe8ce4b551be .cost_usd")
    add("trace_neg_req", t2["requests"], "audit_trail.json", "run_end fe8ce4b551be .requests")
    add("trace_inj_cost", _usd(t3["cost_usd"]), "audit_trail.json", "run_end 808f89078e9c .cost_usd (0 requests)")

    # ---- safety and reliability
    sm = saf["summary"]
    for k in ("attack", "malfunction", "overspending"):
        add(f"saf_{k}", f"{sm[k]['pass']}/{sm[k]['tests']}", "safety_tests.json", f"summary.{k}")
    b = conc["before"][0]
    add("crash_before", f"{b['crashes']}/{b['jobs']}", "concurrency_test.json", "before[0].crashes / jobs (6 at once, process per run)")
    r0 = conc["runs"][0]
    add("crash_after", f"{r0['crashes']}/{r0['jobs']}", "concurrency_test.json", "runs[0].crashes / jobs (6 at once, shared processes)")
    add("crash_conc", r0["concurrency"], "concurrency_test.json", "runs[0].concurrency")
    o = neg["overall"]
    add("neg_n", o["negotiations"], "eval_negotiation.json", "overall.negotiations")
    add("neg_deals", o["deals"], "eval_negotiation.json", "overall.deals")
    add("neg_violations", o["limit_violations"], "eval_negotiation.json", "overall.limit_violations")
    add("neg_rounds", o["avg_rounds"], "eval_negotiation.json", "overall.avg_rounds")
    pf = neg["prompt_fix_effect"]
    add("narrow_before", f"{pf['before_phase6_fix']['deals']}/{pf['before_phase6_fix']['negotiations']}", "eval_negotiation.json", "prompt_fix_effect.before_phase6_fix")
    add("narrow_after", f"{pf['after_phase6_fix']['deals']}/{pf['after_phase6_fix']['negotiations']}", "eval_negotiation.json", "prompt_fix_effect.after_phase6_fix")
    wa = neg["by_pair_type"]["walk_away"]
    add("walk_n", wa["negotiations"], "eval_negotiation.json", "by_pair_type.walk_away.negotiations")
    add("walk_deals", wa["deals"], "eval_negotiation.json", "by_pair_type.walk_away.deals")
    add("auto_e2e", f"{neg['auto_negotiate_e2e']['pass']}/{neg['auto_negotiate_e2e']['checks']}", "eval_negotiation.json", "auto_negotiate_e2e")
    add("top1", mat["forward_matching"]["top1"], "eval_matching.json", "forward_matching.top1")
    add("top3", mat["forward_matching"]["top3"], "eval_matching.json", "forward_matching.top3")
    add("reverse", mat["reverse_matching"]["correct"], "eval_matching.json", "reverse_matching.correct")
    add("fields", mat["listing_extraction"]["result"].split(" ")[0], "eval_matching.json", "listing_extraction.result")
    add("factcheck", mat["fact_check"]["result"], "eval_matching.json", "fact_check.result")
    br = mat["buy_requests_as_new_posts"]
    add("req_n", br["runs"], "eval_matching.json", "buy_requests_as_new_posts.runs")
    add("req_matched", br["posted_and_matched"], "eval_matching.json", "buy_requests_as_new_posts.posted_and_matched")
    add("req_flagged", len(br["flagged_by_guard"]), "eval_matching.json", "buy_requests_as_new_posts.flagged_by_guard (false positive)")
    calls = smoke.get("summary", smoke)
    ok = sum(1 for x in smoke["calls"] if x.get("passed")) if "calls" in smoke else None
    if ok is not None:
        add("smoke", f"{ok}/{len(smoke['calls'])}", "mcp_smoke.json", "calls[].passed")
    tools = {x["tool"] for x in smoke.get("calls", []) if "tool" in x}
    if tools:
        add("tools", len(tools), "mcp_smoke.json", "distinct calls[].tool")

    add("roles", len(smoke["tools_by_role"]), "mcp_smoke.json", "tools_by_role (count of roles)")
    add("data_size", mat["caveats"][0].replace("Synthetic data: ", "").rstrip("."), "eval_matching.json", "caveats[0]")
    add("symmetry_gap", mat["symmetry"]["max_gap"], "eval_matching.json", "symmetry.max_gap")
    add("symmetry_pairs", mat["symmetry"]["pairs"], "eval_matching.json", "symmetry.pairs")

    add("github_url", (OUT / "github_url.txt").read_text(encoding="utf-8").strip(), "github_url.txt", "repo link")
    con = sqlite3.connect(REPO / "data" / "exchange.db")
    fx = {r[0]: (r[1], r[2]) for r in con.execute("SELECT family, kg_co2e_per_kg, kg_co2e_per_unit FROM carbon_factors")}
    add("reuse", con.execute("SELECT value FROM exchange_meta WHERE key='reuse_credit'").fetchone()[0], "data/exchange.db", "exchange_meta.reuse_credit")
    con.close()
    add("f_steel", fx["Bearing"][0], "data/exchange.db", "carbon_factors[Bearing].kg_co2e_per_kg (= impact_sources.md steel row)")
    add("f_iron", fx["Pump"][0], "data/exchange.db", "carbon_factors[Pump].kg_co2e_per_kg (= impact_sources.md cast iron row)")
    add("f_cpu", f"{fx['PLC CPU'][1]:g}", "data/exchange.db", "carbon_factors[PLC CPU].kg_co2e_per_unit")
    add("f_module", f"{fx['PLC I/O'][1]:g}", "data/exchange.db", "carbon_factors[PLC I/O].kg_co2e_per_unit")

    # ---- the traced run, as shown on the phase11-* screenshots (see output/phase11_trace.md)
    T = "phase11_trace.md + screenshots"
    for key, v, what in (("tr_score", "98", "Riverbend's match score (phase11-sell-buyers)"), ("tr_ask", "$1,425", "suggested ask (phase11-sell-buyers)"),
                         ("tr_new", "$2,966", "new (list) price (phase11-sell-buyers)"), ("tr_scrapunit", "$45.64", "scrap value per unit (phase11-sell-buyers)"),
                         ("tr_floor", "$998", "seller's confirmed floor (phase11-negotiation-seller)"), ("tr_budget", "$1,890", "buyer's budget (phase11-negotiation-buyer)"),
                         ("tr_rounds", "2", "rounds used (negotiations.rounds_used)"), ("tr_price", "$1,425", "deal price (deals.price)"),
                         ("tr_co2_listing", "21", "est. kg CO2e for the 3-unit listing (phase11-sell-top)"),
                         ("tr_co2_deal", "7", "est. kg CO2e for the 1-unit deal (phase11-deal-approved)"),
                         ("tr_under", "$465", "deal under the buyer's budget (phase11-deal-approved)"),
                         ("tr_tokens_ui", "7,593", "tokens on the cost meter, incl. cache-write (phase11-sell-top)")):
        add(key, v, T, what)

    # ---- impact (impact_model.json) and per-deal averages from the logged test deals
    mid = imp["mid_scenario"]
    add("imp_idle", _usd(mid["idle_inventory_usd"], 0), "impact_model.json", "mid_scenario.idle_inventory_usd")
    add("imp_scrap", _usd(mid["one_time"]["recovered_if_all_scrapped_usd"], 0), "impact_model.json", "mid_scenario.one_time.recovered_if_all_scrapped_usd")
    add("imp_with", _usd(mid["one_time"]["recovered_with_spare_change_usd"], 0), "impact_model.json", "mid_scenario.one_time.recovered_with_spare_change_usd")
    add("imp_extra", _usd(mid["one_time"]["extra_recovered_vs_scrap_usd"], 0), "impact_model.json", "mid_scenario.one_time.extra_recovered_vs_scrap_usd")
    add("imp_co2", f"{mid['one_time']['est_kg_co2e_avoided']:,}", "impact_model.json", "mid_scenario.one_time.est_kg_co2e_avoided")
    add("imp_carry", _usd(mid["per_year"]["carrying_cost_avoided_usd"], 0), "impact_model.json", "mid_scenario.per_year.carrying_cost_avoided_usd")
    add("imp_carry_all", _usd(mid["per_year"]["carrying_cost_of_idle_stock_usd"], 0), "impact_model.json", "mid_scenario.per_year.carrying_cost_of_idle_stock_usd")
    add("imp_down", _usd(mid["per_year"]["buyer_downtime_value_usd"], 0), "impact_model.json", "mid_scenario.per_year.buyer_downtime_value_usd")
    add("imp_model", _usd(mid["per_year"]["app_model_cost_usd"]), "impact_model.json", "mid_scenario.per_year.app_model_cost_usd")
    add("imp_multiple", f"{mid['one_time']['recovered_with_spare_change_usd'] / mid['one_time']['recovered_if_all_scrapped_usd']:.1f}×", "impact_model.json",
        "recovered_with_spare_change_usd ÷ recovered_if_all_scrapped_usd")
    for lvl, key in (("all_low", "lo"), ("all_high", "hi")):
        s = imp[lvl]
        add(f"imp_extra_{key}", _usd(s["one_time"]["extra_recovered_vs_scrap_usd"], 0), "impact_model.json", f"{lvl}.one_time.extra_recovered_vs_scrap_usd")
        add(f"imp_co2_{key}", f"{s['one_time']['est_kg_co2e_avoided']:,}", "impact_model.json", f"{lvl}.one_time.est_kg_co2e_avoided")
        add(f"imp_carry_{key}", _usd(s["per_year"]["carrying_cost_avoided_usd"], 0), "impact_model.json", f"{lvl}.per_year.carrying_cost_avoided_usd")
        add(f"imp_down_{key}", _usd(s["per_year"]["buyer_downtime_value_usd"], 0), "impact_model.json", f"{lvl}.per_year.buyer_downtime_value_usd")
    M = imp["measured"]
    add("recovery", f"{M['negotiated_price_over_new_price']['value']:.0%}", "impact_model.json", "measured.negotiated_price_over_new_price.value")
    add("recovery_n", M["negotiated_price_over_new_price"]["n"], "impact_model.json", "measured.negotiated_price_over_new_price.n")
    add("recovery_lo", f"{M['negotiated_price_over_new_price']['range'][0]:.0%}", "impact_model.json", "measured.negotiated_price_over_new_price.range[0]")
    add("recovery_hi", f"{M['negotiated_price_over_new_price']['range'][1]:.0%}", "impact_model.json", "measured.negotiated_price_over_new_price.range[1]")
    add("co2_per_dollar", M["kg_co2e_per_dollar_of_new_value"]["value"], "impact_model.json", "measured.kg_co2e_per_dollar_of_new_value.value")
    dd = imp["downtime_in_our_logged_deals"]
    add("ld_deals", dd["line_down_deals_logged"], "impact_model.json", "downtime_in_our_logged_deals.line_down_deals_logged")
    add("ld_of", dd["deals_logged"], "impact_model.json", "downtime_in_our_logged_deals.deals_logged")
    add("ld_value", _usd(dd["downtime_value_lower_bound_usd"], 0), "impact_model.json", "downtime_in_our_logged_deals.downtime_value_lower_bound_usd")
    for k, (lab, f) in {"mro_inventory_usd": ("inv", lambda v: _usd(v, 0)), "sell_through": ("sell", lambda v: f"{v:.0%}"),
                        "line_down_purchases_per_year": ("ldpy", str)}.items():
        for lvl in ("low", "mid", "high"):
            add(f"as_{lab}_{lvl}", f(imp["assumptions"][k][lvl]), "impact_model.json", f"assumptions.{k}.{lvl}")
    for k, lab in (("idle_share", "idle"), ("carrying_cost_rate", "carry"), ("scrap_recovery", "scrap")):
        for lvl in ("low", "mid", "high"):
            add(f"src_{lab}_{lvl}", f"{imp['sourced'][k][lvl]:.0%}", "impact_model.json", f"sourced.{k}.{lvl}")
    pd = per_deal_averages(neg)
    add("pd_n", pd["n"], "eval_negotiation.json + data/exchange.db", "logged deals with a price, impact via get_impact_estimate(listing, price, qty)")
    add("pd_value", _usd(pd["value"], 0), "eval_negotiation.json + get_impact_estimate", "mean value_recovered per deal")
    add("pd_scrap", _usd(pd["scrap"], 0), "eval_negotiation.json + get_impact_estimate", "mean scrap_value_total per deal")
    add("pd_co2", f"{pd['co2']:.1f}", "eval_negotiation.json + get_impact_estimate", "mean est_kg_co2e_avoided per deal (non-chemical)")

    # ---- external numbers (each a sourced row of output/impact_sources.md)
    S = "impact_sources.md"
    for key, v, row in (("tcod_total", "$1.4 trillion", "Siemens TCOD 2024 row 1"), ("tcod_pct", "11%", "Siemens TCOD 2024 row 1"),
                        ("tcod_hour", "$36,000", "Siemens TCOD 2024 row 2 (lowest-cost sector, lower bound)"),
                        ("restart_before", "49", "Siemens TCOD 2024 row 3 (2019)"), ("restart_after", "81", "Siemens TCOD 2024 row 3"),
                        ("downtime_hours", "27", "Siemens TCOD 2024 row 5"), ("idle_pct", "22%", "SPARETECH 2025 via Reliamag"),
                        ("carry_range", "15–30%", "Cleverence carrying-cost row"), ("scrap_range", "5–15%", "Maas Companies scrap row"),
                        ("auction_range", "30–60%", "Maas Companies auction row"), ("lead_new", "16–20 weeks", "Automa lead-time row"),
                        ("lead_surplus", "2–10 days", "Automa lead-time row"), ("s7_end", "October 2025", "Eichler / automa.net S7-300 row"),
                        ("s7_spares", "2033", "Eichler / automa.net S7-300 row"), ("us_sites", "about 280,000", "Census CBP summary row"),
                        ("reman_range", "46–93%", "reuse credit row (Energies 2024; MAN/Bayreuth; Curtin)"),
                        ("drum", "$242", "Alachua County fee schedule row")):
        add(key, v, S, row)
    add("share_10k", f"{10_000 / 280_000:.1%}", S, "10,000 ÷ about 280,000 US manufacturing establishments")
    return N


def per_deal_averages(neg) -> dict:
    """Averages over the logged test deals, through the app's own get_impact_estimate on a scratch DB copy."""
    tmp = Path(tempfile.mkdtemp(prefix="sx_rn_"))
    shutil.copyfile(REPO / "data" / "exchange.db", tmp / "w.db")
    os.chmod(tmp / "w.db", 0o600)
    os.environ.update(SURPLUS_DB=str(tmp / "w.db"), SURPLUS_ROLE="system")
    sys.path.insert(0, str(REPO / "mcp_server"))
    import server  # noqa: E402
    con = sqlite3.connect(tmp / "w.db")
    vals, scraps, co2s = [], [], []
    for r in neg["logged_negotiations"]:
        if not r.get("price") or r["status"] not in ("agreed", "approved", "rejected") or "/" not in str(r["pair"]):
            continue
        lid, nid = (int(x) for x in str(r["pair"]).split("/"))
        lq = con.execute("SELECT qty FROM listings WHERE id=?", (lid,)).fetchone()
        nq = con.execute("SELECT qty FROM needs WHERE id=?", (nid,)).fetchone()
        if not lq or not nq:
            continue
        e = server.get_impact_estimate(lid, price=r["price"], qty=min(lq[0], nq[0]))
        vals.append(e["value_recovered"])
        scraps.append(e["scrap_value_total"])
        if e["est_kg_co2e_avoided"] is not None:
            co2s.append(e["est_kg_co2e_avoided"])
    con.close()
    shutil.rmtree(tmp, ignore_errors=True)
    return {"n": len(vals), "value": sum(vals) / len(vals), "scrap": sum(scraps) / len(scraps), "co2": sum(co2s) / len(co2s)}


def write_ledger(N, used: dict | None = None):
    lines = ["# Report numbers ledger", "",
             "Generated by `scripts/report_numbers.py` (and rewritten by `build_report.py` / `build_slides.py` with where each number is used). "
             "Every number in `report.html` and `slides.html` is a `{{key}}` in `report/report.md` or `slides/slides.md`, filled from this table; "
             "the build fails on an unknown key. External numbers trace to a sourced row of `output/impact_sources.md`.", "",
             "| Key | Value | Source file | Field | Used in |", "|---|---|---|---|---|"]
    for k, (v, src, field) in N.items():
        lines.append(f"| `{k}` | {v} | `{src}` | {field} | {', '.join(sorted((used or {}).get(k, []))) or '—'} |")
    (OUT / "report_numbers.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    N = build()
    write_ledger(N)
    print(f"{len(N)} numbers → output/report_numbers.md")
