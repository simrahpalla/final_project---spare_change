r"""End-to-end test of two-sided matching through the real backend API (Phase 5).

    .venv\Scripts\python.exe scripts\test_two_sided.py

Starts the FastAPI backend (uvicorn) on a scratch copy of the database and drives it like the UI does:

Part A, sequential (one two-account flow at a time):
  1. Seller account posts on Sell (POST /api/seller-flow/start, poll /api/runs/{id}).
  2. The run's alerts step names the buyer.  3. "Switch account": GET /api/companies/{buyer} shows the alert.
  4. The seller's own account shows its side of the alert; other accounts see neither (each account sees only its own).
  5. Buyer posts a need with a private max price on Buy (POST /api/need-flow/start): the seller is alerted,
     and the max price appears in no alert, no company view and not on the Marketplace board.
  6. Re-running the same matching sends NO duplicate alerts.  7. A need with no surplus makes no matching-agent call.
  8. Reset demo (POST /api/reset) restores a clean state.
Part B, concurrent: after a reset, the four demo flows (2 seller posts + 2 buyer posts) start at the same moment,
plus two re-runs of seeded matching, and every expected alert must arrive exactly once with no crash.
Tokens per alert event: every alert's run_id joined to token_usage (input / cached / output tokens and cost).
Writes output/two_sided_test.json.
"""

import asyncio
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from concurrency_test import ahttp, kill_tree  # noqa: E402
from stress_phase3 import PY  # noqa: E402

KEYS = json.loads((REPO / "data" / "answer_keys.json").read_text(encoding="utf-8"))
TS = KEYS["two_sided"]
PORT = 8766
BASE = f"http://127.0.0.1:{PORT}"
results: list[dict] = []


def case(name: str, ok: bool, detail=None) -> bool:
    results.append({"case": name, "pass": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"\n       {detail}" if detail is not None and not ok else ""), flush=True)
    return ok


async def run_flow(path: str, body: dict) -> dict:
    status, started = await ahttp("POST", BASE + path, body)
    if status != 200:
        return {"outcome": f"http {status}: {started}", "steps": [], "crashed": status >= 500}
    while True:
        await asyncio.sleep(0.6)
        _, r = await ahttp("GET", f"{BASE}/api/runs/{started['run_id']}")
        if r.get("status") == "done":
            return r["result"] | {"crashed": False}


def step(r: dict, name: str) -> dict:
    return next((s for s in r.get("steps", []) if s["step"] == name), {})


async def company(cid: int) -> dict:
    return (await ahttp("GET", f"{BASE}/api/companies/{cid}"))[1]


def ceilings(db: Path) -> dict[int, float]:
    con = sqlite3.connect(db)
    out = dict(con.execute("SELECT need_id, ceiling_price FROM buyer_private").fetchall())
    con.close()
    return out


def money_forms(v: float) -> list[str]:
    return [f"${v:,.0f}", f"${v:.0f}", f"${v:,.2f}", f"{v:.1f}"]


