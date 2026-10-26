r"""Impact model for one mid-size plant (Phase 10), from impact_research.md section 3.

    .venv\Scripts\python.exe scripts\impact_model.py                      # reads the evidence in output/
    .venv\Scripts\python.exe scripts\impact_model.py --evidence-dir DIR   # reads phase3_stress.json, eval_negotiation.json,
                                                                          # tokenomics.json from DIR (used by check_impact.py)

Every input is labelled MEASURED (read from this app's evidence files), SOURCED (external; links in
output/impact_sources.md) or ASSUMPTION (a stated guess with a low / mid / high range). CO2e uses the app's own
get_impact_estimate (the same function behind the impact strip, the deal card and the Marketplace). Outputs are
labelled ONE-TIME (recovered $, CO2e for the stock sold once) or PER YEAR (carrying cost, downtime, model cost) and are
never added together. No model calls. Writes output/impact_model.json and output/impact_model.md.
"""

import argparse
import json
import os
import shutil
import sqlite3
import statistics
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "output"
sys.stdout.reconfigure(encoding="utf-8")

DOWNTIME_RATE = 36_000  # USD per hour: Siemens TCOD 2024, lowest-cost sector (consumer goods); used as a lower bound only


def measured_inputs(evidence: Path) -> dict:
    load = lambda n: json.loads((evidence / n).read_text(encoding="utf-8"))  # noqa: E731
    p3, neg, tok = load("phase3_stress.json")["raw"], load("eval_negotiation.json"), load("tokenomics.json")
    asks = [s["ask"] / s["new_price"] for k, v in p3.items() if k.startswith("coverage:")
            for s in v["result"]["steps"] if s["step"] == "pricing" and s.get("new_price")]

    # The app's own impact function, on a scratch copy of the seed database (never the original)
    tmp = Path(tempfile.mkdtemp(prefix="sx_imp_"))
    shutil.copyfile(REPO / "data" / "exchange.db", tmp / "w.db")
    os.chmod(tmp / "w.db", 0o600)
    os.environ.update(SURPLUS_DB=str(tmp / "w.db"), SURPLUS_ROLE="system")
    sys.path.insert(0, str(REPO / "mcp_server"))
    import server  # noqa: E402
    con = sqlite3.connect(tmp / "w.db")
    con.row_factory = sqlite3.Row
    lst = con.execute("SELECT l.id, l.qty, p.new_price, p.category FROM listings l JOIN part_catalog p ON p.part_number=l.part_number "
                      "WHERE l.status='active'").fetchall()
    new_price = {r["id"]: r["new_price"] for r in con.execute("SELECT l.id, p.new_price FROM listings l JOIN part_catalog p ON p.part_number=l.part_number")}
    urgency = {r["id"]: r["urgency"] for r in con.execute("SELECT id, urgency FROM needs")}
    req_share = sum(1 for u in urgency.values() if u == "line_down") / len(urgency)
    con.close()
    per_dollar = []
    for r in lst:
        if r["category"] == "chemical" or not r["new_price"]:
            continue  # no CO2 claim for chemicals
        e = server.get_impact_estimate(r["id"])
        per_dollar.append(e["est_kg_co2e_avoided"] / (r["new_price"] * r["qty"]))

    # ONE deal set for every price and impact statistic: logged deals whose listing AND request are in the seed
    # database (a deal on a listing or request created during a test run can't be priced from the seed catalog)
    all_deals = [r for r in neg["logged_negotiations"] if r.get("price") and r["status"] in ("agreed", "approved", "rejected")]
    ids = lambda r: [int(x) for x in str(r["pair"]).split("/") if x.isdigit()]  # noqa: E731  pair = "listing/need"
    deals = [r for r in all_deals if len(ids(r)) == 2 and ids(r)[0] in new_price and ids(r)[1] in urgency]
    ratio = [r["price"] / new_price[ids(r)[0]] for r in deals]
    line_down = [r for r in deals if urgency[ids(r)[1]] == "line_down"]
    con = sqlite3.connect(tmp / "w.db")
    vals, scraps, co2s = [], [], []
    for r in deals:
        lid, nid = ids(r)
        q = min(con.execute("SELECT qty FROM listings WHERE id=?", (lid,)).fetchone()[0], con.execute("SELECT qty FROM needs WHERE id=?", (nid,)).fetchone()[0])
        e = server.get_impact_estimate(lid, price=r["price"], qty=q)
        vals.append(e["value_recovered"])
        scraps.append(e["scrap_value_total"])
        if e["est_kg_co2e_avoided"] is not None:
            co2s.append(e["est_kg_co2e_avoided"])
    con.close()
    shutil.rmtree(tmp, ignore_errors=True)
    return {
        "suggested_ask_over_new_price": {"value": round(statistics.mean(asks), 3), "n": len(asks), "range": [round(min(asks), 3), round(max(asks), 3)],
                                         "file": "phase3_stress.json", "basis": "pricing agent's suggested ask ÷ catalog new price (coverage runs)"},
        "negotiated_price_over_new_price": {"value": round(statistics.mean(ratio), 3), "n": len(ratio), "range": [round(min(ratio), 3), round(max(ratio), 3)],
                                            "file": "eval_negotiation.json", "basis": "agreed price ÷ new price over every logged deal"},
        "kg_co2e_per_dollar_of_new_value": {"value": round(statistics.mean(per_dollar), 5), "n": len(per_dollar), "file": "data/exchange.db via get_impact_estimate",
                                            "basis": "get_impact_estimate (sourced factors × 0.5 reuse credit) ÷ new value, over active non-chemical listings"},
        "app_cost_per_user_month_usd": {"value": tok["cost_per_user_month_usd"], "file": "tokenomics.json", "basis": "real token logs × stated usage"},
        "deal_set": {"used": len(deals), "logged": len(all_deals), "file": "eval_negotiation.json",
                     "excluded": "deals on a listing or request created during a test run (not in the seed catalog, so they can't be priced)"},
        "per_deal_average": {"n": len(deals), "value_recovered_usd": round(statistics.mean(vals)), "scrap_value_usd": round(statistics.mean(scraps)),
                             "est_kg_co2e_avoided": round(statistics.mean(co2s), 1), "co2_n": len(co2s), "file": "eval_negotiation.json + get_impact_estimate",
                             "basis": "average per logged test deal (agreed price × quantity); test deals repeat the same pairs, so these are averages, never totals"},
        "line_down_deals": {"value": len(line_down), "of_deals": len(deals), "file": "eval_negotiation.json",
                            "basis": "deals whose buyer request was marked line down (the only kind of purchase given a downtime value in the plant model)"},
        "line_down_share_of_requests": {"value": round(req_share, 3), "n": len(urgency), "file": "data/exchange.db (synthetic demo data)",
                                        "basis": "share of seeded buy requests marked line down"},
    }


