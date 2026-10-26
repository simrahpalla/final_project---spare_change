r"""Build output/evidence_index.md (report section -> evidence files -> screenshots -> headline numbers) from the JSON
evidence, and check that the evidence is consistent.

    .venv\Scripts\python.exe scripts\build_evidence_index.py

Checks (exit 1 if any fails):
  - tokenomics: per-user cost = sum of (assumed runs x measured average); 100 / 10,000-user totals follow from it;
    the pre-filter experiment reports both tokens and accuracy
  - safety: attacks, malfunction and overspending each have at least one passing test and a screenshot
  - cost check by hand matched
  - the same metric is identical in every JSON file that reports it
  - the prose docs (harness.md, evidence_audit.md, READMEs) state the same numbers as the JSON
Historical records (phase3_stress_before_fixes.*, phase3_history.md, phase6_decisions.md, phase6_morning_summary.md, AI_prompts.md) keep the
numbers of their time on purpose and are not checked.
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "output"
SHOTS = {p.name for p in (OUT / "screenshots").glob("*")}


def load(name):
    p = OUT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


imp = load("impact_model.json")
tok, pre, safety, em, en = load("tokenomics.json"), load("prefilter_experiment.json"), load("safety_tests.json"), load("eval_matching.json"), load("eval_negotiation.json")
suite, p5, two, smoke, rev = load("negotiation_suite.json"), load("phase5_stress.json"), load("two_sided_test.json"), load("mcp_smoke.json"), load("eval_reverse.json")
cost, conc, p3, mc, pair, extra = load("cost_check.json"), load("concurrency_test.json"), load("phase3_stress.json"), load("match_check_test.json"), load("eval_demo_pair.json"), load("safety_extra.json")

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def frac(rows, key="result"):
    return f"{sum(1 for r in rows if r[key] == 'PASS')}/{len(rows)}"


# ---------------------------------------------------------------- canonical numbers (from the JSON files)
S6 = suite.get("checks", [])
C = {
    "phase6_suite": frac(S6),
    "auto_e2e": frac([c for c in S6 if c["section"] == 1]),
    "phase5_stress": frac(p5.get("checks", [])),
    "two_sided": f"{two.get('passed')}/{two.get('cases')}",
    "mcp_smoke": f"{sum(1 for c in smoke.get('calls', []) if c['passed'])}/{len(smoke.get('calls', []))}",
    "mcp_tools": len({c["tool"] for c in smoke.get("calls", [])}),
    "reverse": f"{rev.get('passed')}/{rev.get('cases')}",
    "match_check": f"{mc.get('passed')}/{mc.get('cases')}",
    "safety": f"{sum(v['pass'] for v in safety.get('summary', {}).values())}/{sum(v['tests'] for v in safety.get('summary', {}).values())}",
    "safety_extra": f"{extra.get('passed')}/{extra.get('tests')}",
    "per_user_month": tok.get("cost_per_user_month_usd"),
    "phase3_table": frac(p3.get("table", [])),
    "demo_pair": (pair or {}).get("deals_closed"),
}
conc_rows = [r for r in (conc.get("results") or conc.get("runs") or []) if isinstance(r, dict)]

# ---------------------------------------------------------------- 1. tokenomics arithmetic
if tok:
    unit = {"seller_flows": tok["per_run"]["seller_flow"]["avg_cost_usd"], "buy_requests": tok["per_run"]["buy_request"]["avg_cost_usd"],
            "negotiations": tok["per_run"]["negotiation"]["avg_cost_usd"]}
    expect = round(sum(tok["assumptions_per_user_month"][k] * unit[k] for k in unit), 5)
    check("tokenomics: per-user cost = assumed runs × measured averages", abs(expect - tok["cost_per_user_month_usd"]) < 1e-9,
          f"{tok['assumptions_per_user_month']} → ${expect}")
    for s in tok["at_scale"]:
        check(f"tokenomics: {s['users']:,} users = per-user × users", abs(s["per_month_usd"] - round(tok["cost_per_user_month_usd"] * s["users"], 2)) < 0.006
              and abs(s["per_year_usd"] - round(tok["cost_per_user_month_usd"] * s["users"] * 12, 2)) < 0.006,
              f"${s['per_month_usd']:,}/month, ${s['per_year_usd']:,}/year")
    check("tokenomics: assumptions are stated in the file", bool(tok.get("assumptions_per_user_month")))
check("pre-filter experiment reports tokens AND accuracy", all(k in pre.get("with_prefilter", {}) and k in pre.get("no_prefilter", {})
      for k in ("avg_total_tokens", "avg_cost_usd", "top1_correct", "ungrounded_picks")))

# ---------------------------------------------------------------- 2. safety coverage
for cat in ("attack", "malfunction", "overspending"):
    tests = [t for t in safety.get("tests", []) if t["category"] == cat]
    shots = sorted({t["screenshot"].split(" ")[0].replace("+", "").strip() for t in tests if t.get("screenshot")})
    check(f"safety: {cat} has a passing test", any(t["result"] == "PASS" for t in tests), f"{sum(t['result'] == 'PASS' for t in tests)}/{len(tests)} pass")
    check(f"safety: {cat} has a screenshot that exists", shots and all(s in SHOTS for s in shots), ", ".join(shots))

# ---------------------------------------------------------------- 3. cost check + cross-file equality
check("cost check by hand: one seller run, one negotiation and every tokenomics run match", cost.get("all_match"))
if cost and tok:
    src = cost["tokenomics_sources"]
    check("tokenomics averages = cost_check means (seller flow, buy request)",
          all(src[k].get("average_matches") for k in ("seller_flow", "buy_request")))
cov = next((r for r in p3.get("table", []) if r["test"].startswith("Coverage")), {})
m = re.search(r"top-1 (\d+/\d+); top-3 (\d+/\d+)", cov.get("evidence", ""))
if m and em:
    check("eval_matching forward top-1/top-3 = phase3_stress coverage", em["forward_matching"]["top1"] == m.group(1) and em["forward_matching"]["top3"] == m.group(2),
          f"{m.group(1)}, {m.group(2)}")
check("eval_matching reverse = eval_reverse.json", em.get("reverse_matching", {}).get("correct") == C["reverse"], C["reverse"])
check("eval_negotiation Phase 6 checks = negotiation_suite.json", len(en.get("phase6_checks", [])) == len(S6))
check("safety_tests summary = its own tests", C["safety"] == frac(safety.get("tests", [])), C["safety"])
if pre and tok.get("cost_cutting_experiment"):
    check("tokenomics pre-filter numbers = prefilter_experiment.json",
          tok["cost_cutting_experiment"]["with_prefilter"]["avg_total_tokens"] == pre["with_prefilter"]["avg_total_tokens"])

# ---------------------------------------------------------------- 4. prose docs say the same numbers
DOCS = ["output/harness.md", "output/evidence_audit.md", "README.md", "mcp_server/README.md"]
CLAIMS = [  # (what, regex capturing "a/b" or a number, canonical)
    ("Phase 6 suite", r"Phase 6 suite\W{0,6}\**(\d+/\d+)", C["phase6_suite"]),
    ("Phase 5 stress", r"Phase 5 stress(?: test)?\W{0,6}\**(\d+/\d+)", C["phase5_stress"]),
    ("two-sided", r"two-sided\W{0,6}\**(\d+/\d+)", C["two_sided"]),
    ("MCP smoke", r"(?:MCP )?smoke(?: test)?\W{0,6}\**(\d+/\d+)", C["mcp_smoke"]),
    ("match check", r"match check\W{0,6}\**(\d+/\d+)", C["match_check"]),
    ("safety tests", r"safety_tests\.json`?\W{0,6}\**(\d+/\d+)", C["safety"]),
    ("per user per month", r"\$(0\.0\d+)\*{0,2} per (?:active )?user per month", f"{C['per_user_month']:.3f}" if C["per_user_month"] else None),
]
for doc in DOCS:
    text = (REPO / doc).read_text(encoding="utf-8") if (REPO / doc).exists() else ""
    for what, rx, canon in CLAIMS:
        if canon is None:
            continue
        for found in re.findall(rx, text, re.I):
            same = found == canon or (what == "per user per month" and abs(float(found) - float(canon)) < 0.0015)
            if not same:
                check(f"{doc}: '{what}' says {found}", False, f"evidence says {canon}")
check("prose docs state the same numbers as the JSON evidence", not [c for c in checks if c[0].startswith(tuple(DOCS)) and not c[1]])

# ---------------------------------------------------------------- the index
t = tok.get("per_run", {})
pw, pn = pre.get("with_prefilter", {}), pre.get("no_prefilter", {})
o = en.get("overall", {})
fix = en.get("prompt_fix_effect", {})
cat = safety.get("summary", {})
shots_by_cat = {c: sorted({x["screenshot"] for x in safety.get("tests", []) if x["category"] == c and x.get("screenshot")})
                for c in ("attack", "malfunction", "overspending")}
bm = em.get("buy_requests_as_new_posts", {})
rows = [
    ("Motivation & what's new", "`README.md`, `output/harness.md` (what is reused from HW5 vs. new), `output/design.md`",
     "`phase4-sell-result`, `phase5-marketplace`, `phase6-negotiation-live`",
     "Agents do the listing, compliance, compatibility matching, pricing and negotiation; humans confirm limits and approve deals"),
    ("Agent design (incl. a real run traced)", "`output/harness.md`, `output/mcp_smoke.json` (tools by role), `output/audit_trail.json`, `output/cost_check.md` (one real seller run + one negotiation, every agent call with tokens)",
     "`phase3-run-flow`, `phase4-sell-result` (agent steps in the rail), `phase6-confirm-limit`, `phase6-negotiation-live`, `phase6-deal-approved`",
     f"MCP smoke {C['mcp_smoke']} calls, {C['mcp_tools']} tools, 5 roles; auto-negotiate end to end {C['auto_e2e']}"),
    ("Tokenomics", "`output/tokenomics.json`/`.md`, `output/cost_check.md`, `output/prefilter_experiment.json`, `output/need_post_runs.json`",
     "`phase4-sell-result` (cost meter + session budget), `phase6-negotiation-live` (cost of this negotiation)",
     (f"seller flow ${t.get('seller_flow', {}).get('avg_cost_usd', 0):.5f} (n={t.get('seller_flow', {}).get('runs')}), buy request ${t.get('buy_request', {}).get('avg_cost_usd', 0):.5f} "
      f"(n={t.get('buy_request', {}).get('runs')}), negotiation ${t.get('negotiation', {}).get('avg_cost_usd', 0):.5f} (n={t.get('negotiation', {}).get('runs')}); "
      f"**${tok.get('cost_per_user_month_usd', 0):.3f} per active user per month** (stated assumptions); "
      + ", ".join(f"{s['users']:,} users ${s['per_year_usd']:,.0f}/yr" for s in tok.get("at_scale", [])[1:])
      + f"; pre-filter: {pw.get('avg_total_tokens', 0):,} vs {pn.get('avg_total_tokens', 0):,} tokens per matching call (−{round(100 * (pre.get('token_reduction') or 0))}%), "
      f"top-1 {pw.get('top1_correct')}/{pw.get('listings')} vs {pn.get('top1_correct')}/{pn.get('listings')}; hand-priced costs match the app")),
    ("Safety: attacks", "`output/safety_tests.json` (A1–A10) ← `phase3_stress`, `phase5_stress`, `negotiation_suite`, `mcp_smoke`, `match_check_test`",
     ", ".join(f"`{s}`" for s in shots_by_cat["attack"]), f"{cat.get('attack', {}).get('pass')}/{cat.get('attack', {}).get('tests')} pass"),
    ("Safety: malfunction", "`output/safety_tests.json` (M1–M8) ← `phase3_stress`, `match_check_test`, `safety_extra`, `negotiation_suite`, `phase5_stress`",
     ", ".join(f"`{s}`" for s in shots_by_cat["malfunction"]), f"{cat.get('malfunction', {}).get('pass')}/{cat.get('malfunction', {}).get('tests')} pass"),
    ("Safety: overspending", "`output/safety_tests.json` (O1–O6) ← `safety_extra`, `phase3_stress`, `negotiation_suite`, `eval_reverse`",
     ", ".join(f"`{s}`" for s in shots_by_cat["overspending"]), f"{cat.get('overspending', {}).get('pass')}/{cat.get('overspending', {}).get('tests')} pass"),
    ("Quality: matching", "`output/eval_matching.json` ← `phase3_stress`, `eval_reverse`, `phase5_stress`, `match_check_test`, `prefilter_experiment`, `need_post_runs`",
     "`phase4-sell-result` (top buyers, fact-checked), `phase5-buy`, `phase4-matching-error` (the incident)",
     (f"forward top-1 {em.get('forward_matching', {}).get('top1')}, top-3 {em.get('forward_matching', {}).get('top3')} (labelled listings); reverse {C['reverse']}; "
      f"fact-check {C['match_check']}; symmetry max gap {em.get('symmetry', {}).get('max_gap')} (n={em.get('symmetry', {}).get('pairs')}); "
      f"{bm.get('runs')} real buy requests: {bm.get('posted_and_matched')} matched, {bm.get('posted_no_surplus_yet')} correctly 'no surplus yet', "
      f"{len(bm.get('flagged_by_guard', []))} false flag")),
    ("Quality: negotiation", "`output/eval_negotiation.json` ← `phase3_stress`, `negotiation_suite`, `eval_demo_pair`",
     "`phase6-negotiation-live`, `phase6-seller-view`, `phase6-deal-approved`",
     (f"{o.get('negotiations')} negotiations, {o.get('deals')} deals, **{o.get('limit_violations')} limit violations**, avg {o.get('avg_rounds')} rounds; "
      f"narrow-overlap deal rate {fix.get('before_phase6_fix', {}).get('deal_rate')} → {fix.get('after_phase6_fix', {}).get('deal_rate')} after the prompt fix; "
      f"featured demo pair {C['demo_pair']}")),
    ("It works / reliability", "`output/phase6_stress.md`, `output/phase5_stress.md`, `output/two_sided_test.json`, `output/concurrency_test.json`, `output/phase3_stress.md`",
     "`phase5-alert`, `phase6-approval-alert`, `phase6-deal-approved`",
     f"Phase 6 suite {C['phase6_suite']}, Phase 5 stress {C['phase5_stress']}, two-sided {C['two_sided']}, Phase 3 stress {C['phase3_table']}"),
    ("Impact", "`output/impact_model.md`/`.json` (one mid-size plant; inputs labelled measured / sourced / assumption), `output/impact_check.md` (Phase 10 consistency check), `output/impact_sources.md` "
     "(every external number, link, confidence), `carbon_factors` (sourced), `output/timed_test_template.md` (author's timed test, to fill in)",
     "`phase5-marketplace` (impact summary), `phase6-deal-approved` (impact line); to take: `phase10-impact`",
     (f"mid case: {imp.get('mid_scenario', {}).get('extra_recovered_vs_scrap_usd', 0):,} USD more than scrap, "
      f"{imp.get('mid_scenario', {}).get('carrying_cost_avoided_per_year_usd', 0):,} USD/yr carrying cost avoided, "
      f"{imp.get('mid_scenario', {}).get('buyer_downtime_value_per_year_usd', 0):,} USD/yr buyer downtime value, "
      f"est. {imp.get('mid_scenario', {}).get('est_kg_co2e_avoided', 0):,} kg CO2e, model cost "
      f"{imp.get('mid_scenario', {}).get('app_running_cost_per_year_usd', 0)} USD/yr; measured recovery "
      f"{imp.get('measured', {}).get('negotiated_price_over_new_price', {}).get('value', 0):.0%} of new price "
      f"(n={imp.get('measured', {}).get('negotiated_price_over_new_price', {}).get('n')}); **no real user yet** (pilot planned)")),
    ("Design", "`output/design.md`, `output/design/` mockups", "`phase4-*`, `phase5-*`, `phase6-*`", "Workshop style; orange Sell / blue Buy"),
]
LIMITS = [
    f"Synthetic data: 50 companies, 27 listings, 21 needs; accuracy is measured against hand-written answer keys.",
    "Every seeded need has exactly one compatible listing, so reverse matching shows correct grounding, not fine ranking; symmetry is measured on 6 pairs.",
    f"Compliance guard false positive: {len(bm.get('flagged_by_guard', []))} of {bm.get('runs')} real buy requests flagged (seeded need {', '.join(map(str, bm.get('flagged_by_guard', [])))}).",
    "Matching mix-up seen once in 15 recorded UI runs (before the fact-check); now caught by code (retry, then rules fallback).",
    "Narrow-overlap negotiations walked away before the Phase 6 'last offer' prompt fix (see the before/after rate above).",
    "Blocked moves are rare after the prompt fix; the blocked-move display is proven with a scripted rogue agent (`safety_extra.json`), not a natural run.",
    "The model call that crosses the per-run token cap is stopped but its tokens are not written to token_usage (at most one call per run).",
    "Account switching is a demo, not authentication; private limits never leave their owner's views (leak scans), and run results are owner-only since the fix found in the evidence re-runs.",
    "Per-user cost uses stated assumptions (runs per month), not measured usage.",
    "Impact: sourced carbon factors × a conservative 0.5 reuse credit on estimated shipping weights (no CO2 claim for chemicals); "
    "the plant model is illustrative, with inventory size, sell-through and line-down purchases as labelled assumptions; downtime only for line-down purchases at $36k/hr (lower bound); one-time and per-year values never summed.",
    "No real user yet: a pilot is planned; the only timing evidence will be the author's own timed test, labelled as such.",
    "`gpt-6-luna` ignores temperature (reasoning model); consistency is measured by repeat runs instead.",
]
ok = all(c[1] for c in checks)
md = ["# Evidence index", "", "Generated by `scripts/build_evidence_index.py` from the JSON evidence (regenerate everything with `scripts/run_all_evidence.py`). "
      "Every number below comes from those files; screenshots are in `output/screenshots/`.", "",
      "| Report section | Evidence files | Screenshots | Headline numbers |", "|---|---|---|---|"]
md += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
md += ["", "## Sample sizes, failures and limits (stated honestly)", ""] + [f"- {x}" for x in LIMITS]
md += ["", "## Consistency checks", "", "| Check | Result | Detail |", "|---|---|---|"]
md += [f"| {n} | {'PASS' if k else '**FAIL**'} | {d} |" for n, k, d in checks]
md += ["", f"**{sum(c[1] for c in checks)}/{len(checks)} consistency checks pass.**", "",
       "Historical records keep the numbers of their time on purpose: `phase3_stress_before_fixes.*`, `phase3_stress_pre_phase6.json` (Phase 3 as first recorded, the 'before' of the prompt-fix comparison), `phase3_stress_after_fixes.md`, "
       "`phase3_history.md`, `data_report_baseline.md`, `phase6_decisions.md`, `phase6_morning_summary.md` (its status block on top is current), `AI_prompts.md`."]
(OUT / "evidence_index.md").write_text("\n".join(md) + "\n", encoding="utf-8")
for n, k, d in checks:
    if not k:
        print("FAIL:", n, "|", d)
print(f"{sum(c[1] for c in checks)}/{len(checks)} consistency checks pass. Saved output/evidence_index.md")
sys.exit(0 if ok else 1)