async def part_a(db: Path) -> None:
    print("\nPart A: two-account flows, one at a time", flush=True)
    seller = TS["seller_posts"][0]  # Prairie posts CR 15 seal kits -> Tidewater's need #20
    buyer_id, need_id = seller["expected_first_buyer"], seller["expected_alert_need"]
    r = await run_flow("/api/seller-flow/start", {"text": seller["text"], "seller_id": seller["seller_id"]})
    ranked = step(r, "matching").get("ranked") or []
    lid = r.get("listing_id")
    case("A1. seller posts on Sell: listed and matched", r["outcome"].startswith("listed and matched") and ranked
         and ranked[0]["buyer_id"] == buyer_id, {"outcome": r["outcome"], "ranked": [m["buyer_id"] for m in ranked]})
    al = step(r, "alerts")
    case("A2. alerts step (code) alerts the buyer and the seller", sorted(al.get("companies", [])) == sorted(seller["expected_alerts_to"]), al)

    b = await company(buyer_id)
    mine = [a for a in b["alerts"] if a["listing_id"] == lid and a["need_id"] == need_id]
    case("A3. switch to the buyer account: the alert is visible, unread, with its score",
         len(mine) == 1 and not mine[0]["read"] and mine[0]["score"] >= 70 and b["unread_alerts"] >= 1, mine)
    s = await company(seller["seller_id"])
    case("A4. the seller account sees its side of the same match",
         any(a["listing_id"] == lid and a["need_id"] == need_id for a in s["alerts"]), [a["message"] for a in s["alerts"]])
    other = await company(20)
    case("A5. another account (Riverbend) does not see either alert",
         not any(a["listing_id"] == lid for a in other["alerts"]), [a["message"] for a in other["alerts"]])
    case("A6. every alert in a company view belongs to that company",
         all(a["company_id"] == cid for cid, view in ((buyer_id, b), (seller["seller_id"], s), (20, other)) for a in view["alerts"]))

    post = TS["buyer_posts"][0]  # Riverbend posts DI cards with a private max -> Hartwell listing 13
    r2 = await run_flow("/api/need-flow/start", {"text": post["text"], "buyer_id": post["buyer_id"], "max_price": post["max_price"]})
    nid = r2.get("need_id")
    ranked2 = step(r2, "matching").get("ranked") or []
    case("A7. buyer posts on Buy: same matching agent in reverse ranks the expected listing first",
         r2["outcome"] == "posted and matched" and ranked2 and ranked2[0]["listing_id"] == post["expected_first_listing"],
         {"outcome": r2["outcome"], "ranked": [m["listing_id"] for m in ranked2]})
    case("A8. the max price is stored privately (write-only)", step(r2, "save").get("ceiling_recorded") is True, step(r2, "save"))
    hart = await company(1)
    case("A9. switch to the seller (Hartwell): the new-need alert is visible",
         any(a["need_id"] == nid and a["listing_id"] == post["expected_first_listing"] for a in hart["alerts"]),
         [a["message"] for a in hart["alerts"]])

    board = (await ahttp("GET", f"{BASE}/api/marketplace"))[1]
    # The posted need's max ($180) must appear nowhere others can see. For every other need, its own board entry
    # must not carry its max. (A seller's public ask can equal some buyer's max by coincidence: that is not a leak.)
    views = {"board": json.dumps(board), "Hartwell view": json.dumps(hart), "Tidewater view": json.dumps(b),
             "matching step shown to sellers": json.dumps(step(r2, "matching")),
             "alerts sent": json.dumps([a for v in (hart, b) for a in v["alerts"]])}
    caps = ceilings(db)
    leaks = [f"posted need {nid}: max ${caps[nid]:,.0f} found in {where}" for where, text in views.items()
             if any(f in text for f in money_forms(caps[nid]))]
    for n in board["needs"]:
        if "ceiling_price" in n or (n["need_id"] in caps and caps[n["need_id"]] in n.values()):
            leaks.append(f"need {n['need_id']}: its max is in its Marketplace entry")
    if "ceiling" in views["board"]:
        leaks.append("a ceiling field is on the Marketplace board")
    case("A10. no buyer max price in alerts, company views or the Marketplace board", not leaks, leaks)
    case("A11. the Marketplace shows the new need and its match badge pair",
         any(n["need_id"] == nid for n in board["needs"]) and
         any(p["need_id"] == nid and p["listing_id"] == post["expected_first_listing"] for p in board["pairs"]))

    before = len((await company(buyer_id))["alerts"]) + len((await company(1))["alerts"])
    again = await run_flow("/api/seller-flow/start", {"listing_id": lid})
    again2 = await run_flow("/api/need-flow/start", {"need_id": nid})
    after = len((await company(buyer_id))["alerts"]) + len((await company(1))["alerts"])
    case("A12. re-running both matchings sends no duplicate alerts",
         after == before and step(again, "alerts").get("sent") == 0 and step(again, "alerts").get("duplicates", 0) >= 2
         and step(again2, "alerts").get("sent") == 0,
         {"before": before, "after": after, "seller_rerun": step(again, "alerts"), "need_rerun": step(again2, "alerts")})

    empty = TS["buyer_posts"][1]
    r3 = await run_flow("/api/need-flow/start", {"text": empty["text"], "buyer_id": empty["buyer_id"], "max_price": empty["max_price"]})
    calls = [a["agent"] for a in r3.get("agent_calls", [])]
    case("A13. a need with no surplus: 0 candidates, matching agent skipped (no model call)",
         r3["outcome"].startswith("posted (no matching") and step(r3, "prefilter").get("candidates") == 0
         and "matching_agent" not in calls, {"outcome": r3["outcome"], "agents": calls})

    status, _ = await ahttp("POST", f"{BASE}/api/reset")
    after_reset = await company(buyer_id)
    board2 = (await ahttp("GET", f"{BASE}/api/marketplace"))[1]
    case("A14. Reset demo restores the seeded state (no alerts, the posted need is gone)",
         status == 200 and not after_reset["alerts"] and not any(n["need_id"] == nid for n in board2["needs"]),
         {"status": status, "alerts": len(after_reset["alerts"])})