SOURCED = {
    "idle_share": {"mid": 0.22, "low": 0.15, "high": 0.22, "source": "SPARETECH 2025 survey (22% unused 5+ years); low = ~15% obsolete (Reliable Plant)"},
    "carrying_cost_rate": {"mid": 0.20, "low": 0.15, "high": 0.30, "source": "industry range 15–30% of value per year"},
    "scrap_recovery": {"mid": 0.10, "low": 0.05, "high": 0.15, "source": "industrial liquidator benchmarks 5–15%"},
}
ASSUMPTIONS = {
    "mro_inventory_usd": {"mid": 3_000_000, "low": 1_500_000, "high": 6_000_000, "why": "a mid-size plant's spare-parts inventory (research section 3)"},
    "sell_through": {"mid": 0.50, "low": 0.25, "high": 0.75, "why": "share of the idle stock that finds a buyer (the rest is still scrapped); not measured"},
    "line_down_purchases_per_year": {"mid": 1, "low": 0, "high": 3,
                                     "why": "line-down emergencies per year this plant fills with a surplus part; each counts 1 hour at $36k (lower bound). "
                                            "Only line-down purchases get a downtime value."},
    "users_per_plant": {"mid": 1, "low": 1, "high": 3, "why": "accounts one plant runs on the app"},
}


