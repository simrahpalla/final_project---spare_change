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
    add("pf_n", w["listings"], "tokenomics.json", "cost_cutting_experiment.with_prefilter.listings")
    add("pf_tok_cut", f"{e['token_reduction_per_matching_call']:.0%}", "tokenomics.json", "cost_cutting_experiment.token_reduction_per_matching_call")
    add("pf_cost_cut", f"{e['cost_reduction_per_matching_call']:.0%}", "tokenomics.json", "cost_cutting_experiment.cost_reduction_per_matching_call")
    pr = {k: tok["per_run"][k]["avg_cost_usd"] for k in ("seller_flow", "buy_request", "negotiation")}
    for name, (sp, bq, ng) in (("light", (5, 2, 3)), ("typical", (a["seller_flows"], a["buy_requests"], a["negotiations"])), ("heavy", (100, 20, 50))):
        m = round(sp * pr["seller_flow"] + bq * pr["buy_request"] + ng * pr["negotiation"], 5)  # rounded like tokenomics.json
        add(f"use_{name}", f"{sp} / {bq} / {ng}", "tokenomics.json", f"usage scenario ({name}): seller posts / buy requests / negotiations per month")
        add(f"use_{name}_month", _usd(m, 3), "tokenomics.json", "Σ runs × per_run.*.avg_cost_usd")
        add(f"use_{name}_100", _usd(m * 100), "tokenomics.json", "per plant per month × 100")
        add(f"use_{name}_10k", _usd(m * 10_000), "tokenomics.json", "per plant per month × 10,000")
        add(f"use_{name}_10k_year", _usd(m * 10_000 * 12), "tokenomics.json", "per plant per month × 10,000 × 12")
    c = tok["caps"]
    add("cap_requests", c["MAX_MODEL_REQUESTS"], "tokenomics.json", "caps.MAX_MODEL_REQUESTS")
    add("cap_tokens", f"{c['MAX_TOKENS_PER_RUN']:,}", "tokenomics.json", "caps.MAX_TOKENS_PER_RUN")
    add("cap_rounds", c["MAX_NEGOTIATION_ROUNDS"], "tokenomics.json", "caps.MAX_NEGOTIATION_ROUNDS")
    add("cap_neg_cost", _usd(c["NEGOTIATION_MAX_COST_USD"]), "tokenomics.json", "caps.NEGOTIATION_MAX_COST_USD")
    add("cap_session", _usd(c["SESSION_BUDGET_USD"]), "tokenomics.json", "caps.SESSION_BUDGET_USD")
    add("blocked_runs", tok["per_run"]["seller_flow"]["blocked_posts"]["runs"], "tokenomics.json", "per_run.seller_flow.blocked_posts.runs (0 model requests each)")

    # ---- the traced run (one real run in the app on 2026-10-26; output/phase11_trace.json, run ids in the audit trail)
    tr = _load("phase11_trace.json")
    t1, t2 = tr["runs"][tr["sell_run"]], tr["runs"][tr["negotiation_run"]]
    audit_ids = {x["run_id"] for x in _load("audit_trail.json") if x.get("action") == "run_end"}
    assert {tr["sell_run"], tr["negotiation_run"], tr["injection_run"]} <= audit_ids, "trace run ids missing from the audit trail"
    add("trace_sell_cost", _usd(t1["cost_usd"], 5), "phase11_trace.json", f"runs[{tr['sell_run']}].cost_usd (= audit run_end)")
    add("trace_sell_req", t1["requests"], "phase11_trace.json", f"runs[{tr['sell_run']}].requests")
    add("trace_neg_cost", _usd(t2["cost_usd"], 5), "phase11_trace.json", f"runs[{tr['negotiation_run']}].cost_usd (= audit run_end)")
    add("trace_neg_req", t2["requests"], "phase11_trace.json", f"runs[{tr['negotiation_run']}].requests")
    add("trace_sell_run", tr["sell_run"], "phase11_trace.json", "sell_run (audit run id)")
    add("trace_neg_run", tr["negotiation_run"], "phase11_trace.json", "negotiation_run (audit run id)")
    add("trace_inj_cost", "$0.00", "audit_trail.json", f"run_end {tr['injection_run']} (0 model requests)")
    sf = tr["seller_flow"]
    for key, v, what in (("tr_score", sf["score"], "seller_flow.score"), ("tr_ask", _usd(sf["ask"], 0), "seller_flow.ask"),
                         ("tr_new", _usd(sf["new_price"], 0), "seller_flow.new_price"), ("tr_scrapunit", _usd(sf["scrap_per_unit"]), "seller_flow.scrap_per_unit"),
                         ("tr_floor_sugg", _usd(sf["floor_suggested"]), "seller_flow.floor_suggested"), ("tr_floor", _usd(sf["floor_confirmed"], 0), "seller_private.floor_price"),
                         ("tr_budget", _usd(sf["budget"], 0), "buyer_private.ceiling_price"), ("tr_rounds", tr["negotiation"]["rounds_used"], "negotiation.rounds_used"),
                         ("tr_price", _usd(tr["deal"]["price"], 0), "deal.price"), ("tr_qty", tr["deal"]["qty"], "deal.qty"),
                         ("tr_total", _usd(sf["deal_total"], 0), "seller_flow.deal_total (price × qty)"), ("tr_under", _usd(sf["under_budget"], 0), "seller_flow.under_budget"),
                         ("tr_co2_listing", sf["listing_co2"], "seller_flow.listing_co2 (12 units)"), ("tr_co2_deal", f"{sf['deal_co2']:.0f}", "seller_flow.deal_co2 (6 units)"),
                         ("tr_listing_qty", sf["qty"], "seller_flow.qty"), ("tr_other1", sf["other_buyers"][0][1], "seller_flow.other_buyers[0]"),
                         ("tr_other2", sf["other_buyers"][1][1], "seller_flow.other_buyers[1]")):
        add(key, v, "phase11_trace.json", what)
    o = tr["offers"]
    add("tr_offers", " → ".join(f"{'S' if x['from_side'] == 'seller' else 'B'} {_usd(x['price'], 0)}{' accept' if x['action'] == 'accept' else ''}" for x in o),
        "phase11_trace.json", "offers[] (S = seller agent, B = buyer agent)")

    # ---- safety and reliability
    sm = saf["summary"]
    for k in ("attack", "malfunction", "overspending"):
        add(f"saf_{k}", f"{sm[k]['pass']}/{sm[k]['tests']}", "safety_tests.json", f"summary.{k}")
    add("saf_total", sum(v["tests"] for v in sm.values()), "safety_tests.json", "summary (sum of tests)")
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
    p3raw = _load("phase3_stress.json")["raw"]["neg:3/3#1"]["result"]
    wo = p3raw["negotiation"]["offers"]
    wa1 = next(r for r in neg["logged_negotiations"] if r["pair"] == "3/3")
    add("wa_floor", _usd(wa1["floor"], 0), "eval_negotiation.json", "logged_negotiations[pair 3/3].floor")
    add("wa_budget", _usd(wa1["ceiling"], 0), "eval_negotiation.json", "logged_negotiations[pair 3/3].ceiling")
    add("wa_rounds", len(wo), "phase3_stress.json", "raw['neg:3/3#1'].result.negotiation.offers (count)")
    add("wa_last_s", _usd(min(x["price"] for x in wo if x["from_side"] == "seller" and x["action"] == "offer"), 0), "phase3_stress.json", "lowest seller offer, pair 3/3 run 1")
    add("wa_last_b", _usd(max(x["price"] for x in wo if x["from_side"] == "buyer" and x["action"] == "offer"), 0), "phase3_stress.json", "highest buyer offer, pair 3/3 run 1")
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
    for k, (lab, f) in {"mro_inventory_usd": ("inv", lambda v: _usd(v, 0)), "sell_through": ("sell", lambda v: f"{v:.0%}"),
                        "line_down_purchases_per_year": ("ldpy", str)}.items():
        for lvl in ("low", "mid", "high"):
            add(f"as_{lab}_{lvl}", f(imp["assumptions"][k][lvl]), "impact_model.json", f"assumptions.{k}.{lvl}")
    for k, lab in (("idle_share", "idle"), ("carrying_cost_rate", "carry"), ("scrap_recovery", "scrap")):
        for lvl in ("low", "mid", "high"):
            add(f"src_{lab}_{lvl}", f"{imp['sourced'][k][lvl]:.0%}", "impact_model.json", f"sourced.{k}.{lvl}")
    pa, ds = M["per_deal_average"], M["deal_set"]
    add("pd_n", pa["n"], "impact_model.json", "measured.per_deal_average.n")
    add("pd_value", _usd(pa["value_recovered_usd"], 0), "impact_model.json", "measured.per_deal_average.value_recovered_usd")
    add("pd_scrap", _usd(pa["scrap_value_usd"], 0), "impact_model.json", "measured.per_deal_average.scrap_value_usd")
    add("pd_co2", f"{pa['est_kg_co2e_avoided']:.1f}", "impact_model.json", "measured.per_deal_average.est_kg_co2e_avoided")
    add("pd_co2_n", pa["co2_n"], "impact_model.json", "measured.per_deal_average.co2_n (chemical deals have no CO2 claim)")
    add("ds_logged", ds["logged"], "impact_model.json", "measured.deal_set.logged")
    add("ds_excluded", ds["logged"] - ds["used"], "impact_model.json", "measured.deal_set.logged - used")

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
    add("automa_products", "10M+", "competitors.md", "Automa row: homepage '10 million unique, standardised products'")
    add("automa_suppliers", "750+", "competitors.md", "Automa row: homepage '750+ Trusted Suppliers'")
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