async def part_b() -> None:
    print("\nPart B: the demo flows at the same moment (concurrent requests)", flush=True)
    jobs = ([("/api/seller-flow/start", {"text": p["text"], "seller_id": p["seller_id"]}, p) for p in TS["seller_posts"]]
            + [("/api/need-flow/start", {"text": p["text"], "buyer_id": p["buyer_id"], "max_price": p["max_price"]}, p)
               for p in TS["buyer_posts"]]
            + [("/api/need-flow/start", {"need_id": 2}, None), ("/api/need-flow/start", {"need_id": 5}, None)])
    t0 = time.time()
    outs = await asyncio.gather(*[run_flow(path, body) for path, body, _ in jobs], return_exceptions=True)
    secs = round(time.time() - t0, 1)
    crashed = [str(o) if isinstance(o, Exception) else o["outcome"] for o in outs
               if isinstance(o, Exception) or o.get("crashed") or str(o.get("outcome", "")).startswith("error")]
    case(f"B1. {len(jobs)} flows at once: no crash, no error ({secs}s)", not crashed, crashed)
    missing = []
    for (path, body, p), o in zip(jobs, outs):
        if isinstance(o, Exception) or not p:
            continue
        got = sorted(step(o, "alerts").get("companies", []))
        if got != sorted(p["expected_alerts_to"]):
            missing.append(f"{p['name']}: alerts to {got}, expected {p['expected_alerts_to']}")
        for cid in p["expected_alerts_to"]:
            view = await company(cid)
            if not view["alerts"]:
                missing.append(f"{p['name']}: company {cid} shows no alert")
    case("B2. every expected alert arrived and is visible in the right account", not missing, missing)
    con = sqlite3.connect(DB_REF[0])
    dup = con.execute("SELECT company_id, listing_id, need_id, COUNT(*) c FROM notifications WHERE kind='new_match' "
                      "GROUP BY 1,2,3 HAVING c > 1").fetchall()
    con.close()
    case("B3. no duplicate alerts under concurrency", not dup, dup)


def tokens_per_alert_event(db: Path) -> list[dict]:
    """Each alert event = one matching run. Its tokens come from token_usage rows with the same run_id."""
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT n.run_id, COUNT(DISTINCT n.id) AS alerts, GROUP_CONCAT(DISTINCT n.company_id) AS companies, "
        "(SELECT run_kind FROM token_usage t WHERE t.run_id=n.run_id LIMIT 1) AS run_kind, "
        "(SELECT SUM(requests) FROM token_usage t WHERE t.run_id=n.run_id) AS requests, "
        "(SELECT SUM(input_tokens) FROM token_usage t WHERE t.run_id=n.run_id) AS input_tokens, "
        "(SELECT SUM(cached_tokens) FROM token_usage t WHERE t.run_id=n.run_id) AS cached_tokens, "
        "(SELECT SUM(output_tokens) FROM token_usage t WHERE t.run_id=n.run_id) AS output_tokens, "
        "(SELECT ROUND(SUM(cost_usd), 6) FROM token_usage t WHERE t.run_id=n.run_id) AS cost_usd, "
        "(SELECT ROUND(SUM(cost_usd), 6) FROM token_usage t WHERE t.run_id=n.run_id AND t.agent='matching_agent') AS matching_cost_usd "
        "FROM notifications n WHERE n.kind='new_match' GROUP BY n.run_id ORDER BY MIN(n.id)")]
    con.close()
    return rows


DB_REF: list[Path] = []


async def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="sx_2side_"))
    db = tmp / "w.db"
    DB_REF.append(db)
    shutil.copyfile(REPO / "data" / "exchange.db", db)
    os.chmod(db, stat.S_IWRITE | stat.S_IREAD)
    env = {**os.environ, "SURPLUS_DB": str(db), "SURPLUS_AUDIT": str(tmp / "audit.json"), "PYTHONIOENCODING": "utf-8"}
    log = open(tmp / "uvicorn.log", "w", encoding="utf-8")
    proc = subprocess.Popen([str(PY), "-m", "uvicorn", "main:app", "--app-dir", "backend", "--port", str(PORT)],
                            cwd=str(REPO), env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
    events = []
    try:
        t0 = time.time()
        while time.time() - t0 < 180:
            try:
                if (await ahttp("GET", f"{BASE}/api/health", timeout=5))[1]["mcp"]["status"] != "starting":
                    break
            except (OSError, KeyError, ValueError):
                pass
            await asyncio.sleep(0.5)
        print(f"backend up in {time.time() - t0:.1f}s on a scratch copy of the database", flush=True)
        await part_a(db)
        await ahttp("POST", f"{BASE}/api/reset")
        await part_b()
        events = tokens_per_alert_event(db)
    finally:
        kill_tree(proc.pid)
        log.close()

    print("\nTokens per alert event (Part B, after reset)")
    for e in events:
        print(f"  run {e['run_id']} ({e['run_kind']}): {e['alerts']} alerts to companies {e['companies']} · "
              f"{e['requests']} requests · in {e['input_tokens']} · cached {e['cached_tokens']} · out {e['output_tokens']} · "
              f"${e['cost_usd']:.6f} (matching ${e['matching_cost_usd'] or 0:.6f})")
    passed = sum(r["pass"] for r in results)
    (REPO / "output" / "two_sided_test.json").write_text(json.dumps(
        {"passed": passed, "cases": len(results), "results": results, "tokens_per_alert_event": events}, indent=2, default=str),
        encoding="utf-8")
    print(f"\n{passed}/{len(results)} cases pass. Saved output/two_sided_test.json")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