def model(M, inv, idle, carry, scrap, sell, ld, users):
    idle_value = inv * idle
    sold = idle_value * sell
    recovery = M["negotiated_price_over_new_price"]["value"]
    with_app = sold * recovery + (idle_value - sold) * scrap
    return {
        "idle_inventory_usd": round(idle_value),
        "one_time": {"recovered_if_all_scrapped_usd": round(idle_value * scrap), "recovered_with_spare_change_usd": round(with_app),
                     "extra_recovered_vs_scrap_usd": round(with_app - idle_value * scrap),
                     "est_kg_co2e_avoided": round(sold * M["kg_co2e_per_dollar_of_new_value"]["value"])},
        "per_year": {"carrying_cost_of_idle_stock_usd": round(idle_value * carry), "carrying_cost_avoided_usd": round(sold * carry),
                     "buyer_downtime_value_usd": round(ld * DOWNTIME_RATE),
                     "app_model_cost_usd": round(M["app_cost_per_user_month_usd"]["value"] * 12 * users, 2)},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", default=str(OUT))
    ap.add_argument("--out-dir", default=str(OUT))
    a = ap.parse_args()
    M = measured_inputs(Path(a.evidence_dir))
    lv = lambda d, level: d[level]  # noqa: E731
    base = {"inv": ASSUMPTIONS["mro_inventory_usd"]["mid"], "idle": SOURCED["idle_share"]["mid"], "carry": SOURCED["carrying_cost_rate"]["mid"],
            "scrap": SOURCED["scrap_recovery"]["mid"], "sell": ASSUMPTIONS["sell_through"]["mid"],
            "ld": ASSUMPTIONS["line_down_purchases_per_year"]["mid"], "users": ASSUMPTIONS["users_per_plant"]["mid"]}

    def scenario(level):
        return model(M, lv(ASSUMPTIONS["mro_inventory_usd"], level), lv(SOURCED["idle_share"], level), lv(SOURCED["carrying_cost_rate"], level),
                     lv(SOURCED["scrap_recovery"], level), lv(ASSUMPTIONS["sell_through"], level),
                     lv(ASSUMPTIONS["line_down_purchases_per_year"], level), lv(ASSUMPTIONS["users_per_plant"], level))
    mid, lo, hi = scenario("mid"), scenario("low"), scenario("high")
    sens = []
    for name, key, rng in (("MRO inventory", "inv", ASSUMPTIONS["mro_inventory_usd"]), ("Idle share", "idle", SOURCED["idle_share"]),
                           ("Carrying cost rate", "carry", SOURCED["carrying_cost_rate"]), ("Scrap recovery", "scrap", SOURCED["scrap_recovery"]),
                           ("Sell-through", "sell", ASSUMPTIONS["sell_through"]),
                           ("Line-down purchases / year", "ld", ASSUMPTIONS["line_down_purchases_per_year"])):
        sens.append({"input": name, **{lvl: {"value": rng[lvl], **model(M, **dict(base, **{key: rng[lvl]}))} for lvl in ("low", "mid", "high")}})
    per_deal = {"line_down_deals_logged": M["line_down_deals"]["value"], "deals_logged": M["line_down_deals"]["of_deals"],
                "note": "count only: test deals repeat the same pairs, so no dollar total is given; downtime is valued only in the plant model"}
    out = {"what": "Illustrative impact for one mid-size plant. MEASURED = read from this app's evidence files; SOURCED = external "
                   "(output/impact_sources.md); ASSUMPTION = stated guess with a range. ONE-TIME and PER-YEAR values are never added together.",
           "measured": M, "sourced": SOURCED | {"downtime_cost_per_hour": {"value": DOWNTIME_RATE, "source": "Siemens TCOD 2024, lowest-cost sector; lower bound"}},
           "assumptions": ASSUMPTIONS, "mid_scenario": mid, "all_low": lo, "all_high": hi, "sensitivity_one_at_a_time": sens,
           "downtime_in_our_logged_deals": per_deal,
           "pilot": {"status": "planned, not done", "tests": ["time to list a part and find 3 plausible buyers: today's process vs. Spare Change",
                                                          "whether the suggested floor/budget and matches make sense to a maintenance manager", "a short quote"]}}
    od = Path(a.out_dir)
    (od / "impact_model.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    usd = lambda x: f"${x:,.0f}"  # noqa: E731
    ld_derived = 4 * 12 * M["line_down_share_of_requests"]["value"]
    md = ["# Impact model: one mid-size plant (illustrative)", "",
          "`scripts/impact_model.py` → `output/impact_model.json`. Inputs are labelled **MEASURED** (read from this app's evidence files), "
          "**SOURCED** (external; links in `output/impact_sources.md`) or **ASSUMPTION** (a stated guess with a low / mid / high range). "
          "Outputs are **ONE-TIME** (value recovered and CO2e when the idle stock is sold once) or **PER YEAR**, and are never added together. "
          "Nothing here comes from a real user: see *Planned pilot* below.", "",
          "## Inputs", "", "| Input | Mid | Low – high | Type | Basis |", "|---|---|---|---|---|",
          f"| Spare-parts (MRO) inventory | {usd(ASSUMPTIONS['mro_inventory_usd']['mid'])} | {usd(ASSUMPTIONS['mro_inventory_usd']['low'])} – {usd(ASSUMPTIONS['mro_inventory_usd']['high'])} | ASSUMPTION | {ASSUMPTIONS['mro_inventory_usd']['why']} |",
          f"| Share unused 5+ years (idle) | {SOURCED['idle_share']['mid']:.0%} | {SOURCED['idle_share']['low']:.0%} – {SOURCED['idle_share']['high']:.0%} | SOURCED | {SOURCED['idle_share']['source']} |",
          f"| Annual carrying cost | {SOURCED['carrying_cost_rate']['mid']:.0%} of value | {SOURCED['carrying_cost_rate']['low']:.0%} – {SOURCED['carrying_cost_rate']['high']:.0%} | SOURCED | {SOURCED['carrying_cost_rate']['source']} |",
          f"| Scrap recovery | {SOURCED['scrap_recovery']['mid']:.0%} of value | {SOURCED['scrap_recovery']['low']:.0%} – {SOURCED['scrap_recovery']['high']:.0%} | SOURCED | {SOURCED['scrap_recovery']['source']} |",
          f"| Recovery through Spare Change | **{M['negotiated_price_over_new_price']['value']:.0%}** of new price | {M['negotiated_price_over_new_price']['range'][0]:.0%} – {M['negotiated_price_over_new_price']['range'][1]:.0%} across deals | **MEASURED** | {M['negotiated_price_over_new_price']['basis']} (`{M['negotiated_price_over_new_price']['file']}`, n={M['negotiated_price_over_new_price']['n']}) |",
          f"| Suggested ask ÷ new price (cross-check) | {M['suggested_ask_over_new_price']['value']:.0%} | {M['suggested_ask_over_new_price']['range'][0]:.0%} – {M['suggested_ask_over_new_price']['range'][1]:.0%} | **MEASURED** | {M['suggested_ask_over_new_price']['basis']} (`{M['suggested_ask_over_new_price']['file']}`, n={M['suggested_ask_over_new_price']['n']}) |",
          f"| Sell-through of idle stock | {ASSUMPTIONS['sell_through']['mid']:.0%} | {ASSUMPTIONS['sell_through']['low']:.0%} – {ASSUMPTIONS['sell_through']['high']:.0%} | ASSUMPTION | {ASSUMPTIONS['sell_through']['why']} |",
          f"| Line-down purchases filled per year | {ASSUMPTIONS['line_down_purchases_per_year']['mid']} | {ASSUMPTIONS['line_down_purchases_per_year']['low']} – {ASSUMPTIONS['line_down_purchases_per_year']['high']} | ASSUMPTION | {ASSUMPTIONS['line_down_purchases_per_year']['why']} Cross-check: {M['line_down_share_of_requests']['value']:.0%} of our demo requests are line down; at the tokenomics usage of 4 requests a month that would be ~{ld_derived:.0f} a year, so 1–3 is conservative. |",
          f"| Downtime cost per hour | {usd(DOWNTIME_RATE)} | — | SOURCED (lower bound) | Siemens TCOD 2024, lowest-cost sector (consumer goods). Higher sector rates are not used. |",
          f"| est. kg CO2e per $ of new value | {M['kg_co2e_per_dollar_of_new_value']['value']} | — | **MEASURED** | {M['kg_co2e_per_dollar_of_new_value']['basis']} (n={M['kg_co2e_per_dollar_of_new_value']['n']} listings) |",
          f"| App model cost per user per month | ${M['app_cost_per_user_month_usd']['value']:.3f} | — | **MEASURED** | {M['app_cost_per_user_month_usd']['basis']} (`{M['app_cost_per_user_month_usd']['file']}`) |",
          f"| Users per plant | {ASSUMPTIONS['users_per_plant']['mid']} | {ASSUMPTIONS['users_per_plant']['low']} – {ASSUMPTIONS['users_per_plant']['high']} | ASSUMPTION | {ASSUMPTIONS['users_per_plant']['why']} |",
          "", "## Outputs (mid case)", "", "**One-time** (when the idle stock is sold once):", "", "| Output | Value |", "|---|---|",
          f"| Idle spare-parts inventory | {usd(mid['idle_inventory_usd'])} |",
          f"| Recovered if all of it is scrapped (one-time) | {usd(mid['one_time']['recovered_if_all_scrapped_usd'])} |",
          f"| Recovered with Spare Change: sold share at the measured deal ratio, the rest still scrapped (one-time) | **{usd(mid['one_time']['recovered_with_spare_change_usd'])}** |",
          f"| Extra $ recovered vs. scrap (one-time) | **{usd(mid['one_time']['extra_recovered_vs_scrap_usd'])}** |",
          f"| est. CO2e avoided by the sold share (one-time) | **{mid['one_time']['est_kg_co2e_avoided']:,} kg** |",
          "", "**Per year:**", "", "| Output | Value |", "|---|---|",
          f"| Carrying cost of the idle stock today | {usd(mid['per_year']['carrying_cost_of_idle_stock_usd'])} / year |",
          f"| Carrying cost avoided (sold share, vs. keeping it) | **{usd(mid['per_year']['carrying_cost_avoided_usd'])} / year** |",
          f"| Buyer side: downtime value (line-down purchases only, lower bound) | **{usd(mid['per_year']['buyer_downtime_value_usd'])} / year** |",
          f"| Spare Change model cost (model calls only; hosting and support not costed) | **${mid['per_year']['app_model_cost_usd']:.2f} / year** |",
          "", f"**Reading:** at the mid case, Spare Change recovers {mid['one_time']['recovered_with_spare_change_usd'] / max(mid['one_time']['recovered_if_all_scrapped_usd'], 1):.1f}× "
          f"what scrapping does on the idle stock (one-time) and, compared with keeping it on the shelf, stops {usd(mid['per_year']['carrying_cost_avoided_usd'])} a year of carrying cost "
          f"(scrapping would stop that too, but recover only {usd(mid['one_time']['recovered_if_all_scrapped_usd'])}). On the buyer side, one line-down purchase filled from surplus "
          f"is worth at least {usd(DOWNTIME_RATE)} of avoided downtime, against ${mid['per_year']['app_model_cost_usd']:.2f} a year of model costs.",
          "", "## Our logged test deals", "",
          f"Of the {per_deal['deals_logged']} logged test deals used here (`eval_negotiation.json`; {M['deal_set']['logged'] - M['deal_set']['used']} more were excluded: {M['deal_set']['excluded']}), "
          f"**{per_deal['line_down_deals_logged']}** filled a request marked **line down**. Test deals repeat the same pairs, so no dollar total is given; "
          f"downtime is valued only in the plant model above (line-down purchases × 1 hour × $36k). "
          f"Per test deal on average: {usd(M['per_deal_average']['value_recovered_usd'])} recovered vs. {usd(M['per_deal_average']['scrap_value_usd'])} scrap, "
          f"est. {M['per_deal_average']['est_kg_co2e_avoided']} kg CO2e (n={M['per_deal_average']['n']}).",
          "", "## Scenarios", "", "| Output | All low | Mid | All high |", "|---|---|---|---|"]
    rows = [("Extra $ recovered vs. scrap (one-time)", "one_time", "extra_recovered_vs_scrap_usd", usd),
            ("est. kg CO2e avoided (one-time)", "one_time", "est_kg_co2e_avoided", lambda v: f"{v:,} kg"),
            ("Carrying cost avoided (per year)", "per_year", "carrying_cost_avoided_usd", usd),
            ("Buyer downtime value (per year, line-down only)", "per_year", "buyer_downtime_value_usd", usd),
            ("App model cost (per year)", "per_year", "app_model_cost_usd", lambda v: f"${v:,.2f}")]
    md += [f"| {label} | {f(lo[g][k])} | {f(mid[g][k])} | {f(hi[g][k])} |" for label, g, k, f in rows]
    md += ["", "\"All low\" / \"all high\" set every input to its low / high value at once (a high scrap rate lowers the benefit).", "",
           "## Sensitivity (one input at a time, everything else at mid)", "",
           "| Input | Low | Mid | High |", "|---|---|---|---|"]
    for row in sens:
        def cell(level):
            r = row[level]
            v = r["value"]
            vs = f"{v:.0%}" if isinstance(v, float) and v < 1 else (usd(v) if v >= 1000 else str(v))
            if row["input"].startswith("Line-down"):
                return f"{vs}: downtime {usd(r['per_year']['buyer_downtime_value_usd'])}/yr"
            return f"{vs}: extra {usd(r['one_time']['extra_recovered_vs_scrap_usd'])} once · carrying {usd(r['per_year']['carrying_cost_avoided_usd'])}/yr"
        md.append(f"| {row['input']} | {cell('low')} | {cell('mid')} | {cell('high')} |")
    md += ["", "## Caveats", "",
           "- Illustrative for one plant; inventory size, sell-through and line-down purchases are assumptions, shown with ranges.",
           "- Recovery ratios are measured on our synthetic catalog (real part numbers and list prices, made-up companies and asks).",
           "- CO2e comes from the app's `get_impact_estimate`: cradle-to-gate factors × a conservative 0.5 reuse credit; shipping not subtracted; chemicals excluded.",
           "- Downtime uses $36k/hr, the lowest sector rate in Siemens TCOD 2024, only for line-down purchases, 1 hour each: a lower bound.",
           "", "## Planned pilot (not done yet)", "",
           "No real user has tried Spare Change yet. A planned session with a plant maintenance or MRO manager would test:",
           "- **Time** to list one surplus part and find 3 plausible buyers: their current process vs. Spare Change.",
           "- **Trust:** whether the suggested floor / budget, the compatibility matches and the compliance checks make sense to them.",
           "- **A short quote** about the experience.", "",
           "Until then, the only timing evidence is the author's own timed test (`output/timed_test_template.md`), labelled as such. "
           "No user quotes or feedback appear anywhere in this project."]
    (od / "impact_model.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Saved {od / 'impact_model.json'} and .md · mid: extra {usd(mid['one_time']['extra_recovered_vs_scrap_usd'])} one-time, "
          f"carrying {usd(mid['per_year']['carrying_cost_avoided_usd'])}/yr, downtime {usd(mid['per_year']['buyer_downtime_value_usd'])}/yr, "
          f"model ${mid['per_year']['app_model_cost_usd']}/yr")
    return 0


if __name__ == "__main__":
    sys.exit(main())
