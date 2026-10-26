r"""Repeat test for the featured-account negotiation: Hartwell's SM 321 input cards (listing 13) vs Riverbend's sample
input-card request (posted on Buy with its private $180 budget). Both are featured demo accounts.

    .venv\Scripts\python.exe scripts\test_demo_pair.py [--runs 3]

Each run: reset demo -> Riverbend posts its sample request (Buy) -> Hartwell starts the negotiation -> wait -> both
approve. Checks every run ends in a deal inside both limits and that neither side's view shows the other's limit.
Writes output/eval_demo_pair.json.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from test_negotiation import KEYS, RESULTS, Backend, leak_scan  # noqa: E402

POST = KEYS["two_sided"]["buyer_posts"][0]  # Riverbend's sample request (DI cards, max $180)


async def main(runs: int) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = []
    async with Backend(8768) as b:
        for k in range(runs):
            b.account_spend()  # the reset clears token_usage
            await b.call("POST", "/api/reset")
            r = await b.flow("/api/need-flow/start", {"text": POST["text"], "buyer_id": 20, "max_price": POST["max_price"]})
            need = r.get("need_id")
            st, d = await b.start(13, need, 1)
            if st != 200:
                rows.append({"run": k + 1, "status": f"start refused: {d}"})
                continue
            nid = d["negotiation_id"]
            v = await b.wait(nid, 1)
            b.record(f"featured pair run {k + 1}", v)
            if v.get("deal"):
                await b.call("POST", f"/api/negotiations/{nid}/approve", {"company_id": 1}, viewer=1)
                await b.call("POST", f"/api/negotiations/{nid}/approve", {"company_id": 20}, viewer=20)
            sv = (await b.call("GET", f"/api/negotiations/{nid}?company_id=1", viewer=1))[1]
            bv = (await b.call("GET", f"/api/negotiations/{nid}?company_id=20", viewer=20))[1]
            rows.append({"run": k + 1, "status": v["status"], "rounds": v["rounds_used"],
                         "price": (v.get("deal") or {}).get("price"), "qty": v["qty"],
                         "offers": [(o["from_side"], o["action"], o["price"]) for o in v["offers"]],
                         "deal_status_after_approvals": (sv.get("deal") or {}).get("status"),
                         "seller_sees": sv.get("deal", {}).get("relative") if sv.get("deal") else sv.get("explanation"),
                         "buyer_sees": bv.get("deal", {}).get("relative") if bv.get("deal") else bv.get("explanation")})
            print(f"run {k + 1}: {rows[-1]['status']} in {rows[-1]['rounds']} rounds at {rows[-1]['price']} "
                  f"(seller: {rows[-1]['seller_sees']}; buyer: {rows[-1]['buyer_sees']})", flush=True)
        await leak_scan(b, 7)
    deals = sum(1 for r in rows if r.get("status") == "agreed" and r.get("deal_status_after_approvals") == "approved")
    inside = all(122 <= r["price"] <= 180 for r in rows if r.get("price"))
    leak_ok = RESULTS["checks"][-1]["result"] == "PASS"
    out = {"pair": "Hartwell listing 13 (floor $122) vs Riverbend sample request (budget $180)", "runs": rows,
           "deals_closed": f"{deals}/{len(rows)}", "prices_inside_both_limits": inside, "leak_scan": RESULTS["checks"][-1],
           "spend_usd": RESULTS["spend"]["cost_usd"]}
    (REPO / "output" / "eval_demo_pair.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\n{deals}/{len(rows)} closed as deals · prices inside both limits: {inside} · leak scan "
          f"{'PASS' if leak_ok else 'FAIL'} · spend ${RESULTS['spend']['cost_usd']:.4f}. Saved output/eval_demo_pair.json")
    return 0 if deals == len(rows) and inside and leak_ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    sys.exit(asyncio.run(main(ap.parse_args().runs)))
