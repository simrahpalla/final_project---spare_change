r"""Phase 10 impact consistency check: no model calls, scratch databases only.

    .venv\Scripts\python.exe scripts\check_impact.py

Writes output/impact_check.json and output/impact_check.md (PASS/FAIL per check).
"""

import asyncio
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "output"
sys.stdout.reconfigure(encoding="utf-8")
TMP = Path(tempfile.mkdtemp(prefix="sx_chk_"))
DB = TMP / "w.db"
shutil.copyfile(REPO / "data" / "exchange.db", DB)
os.chmod(DB, 0o600)
os.environ.update(SURPLUS_DB=str(DB), SURPLUS_ROLE="system", SURPLUS_AUDIT=str(TMP / "audit.json"))
sys.path[:0] = [str(REPO / "mcp_server"), str(REPO / "backend")]
import server  # noqa: E402

checks = []


def check(item, name, ok, detail):
    checks.append({"item": item, "check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {item}. {name}: {detail}")


def rows(sql, *a):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    r = con.execute(sql, a).fetchall()
    con.close()
    return r


# ---------------------------------------------------------------- 1. hand-computed CO2e
CREDIT = 0.5
hand = [(9, "steel part: 20 × Bearing 6312-2Z/C3", 1.7 * 20 * 1.95 * CREDIT, "1.7 kg × 20 × 1.95 kg CO2e/kg × 0.5"),
        (18, "motor: 2 × Servo motor A06B-0235-B605", 18.0 * 2 * 1.95 * CREDIT, "18 kg × 2 × 1.95 kg CO2e/kg (steel on total weight) × 0.5"),
        (2, "PLC CPU: 2 × 1756-L61", 2 * 14 * CREDIT, "2 units × 14 kg CO2e/unit × 0.5 (weight not used)")]
for lid, what, expect, formula in hand:
    got = server.get_impact_estimate(lid)["est_kg_co2e_avoided"]
    check(1, f"listing {lid}, {what}", abs(got - round(expect, 1)) < 0.05, f"hand {formula} = {expect:.1f} kg; app {got} kg")
fam = rows("SELECT family, kg_co2e_per_kg, kg_co2e_per_unit FROM carbon_factors")
both = [f["family"] for f in fam if f["kg_co2e_per_kg"] is not None and f["kg_co2e_per_unit"] is not None]
per_unit = [f["family"] for f in fam if f["kg_co2e_per_unit"] is not None]
check(1, "electronics use the per-unit factor only (no weight term)", not both,
      f"{len(per_unit)} per-unit families ({', '.join(per_unit)}) have kg_co2e_per_kg NULL; code uses per-unit × qty when set")
# a per-unit estimate must not change with weight
con = sqlite3.connect(DB)
con.execute("UPDATE part_catalog SET weight_kg = weight_kg * 10 WHERE part_number='1756-L61'")
con.commit()
con.close()
check(1, "per-unit estimate ignores weight (weight ×10 on 1756-L61)", server.get_impact_estimate(2)["est_kg_co2e_avoided"] == 14.0,
      f"still {server.get_impact_estimate(2)['est_kg_co2e_avoided']} kg")
con = sqlite3.connect(DB)
con.execute("UPDATE part_catalog SET weight_kg = weight_kg / 10 WHERE part_number='1756-L61'")
con.commit()
con.close()
allco2 = []
for r in rows("SELECT l.id, l.qty, p.part_number, p.family, p.weight_kg, p.new_price FROM listings l JOIN part_catalog p ON p.part_number=l.part_number"):
    e = server.get_impact_estimate(r["id"])
    if e["est_kg_co2e_avoided"] is not None:
        allco2.append({"listing": r["id"], "part": r["part_number"], "family": r["family"], "qty": r["qty"], "weight_kg": r["weight_kg"],
                       "kg_co2e": e["est_kg_co2e_avoided"], "per_unit": round(e["est_kg_co2e_avoided"] / r["qty"], 1)})
big = [x for x in allco2 if x["per_unit"] > 50]  # > 50 kg CO2e per unit (after the reuse credit) is checked by hand
check(1, "no implausibly large figure", all(x["per_unit"] <= 2 * x["weight_kg"] * 1.95 * CREDIT + 0.1 or x["family"] in per_unit for x in allco2),
      f"largest per unit: {max(allco2, key=lambda x: x['per_unit'])}; over 50 kg/unit: "
      + ("; ".join(f"listing {x['listing']} {x['part']} {x['per_unit']} kg/unit ({x['weight_kg']} kg × 1.95 × 0.5, plausible for a {x['family']})" for x in big) or "none"))

# ---------------------------------------------------------------- 2. factors and URLs vs impact_research.md
research = (REPO / "impact_research.md").read_text(encoding="utf-8")
rurls = set(re.findall(r"https?://[^\s)\]]+", research))
expect_factor = {"kg": {1.95, 1.86}, "unit": {14.0, 12.4}}
bad = []
for f in rows("SELECT * FROM carbon_factors"):
    urls = re.findall(r"https?://[^\s)\];,]+", f["source"] + " " + (f["notes"] or ""))
    missing = [u for u in urls if u.rstrip(".") not in rurls]
    if not urls or missing:
        bad.append(f"{f['family']}: url not in research {missing or 'none'}")
    if f["kg_co2e_per_kg"] is not None and f["kg_co2e_per_kg"] not in expect_factor["kg"]:
        bad.append(f"{f['family']}: {f['kg_co2e_per_kg']}/kg")
    if f["kg_co2e_per_unit"] is not None and not (12.0 <= f["kg_co2e_per_unit"] <= 15.0):
        bad.append(f"{f['family']}: {f['kg_co2e_per_unit']}/unit outside research's 12–15")
check(2, "every factor and source URL matches impact_research.md", not bad,
      "; ".join(bad) or f"{len(fam)} families: steel 1.95/kg, cast iron 1.86/kg (research §2), PLC CPU 14/unit and modules 12.4/unit "
      "(research: 12–15 kg per compact CPU), every URL found in impact_research.md")
check(2, "disposal factor = $242 per drum ÷ ~180 kg", all(abs(f["disposal_cost_per_kg"] - 242 / 180) < 0.01 for f in rows("SELECT * FROM carbon_factors") if f["family"] in ("Chemical", "Lubricant")),
      "1.34 $/kg = 242 / 180 for Chemical and Lubricant")
chem = rows("SELECT l.id FROM listings l JOIN part_catalog p ON p.part_number=l.part_number WHERE p.category='chemical'")
ce = [server.get_impact_estimate(r["id"]) for r in chem]
check(2, "chemicals show disposal avoided, never CO2", all(e["est_kg_co2e_avoided"] is None for e in ce) and any(e["est_hazardous_disposal_avoided"] for e in ce),
      f"{len(ce)} chemical listings: CO2 None for all; disposal shown for {sum(1 for e in ce if e['est_hazardous_disposal_avoided'])} "
      "(hazardous or expiring within 12 months)")
src = (OUT / "impact_sources.md").read_text(encoding="utf-8")
# sources added after impact_research.md, each opened and checked on 26 Oct 2026 (Phase 11 final edits)
ADDED = {"https://www.rockwellautomation.com/en-us/products/details.1785-L80E.html": "PLC-5 discontinued 31 Jul 2017",
         "https://www.rockwellautomation.com/en-us/products/hardware/programmable-controllers/slc-500-controllers.html": "SLC 5/01-5/03 discontinued"}
urls = re.findall(r"https?://[^\s)\]]+", src)
missing = [u for u in urls if u not in rurls and u not in ADDED]
added = [ADDED[u] for u in urls if u in ADDED]
check(2, "every URL in impact_sources.md is in impact_research.md or a checked addition", not missing,
      f"missing: {missing}" if missing else f"all present; checked additions: {'; '.join(added)}")

# ---------------------------------------------------------------- 3. one function everywhere; board total = sum of deals; reset
code = (REPO / "mcp_server" / "server.py").read_text(encoding="utf-8")
agents = (REPO / "backend" / "agents.py").read_text(encoding="utf-8")
model_src = (REPO / "scripts" / "impact_model.py").read_text(encoding="utf-8")
fe = "".join(p.read_text(encoding="utf-8") for p in (REPO / "frontend" / "src").rglob("*.tsx"))
uses = {"impact strip (seller run → get_impact_estimate)": '"get_impact_estimate", listing_id=listing_id' in agents,
        "deal card": "imp = get_impact_estimate(d[\"listing_id\"], price=d[\"price\"], qty=d[\"qty\"])" in code,
        "Marketplace summary": "deal_impacts = [get_impact_estimate(" in code,
        "impact_model.json": "server.get_impact_estimate(" in model_src,
        "frontend does no CO2 maths": not re.search(r"1\.95|1\.86|12\.4|reuse_credit\s*\*|\*\s*0\.5", fe)}
check(3, "the same function behind strip, deal card, Marketplace and impact_model", all(uses.values()), ", ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in uses.items()))
con = sqlite3.connect(DB)
picks = [(1, 1, 1300.0, 3), (9, None, 30.0, 20), (15, None, 210.0, 2)]  # CPU, bearing, chemical
for i, (lid, nid, price, qty) in enumerate(picks, start=1):
    nid = nid or con.execute("SELECT id FROM needs LIMIT 1").fetchone()[0]
    con.execute("INSERT INTO deals (negotiation_id, listing_id, need_id, price, qty, status, created_at) VALUES (?,?,?,?,?, 'approved', '2026-10-26')",
                (900000 + i, lid, nid, price, qty))
con.commit()
con.close()
board = server.get_marketplace_board()["impact"]
singles = [server.get_impact_estimate(lid, price=p, qty=q) for lid, _, p, q in picks]
sums = {k: round(sum(s.get(k) or 0 for s in singles), 2) for k in ("value_recovered", "est_kg_co2e_avoided", "est_hazardous_disposal_avoided")}
check(3, "Marketplace total = sum of the individual deals (3 approved deals on a scratch DB)",
      board["deals"] == 3 and all(abs(board[k] - v) < 0.01 for k, v in sums.items()),
      f"board {{$ {board['value_recovered']}, {board['est_kg_co2e_avoided']} kg, $ {board['est_hazardous_disposal_avoided']} disposal}} = "
      f"sum {{$ {sums['value_recovered']}, {sums['est_kg_co2e_avoided']} kg, $ {sums['est_hazardous_disposal_avoided']} disposal}}")
import main  # noqa: E402  (backend; uses the scratch DB and audit file from the env above)
main.session_impact[1] = server.get_impact_estimate(1)
main.session_impact[9] = server.get_impact_estimate(9)
before = (len(main.session_impact), server.get_marketplace_board()["impact"]["deals"])
asyncio.run(main.reset())
after = (len(main.session_impact), server.get_marketplace_board()["impact"]["deals"])
check(3, "Reset demo clears impact totals", after == (0, 0),
      f"before reset: {before[0]} session impacts, {before[1]} approved deals on the board; after /api/reset: {after[0]} and {after[1]}")

# ---------------------------------------------------------------- 4, 5. impact_model.json: downtime and labels
im = json.loads((OUT / "impact_model.json").read_text(encoding="utf-8"))
txt = (OUT / "impact_model.json").read_text(encoding="utf-8") + (OUT / "impact_model.md").read_text(encoding="utf-8")
dd = im["downtime_in_our_logged_deals"]
check(4, "downtime only for line-down deals, $36k/hr lower bound", im["sourced"]["downtime_cost_per_hour"]["value"] == 36000
      and "downtime_value_lower_bound_usd" not in dd and dd["line_down_deals_logged"] < dd["deals_logged"],
      f"{dd['line_down_deals_logged']} of {dd['deals_logged']} logged deals were line down (count only, no summed $); "
      f"plant model: {im['assumptions']['line_down_purchases_per_year']['mid']} line-down purchase/yr × $36k")
check(4, "no $2.3M or $150k downtime rate in the model", not re.search(r"2\.3\s?M|2,300,000|2\.3 million|150,000|150k|150000", txt), "none found")
mid = im["mid_scenario"]
check(5, "one-time and per-year outputs kept apart and labelled", set(mid) == {"idle_inventory_usd", "one_time", "per_year"}
      and "never added together" in txt and "(one-time)" in txt and "/ year" in txt,
      f"one_time: {list(mid['one_time'])}; per_year: {list(mid['per_year'])}; UI $ recovered labelled 'one-time' (strip, deal card, Marketplace, rail)")
check(5, "UI labels $ recovered as one-time", fe.count("one-time") >= 4, f"{fe.count('one-time')} labels in the frontend")

# ---------------------------------------------------------------- 6. measured inputs come from the evidence files
ev = TMP / "ev"
ev.mkdir()
for n in ("phase3_stress.json", "eval_negotiation.json", "tokenomics.json"):
    shutil.copyfile(OUT / n, ev / n)
tok = json.loads((ev / "tokenomics.json").read_text(encoding="utf-8"))
orig_cost = tok["cost_per_user_month_usd"]
tok["cost_per_user_month_usd"] = orig_cost * 10
(ev / "tokenomics.json").write_text(json.dumps(tok), encoding="utf-8")
neg = json.loads((ev / "eval_negotiation.json").read_text(encoding="utf-8"))
first = next(r for r in neg["logged_negotiations"] if r.get("price"))
first["price"] = first["price"] * 2
(ev / "eval_negotiation.json").write_text(json.dumps(neg), encoding="utf-8")
(TMP / "o").mkdir()
py = REPO / ".venv" / "Scripts" / "python.exe"
subprocess.run([str(py if py.exists() else sys.executable), str(REPO / "scripts" / "impact_model.py"), "--evidence-dir", str(ev), "--out-dir", str(TMP / "o")],
               check=True, capture_output=True)
alt = json.loads((TMP / "o" / "impact_model.json").read_text(encoding="utf-8"))
a0, a1 = im["mid_scenario"], alt["mid_scenario"]
check(6, "change an evidence file → the output changes", a1["per_year"]["app_model_cost_usd"] != a0["per_year"]["app_model_cost_usd"]
      and a1["one_time"]["extra_recovered_vs_scrap_usd"] != a0["one_time"]["extra_recovered_vs_scrap_usd"],
      f"tokenomics cost/user-month ${orig_cost} → ${orig_cost * 10:.3f}: model cost ${a0['per_year']['app_model_cost_usd']}/yr → ${a1['per_year']['app_model_cost_usd']}/yr; "
      f"one deal price ×2 in eval_negotiation: recovery ratio {im['measured']['negotiated_price_over_new_price']['value']} → "
      f"{alt['measured']['negotiated_price_over_new_price']['value']}, extra recovered ${a0['one_time']['extra_recovered_vs_scrap_usd']:,} → ${a1['one_time']['extra_recovered_vs_scrap_usd']:,} (temp copies; real files untouched)")

# ---------------------------------------------------------------- 7, 8. text searches
SKIP = {".venv", "node_modules", "dist", ".git", "__pycache__", "evidence_logs", "screenshots"}
EXCL = {"AI_prompts.md", "impact_research.md", "impact_check.md", "impact_check.json", "check_impact.py", "BUILD_PLAN.md", "CLAUDE.md"}
files = [p for p in REPO.rglob("*") if p.is_file() and not (SKIP & set(p.parts)) and p.name not in EXCL
         and p.suffix in (".md", ".tsx", ".ts", ".py", ".html", ".json", ".txt")]


def grep(pattern):
    hits = []
    for p in files:
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(pattern, line, re.I):
                    hits.append(f"{p.relative_to(REPO).as_posix()}:{i}: {line.strip()[:140]}")
        except (UnicodeDecodeError, OSError):
            pass
    return hits


quotes = grep(r"testimonial|\"[^\"]{0,80}\" ?[—-] ?(plant|maintenance|mro|manager|engineer)|users? (said|told|loved|report(ed)?)|"
              r"pilot (showed|found|participants|user said)|in our pilot|customers? (say|said)|feedback from")
allowed_q = [h for h in quotes if re.search(r"no user (quotes|feedback)|not (a|an) (user|independent)|no real user|planned|no .*feedback", h, re.I)]
check(7, "no invented user quotes, testimonials or pilot claims", len(quotes) == len(allowed_q),
      f"{len(quotes)} hits, all disclaimers: " + " | ".join(allowed_q[:6]) if quotes else "no hits")
dont = {"MRO market size": r"MRO market (size|is worth)|\$\d+(\.\d+)? ?(billion|bn|B) (industrial )?MRO", "50–60% obsolete": r"50\s?[–-]\s?60\s?%[^|]{0,60}(obsolete|inactive|MRO|inventory)",
        "S7-300 installed count": r"(million|\d[\d,]+) (installed )?S7-300", "$2.3M/hr": r"2\.3\s?M|2\.3 million", "$150k/hr": r"\$?150,000 an hour|\$?150k/hr"}
for name, pat in dont.items():
    hits = [h for h in grep(pat) if "impact_sources.md" not in h or not re.search(r"^output/impact_sources\.md:\d+: - \*\*No", h)]
    check(8, f"don't-claim: {name}", not hits, "; ".join(hits[:4]) or "only in the 'Not used' list of impact_sources.md")

shutil.rmtree(TMP, ignore_errors=True)
res = {"passed": sum(c["result"] == "PASS" for c in checks), "total": len(checks), "checks": checks, "all_listings_co2": allco2}
(OUT / "impact_check.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
md = ["# Phase 10 impact consistency check", "", f"`scripts/check_impact.py` (no model calls, scratch database). **{res['passed']} / {res['total']} PASS.**", "",
      "| # | Check | Result | Detail |", "|---|---|---|---|"]
md += [f"| {c['item']} | {c['check']} | {c['result']} | {c['detail'].replace('|', '/')} |" for c in checks]
md += ["", "## est. CO2e for every listing (app values)", "", "| Listing | Part | Family | Qty | kg/unit | kg CO2e | per unit |", "|---|---|---|---|---|---|---|"]
md += [f"| {x['listing']} | {x['part']} | {x['family']} | {x['qty']} | {x['weight_kg']} | {x['kg_co2e']} | {x['per_unit']} |" for x in allco2]
(OUT / "impact_check.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(f"\n{res['passed']} / {res['total']} PASS → output/impact_check.md")
sys.exit(0 if res["passed"] == res["total"] else 1)
