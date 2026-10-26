r"""Run the agents from the command line (the Phase 3 checkpoint).

From the repo folder:
    .venv\Scripts\python.exe backend\run_flow.py --listing 1          # seeded listing: listing -> compliance -> matches -> price
    .venv\Scripts\python.exe backend\run_flow.py --text "3x SKF 6312 brgs NIB $50 ea" --seller 9
    .venv\Scripts\python.exe backend\run_flow.py --negotiate 1 1      # listing 1 vs need 1: seller agent vs buyer agent
    .venv\Scripts\python.exe backend\run_flow.py --need "need 4x S7-300 32pt DI cards asap" --buyer 20 --max 180
    .venv\Scripts\python.exe backend\run_flow.py --need-id 1         # re-match an existing need (reverse direction)
    .venv\Scripts\python.exe backend\run_flow.py --reset --listing 22 # reset the working DB first

Prints each step with its tokens and cost. For seeded listings it also scores the listing agent and the
matching agent against data/answer_keys.json. Every run is saved to output/runs/<run_id>.json.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from agents import Exchange  # noqa: E402

RUNS_DIR = config.OUTPUT_DIR / "runs"
KEYS = json.loads((config.DATA_DIR / "answer_keys.json").read_text(encoding="utf-8"))


def score_against_keys(result: dict, listing_id: int) -> dict | None:
    key = next((k for k in KEYS["listings"] if k["listing_id"] == listing_id), None)
    if not key:
        return None
    out = {}
    draft = next((s["draft"] for s in result["steps"] if s["step"] == "listing_agent"), None)
    if draft:
        fields = ["part_number", "qty", "condition", "asking_price", "expiry_date", "sds_available"]
        exp = key["expected"]
        got = {f: draft.get(f) for f in fields}
        if exp.get("expiry_date") and not got["expiry_date"] and draft.get("manufacture_date"):
            got["expiry_date"] = "(derived by server from manufacture date)"
            got_ok = {f: got[f] == exp[f] or f == "expiry_date" for f in fields}
        else:
            got_ok = {f: got[f] == exp[f] for f in fields}
        out["listing_fields"] = f"{sum(got_ok.values())}/{len(fields)} correct"
        out["field_misses"] = {f: {"got": got[f], "expected": exp[f]} for f, ok in got_ok.items() if not ok}
    ranked = next((s.get("ranked") for s in result["steps"] if s["step"] == "matching"), None)
    if key["expected_first_buyer"] is not None and ranked is not None:
        out["top_buyer_correct"] = bool(ranked) and ranked[0]["buyer_id"] == key["expected_first_buyer"]
        out["expected_first_buyer"] = key["expected_first_buyer"]
    if key["is_bad_record"]:
        bad = next(b for b in KEYS["bad_records"] if b["listing_id"] == listing_id)
        out["expected_outcome"] = bad["expected_outcome"]
    return out


def money(x) -> str:
    return "—" if x is None else f"${x:,.2f}"


def print_result(r: dict) -> None:
    print(f"\n=== {r['kind']} · run {r['run_id']} · {r['subject']} ===")
    for s in r["steps"]:
        name, status = s["step"], s["status"]
        if name == "listing_agent":
            d = s["draft"]
            print(f"  LISTING     {d['part_number']} · qty {d['qty']} · {d['condition']} · ask {money(d['asking_price'])}"
                  f" · expiry {d['expiry_date'] or d['manufacture_date'] and 'mfd ' + d['manufacture_date'] or '—'}"
                  f" · SDS {d['sds_available']} · confidence {d['confidence']:.2f}")
            if d["notes"]:
                print(f"              note: {d['notes']}")
        elif name == "prescreen":
            print(f"  PRESCREEN   {status}" + (f" ({s['rule']})" if status == "blocked" else ""))
        elif name == "save":
            print(f"  SAVE        {status}" + (f" listing #{s['listing_id']}" if "listing_id" in s else ""))
        elif name == "compliance":
            print(f"  COMPLIANCE  {status.upper()}" + (f": {'; '.join(s.get('reasons', []))}" if s.get("reasons") else
                                                     f" ({s.get('rules')}; guard {s.get('guard')})" if status == "allowed" else ""))
        elif name == "activate":
            print(f"  ACTIVATE    {status}")
        elif name == "matching":
            if status == "no_candidates":
                print(f"  MATCHES     none: {s['note']}")
            else:
                print(f"  MATCHES     {s['candidates']} pre-filtered candidates -> top {len(s['ranked'])}"
                      f" (saved {s['saved']}, rejected by code {len(s['rejected'])})")
                for i, m in enumerate(s["ranked"], 1):
                    if s.get("direction") == "buyer_to_seller":
                        print(f"              {i}. [{m['score']}] listing #{m['listing_id']} {m['part_number']} from "
                              f"{m['seller_name']}: {m['reason']}")
                        continue
                    print(f"              {i}. [{m['score']}] {m['buyer_name']} (#{m['buyer_id']}"
                          + (f", need #{m['need_id']}" if m["need_id"] else "") + f"): {m['reason']}")
        elif name == "pricing":
            print(f"  PRICE       ask {money(s['ask'])} · floor suggestion {money(s['floor_suggestion'])} (seller only)"
                  f" · new {money(s['new_price'])} · scrap {money(s['scrap_value'])}" + (" · clamped" if s["clamped"] else ""))
            print(f"              {s['rationale']}")
        elif name == "need_agent":
            d = s["draft"]
            print(f"  NEED        {d['part_number'] or d['family']} · platform {d['platform']} · qty {d['qty']} · {d['urgency']}"
                  f" · confidence {d['confidence']:.2f}")
        elif name == "alerts":
            print(f"  ALERTS      {s['sent']} sent to companies {s['companies']} · {s['pairs']} pair(s) >= {s['threshold']}"
                  f" · {s['duplicates']} duplicate(s) skipped (code, no model)")
        elif name in ("rules", "guard", "prefilter", "listing", "need"):
            continue  # detail for the UI's activity rail; the CLI shows them via COMPLIANCE / MATCHES
        elif name == "impact":
            co2 = s.get("est_kg_co2e_avoided")
            haz = s.get("est_hazardous_disposal_avoided")
            print(f"  IMPACT      recovers {money(s.get('value_recovered'))} vs {money(s.get('scrap_value_total'))} scrap · "
                  f"{s.get('kg_kept_out_of_scrap')} kg kept out of scrap · est. {co2} kg CO2e"
                  + (f" · est. {money(haz)} hazardous disposal avoided" if haz else "")
                  )
        elif name == "outreach":
            print(f"  OUTREACH    to {s['to']}: \"{s['subject']}\"")
            for line in s["body"].splitlines():
                print(f"              {line}")
        elif name == "open":
            print(f"  OPEN        negotiation #{s.get('negotiation_id')} · qty {s.get('qty')} · max {s.get('max_rounds')} offers"
                  if status == "done" else f"  OPEN        refused: {s['result'].get('message')}")
        elif name.endswith("_turn"):
            side = name.split("_")[0].upper()
            what = s["action"] if status == "moved" else "NO VALID MOVE"
            price = f" {money(s['price'])}" if s.get("action") in ("offer", "accept") else ""
            print(f"  {side:<6} r{s['round']}  {what}{price}" + (f"  \"{s['message']}\"" if s.get("message") else ""))
        elif name == "deal":
            d = s["deal"]
            print(f"  DEAL        #{d['id']}: {d['qty']} x {money(d['price'])} -> pending HUMAN approval")
        else:
            print(f"  {name.upper():<11} {status} {s.get('detail') or s.get('result') or ''}")
    t = r["totals"]
    print(f"  OUTCOME     {r['outcome']}")
    print(f"  TOKENS      {t['requests']} requests · input {t['input_tokens']} · cached {t['cached_tokens']} · "
          f"output {t['output_tokens']} · cost ${t['cost_usd']:.6f}")
    for a in r["agent_calls"]:
        print(f"              {a['agent']:<18} {a['requests']} req · in {a['input_tokens']} · cached {a['cached_tokens']}"
              f" · out {a['output_tokens']} · ${a['cost_usd']:.6f}")
    if r.get("answer_key_check"):
        print(f"  ANSWER KEY  {json.dumps(r['answer_key_check'])}")


async def main(args) -> int:
    async with Exchange() as ex:
        if args.negotiate:
            r = await ex.run_negotiation(*args.negotiate)
        elif args.need or args.need_id:
            r = await ex.run_need_flow(text=args.need, buyer_id=args.buyer, need_id=args.need_id, max_price=args.max)
        else:
            r = await ex.run_seller_flow(listing_id=args.listing, text=args.text, seller_id=args.seller)
            if args.listing:
                r["answer_key_check"] = score_against_keys(r, args.listing)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{r['run_id']}.json").write_text(json.dumps(r, indent=2, default=str), encoding="utf-8")
    print_result(r)
    print(f"\nSaved output/runs/{r['run_id']}.json")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--listing", type=int, help="run the seller flow on a seeded listing")
    g.add_argument("--text", help="run the seller flow on newly pasted text (needs --seller)")
    g.add_argument("--need", help="run the buyer (wanted) flow on a new post (needs --buyer)")
    g.add_argument("--need-id", type=int, help="re-run reverse matching for an existing need")
    g.add_argument("--negotiate", type=int, nargs=2, metavar=("LISTING", "NEED"), help="negotiate listing vs need")
    p.add_argument("--seller", type=int, help="seller company id for --text")
    p.add_argument("--buyer", type=int, help="buyer company id for --need")
    p.add_argument("--max", type=float, help="buyer's private max price per unit for --need")
    p.add_argument("--reset", action="store_true", help="reset the working database from the original first")
    a = p.parse_args()
    if a.text and not a.seller:
        p.error("--text needs --seller")
    if a.need and not a.buyer:
        p.error("--need needs --buyer")
    if a.reset:
        sys.path.insert(0, str(config.REPO_DIR / "scripts"))
        from reset_db import reset  # noqa: PLC0415  (also clears the WAL files)
        reset(config.ORIGINAL_DB, config.WORKING_DB)
        print("Working database reset from data/exchange.db")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(main(a)))
