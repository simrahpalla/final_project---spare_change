r"""Phase 6 tests: negotiation in the app, through the real backend API (and two direct server checks).

    .venv\Scripts\python.exe scripts\test_negotiation.py              # everything, in priority order
    .venv\Scripts\python.exe scripts\test_negotiation.py --only 1 2   # some sections

Sections run in priority order, so the most important evidence exists even if a spending cap stops the run:
  1. End to end: seller posts -> buyer alerted -> buyer negotiates -> both approve -> listing sold, need filled, alerts closed
  2. Leak scan: every API response either company saw, every message, note and alert; third-party access refused
  3. Oversell (units locked while a negotiation is open) and the reject path (listing back on the market)
  4. Concurrency: 5 negotiations started at once -> at most 3 run, the rest show "queued", all finish
  5. Consistency: the demo samples (clear deal, narrow deal, walk-away) x 3 runs each
  6. Safety in code: message with own limit blocked, other side's limit / money figures scrubbed; per-negotiation cost cap
Each section starts its own backend on a scratch copy of the database (port 8768/8769).
Writes output/eval_negotiation.json and output/phase6_stress.md.
"""

import argparse
import asyncio
import json
import os
import re
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
PAIR_TYPE = {(p["listing_id"], p["need_id"]): p for p in KEYS["negotiation_pairs"]}
SAMPLES = [  # the demo accounts' sample negotiations (decisions log #10), started by the account named
    {"name": "Hartwell -> Riverbend (clear deal)", "listing": 1, "need": 1, "by": 1, "expect": "deal"},
    {"name": "Summit -> Ironclad (clear deal)", "listing": 12, "need": 12, "by": 12, "expect": "deal"},
    {"name": "Hartwell -> Prairie Packaging (narrow deal)", "listing": 13, "need": 13, "by": 1, "expect": "deal"},
    {"name": "Redwood -> Coastal Electronics (narrow deal)", "listing": 15, "need": 15, "by": 13, "expect": "deal"},
    {"name": "Cascade -> Northwoods (walk-away)", "listing": 11, "need": 11, "by": 11, "expect": "no deal"},
]
RESULTS: dict = {"sections": [], "checks": [], "negotiations": [], "spend": {"cost_usd": 0.0, "tokens": 0}}
SPEND_CAP_USD = float(os.getenv("TEST_SPEND_CAP_USD", "1.50"))  # leaves room under the $2 session cap


def check(section: int, name: str, ok: bool, detail=None) -> bool:
    RESULTS["checks"].append({"section": section, "check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + ("" if ok else f"\n         {json.dumps(detail, default=str)[:700]}"), flush=True)
    return ok


class Backend:
    """The real backend on a scratch database. Records every API response with the company that saw it."""

    def __init__(self, port: int, env: dict | None = None):
        self.port, self.extra = port, env or {}
        self.base = f"http://127.0.0.1:{port}"
        self.seen: list[tuple[int | None, str, object]] = []

    async def __aenter__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sx_neg_"))
        self.db = self.tmp / "w.db"
        shutil.copyfile(REPO / "data" / "exchange.db", self.db)
        os.chmod(self.db, stat.S_IWRITE | stat.S_IREAD)
        env = {**os.environ, "SURPLUS_DB": str(self.db), "SURPLUS_AUDIT": str(self.tmp / "audit.json"),
               "PYTHONIOENCODING": "utf-8", **self.extra}
        self.log = open(self.tmp / "uvicorn.log", "w", encoding="utf-8")
        self.proc = subprocess.Popen([str(PY), "-m", "uvicorn", "main:app", "--app-dir", "backend", "--port", str(self.port)],
                                     cwd=str(REPO), env=env, stdout=self.log, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
        t0 = time.time()
        while time.time() - t0 < 180:
            try:
                if (await ahttp("GET", f"{self.base}/api/health", timeout=5))[1]["mcp"]["status"] != "starting":
                    break
            except (OSError, KeyError, ValueError):
                pass
            await asyncio.sleep(0.5)
        return self

    async def __aexit__(self, *exc):
        self.account_spend()
        kill_tree(self.proc.pid)
        self.log.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def q(self, sql: str, *args) -> list[dict]:
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in con.execute(sql, args)]
        finally:
            con.close()

    def account_spend(self) -> None:
        r = self.q("SELECT COALESCE(SUM(cost_usd),0) c, COALESCE(SUM(input_tokens+cached_tokens+output_tokens),0) t FROM token_usage")[0]
        RESULTS["spend"]["cost_usd"] = round(RESULTS["spend"]["cost_usd"] + r["c"], 6)
        RESULTS["spend"]["tokens"] += r["t"]

    async def call(self, method: str, path: str, body: dict | None = None, viewer: int | None = None) -> tuple[int, dict]:
        status, data = await ahttp(method, self.base + path, body)
        self.seen.append((viewer, f"{method} {path}", data))
        return status, data

    async def flow(self, path: str, body: dict) -> dict:
        status, started = await self.call("POST", path, body)
        if status != 200:
            return {"outcome": f"http {status}", "steps": []}
        while True:
            await asyncio.sleep(0.7)
            _, r = await ahttp("GET", f"{self.base}/api/runs/{started['run_id']}")
            if r.get("status") == "done":
                return r["result"]

    async def start(self, listing: int, need: int, company: int, limit: float | None = None) -> tuple[int, dict]:
        return await self.call("POST", "/api/negotiations/start",
                               {"listing_id": listing, "need_id": need, "company_id": company, "my_limit": limit}, viewer=company)

    async def wait(self, nid: int, company: int, timeout: float = 240) -> dict:
        t0, v = time.time(), {}
        while time.time() - t0 < timeout:
            _, v = await self.call("GET", f"/api/negotiations/{nid}?company_id={company}", viewer=company)
            if v.get("status") != "open" and not (v.get("live") or {}).get("status") == "running":
                return v
            await asyncio.sleep(1.0)
        return v | {"timed_out": True}

    def record(self, label: str, v: dict) -> None:
        n = self.q("SELECT * FROM negotiations WHERE id=?", v["negotiation_id"])[0]
        floor = self.q("SELECT floor_price f FROM seller_private WHERE listing_id=?", n["listing_id"])[0]["f"]
        ceiling = self.q("SELECT ceiling_price c FROM buyer_private WHERE need_id=?", n["need_id"])[0]["c"]
        cost = self.q("SELECT COALESCE(SUM(cost_usd),0) c, COALESCE(SUM(input_tokens+cached_tokens+output_tokens),0) t "
                      "FROM token_usage WHERE run_id=?", n["run_id"])[0]
        has_log = self.q("SELECT 1 FROM sqlite_master WHERE name='refused_calls'")
        blocked = self.q("SELECT role, code FROM refused_calls WHERE negotiation_id=? AND tool IN ('submit_offer','walk_away')",
                         n["id"]) if has_log else []
        RESULTS["negotiations"].append({
            "label": label, "negotiation_id": n["id"], "listing": n["listing_id"], "need": n["need_id"], "status": n["status"],
            "rounds": n["rounds_used"], "price": v.get("agreed_price") or (v.get("deal") or {}).get("price"),
            "floor": floor, "ceiling": ceiling, "end_reason": n["end_reason"], "cost_usd": round(cost["c"], 6), "tokens": cost["t"],
            "blocked_moves": blocked, "offers": [(o["from_side"], o["action"], o["price"]) for o in v.get("offers", [])]})


def over_budget() -> bool:
    return RESULTS["spend"]["cost_usd"] > SPEND_CAP_USD


# --------------------------------------------------------------------------- 1. end to end

async def end_to_end() -> None:
    print("\n1. End to end: seller posts -> buyer alerted -> negotiate -> both approve", flush=True)
    async with Backend(8768) as b:
        post = {"text": "1 grundfos CR15 shaft seal kit HQQE left over, opened box but never installed. 330 or best offer", "seller_id": 7}
        r = await b.flow("/api/seller-flow/start", post)
        lid = r.get("listing_id")
        alerts = next((s for s in r["steps"] if s["step"] == "alerts"), {})
        check(1, "Seller (Prairie) posts 1 seal kit: listed, Tidewater alerted", r["outcome"].startswith("listed and matched")
              and 39 in alerts.get("companies", []), {"outcome": r["outcome"], "alerts": alerts})
        _, tide = await b.call("GET", "/api/companies/39", viewer=39)
        alert = next((a for a in tide["alerts"] if a["kind"] == "new_match" and a["listing_id"] == lid), None)
        check(1, "Tidewater's bell shows the alert (switch account)", bool(alert), [a["message"] for a in tide["alerts"]])
        _, info = await b.call("GET", f"/api/negotiations/start-info?listing_id={lid}&need_id=20&company_id=39", viewer=39)
        check(1, "Start panel (as Tidewater): buyer side, its own budget only, can start",
              info.get("side") == "buyer" and info["my_limit"]["value"] == 415 and info.get("can_start"), info)
        st, started = await b.start(lid, 20, 39, 415)
        nid = started.get("negotiation_id")
        check(1, "Tidewater starts the negotiation; units locked at once", st == 200 and
              b.q("SELECT status FROM listings WHERE id=?", lid)[0]["status"] == "in_negotiation", started)
        v = await b.wait(nid, 39)
        b.record("e2e Prairie -> Tidewater", v)
        check(1, "Agents reach a deal within both limits (code-enforced)", v["status"] == "agreed" and v["deal"]
              and v["deal"]["price"] <= 415, {"status": v["status"], "offers": v.get("offers"), "explanation": v.get("explanation")})
        if not v.get("deal"):
            return
        st1, a1 = await b.call("POST", f"/api/negotiations/{nid}/approve", {"company_id": 39}, viewer=39)
        mid = b.q("SELECT status FROM deals WHERE negotiation_id=?", nid)[0]["status"]
        check(1, "Buyer approves its side: deal still pending (needs the seller too)", st1 == 200 and mid == "pending_approval", a1)
        st2, a2 = await b.call("POST", f"/api/negotiations/{nid}/approve", {"company_id": 7}, viewer=7)
        listing = b.q("SELECT status, qty FROM listings WHERE id=?", lid)[0]
        need = b.q("SELECT status FROM needs WHERE id=20")[0]
        open_alerts = b.q("SELECT COUNT(*) c FROM notifications WHERE kind='new_match' AND (listing_id=? OR need_id=20) "
                          "AND closed_reason IS NULL", lid)[0]["c"]
        check(1, "Seller approves too: deal closed, listing sold, need filled, related alerts closed",
              st2 == 200 and a2.get("status") == "approved" and listing["status"] == "sold" and need["status"] == "filled"
              and open_alerts == 0, {"deal": a2, "listing": listing, "need": need, "open_alerts": open_alerts})
        _, sv = await b.call("GET", f"/api/negotiations/{nid}?company_id=7", viewer=7)
        _, bv = await b.call("GET", f"/api/negotiations/{nid}?company_id=39", viewer=39)
        check(1, "Deal card per side: 'above your floor' for the seller, 'under your budget' for the buyer",
              "above your floor" in sv["deal"]["relative"] and "under your budget" in bv["deal"]["relative"],
              {"seller": sv["deal"]["relative"], "buyer": bv["deal"]["relative"]})
        board = (await b.call("GET", "/api/marketplace"))[1]
        check(1, "Sold listing and filled need are gone from the Marketplace",
              all(x["listing_id"] != lid for x in board["listings"]) and all(x["need_id"] != 20 for x in board["needs"]))
        await leak_scan(b, 1)


# --------------------------------------------------------------------------- 2. leak scan (also run inside other sections)

def _money_forms(v: float) -> list[str]:
    return [rf"\${v:,.0f}\b", rf"\${v:,.2f}\b", rf"\${v:.0f}\b", rf"\b{v:,.2f}\b"]


async def leak_scan(b: Backend, section: int) -> None:
    """For every response a company saw: the OTHER side's limit of any of its negotiations never appears, unless that
    exact number was also a public offer or ask. Messages, notes, alerts and public run results are scanned too."""
    negs = b.q("SELECT * FROM negotiations")
    priv = []
    for n in negs:
        floor = b.q("SELECT floor_price f FROM seller_private WHERE listing_id=?", n["listing_id"])[0]["f"]
        ceiling = b.q("SELECT ceiling_price c FROM buyer_private WHERE need_id=?", n["need_id"])[0]["c"]
        public = {o["price"] for o in b.q("SELECT price FROM offers WHERE negotiation_id=?", n["id"])}
        public |= {r["asking_price"] for r in b.q("SELECT asking_price FROM listings WHERE id=?", n["listing_id"])}
        priv.append((n, floor, ceiling, public))
    leaks = []
    for viewer, where, data in b.seen:
        text = json.dumps(data, default=str)
        for n, floor, ceiling, public in priv:
            hidden = []  # limits this viewer must not see
            if viewer != n["seller_id"]:
                hidden.append(("seller floor", floor))
            if viewer != n["buyer_id"]:
                hidden.append(("buyer budget", ceiling))
            for label, val in hidden:
                if val in public:
                    continue  # the same number was public anyway (an offer or the ask)
                in_view = isinstance(data, dict) and data.get("negotiation_id") == n["id"]
                if in_view and re.search(rf"(?<![\d.]){re.escape(repr(float(val)))}(?![\d])|(?<![\d.,]){int(val)}(?![\d.,])", text):
                    leaks.append(f"{where} (viewer {viewer}): {label} {val} of negotiation {n['id']} in the view")
                for pat in _money_forms(val):
                    if re.search(pat, text):
                        leaks.append(f"{where} (viewer {viewer}): {label} ${val:,.0f} of negotiation {n['id']} as text")
                        break
        if isinstance(data, dict) and "/api/runs/" in where:
            if "reasoning" in text or "note" in json.dumps(data.get("steps", [])):
                leaks.append(f"{where}: a public run result carries private reasoning")
    msgs = b.q("SELECT o.message, o.negotiation_id FROM offers o")
    for m in msgs:
        n, floor, ceiling, public = next(p for p in priv if p[0]["id"] == m["negotiation_id"])
        for val in (floor, ceiling):
            if m["message"] and any(re.search(p, m["message"]) for p in _money_forms(val)):
                leaks.append(f"message in negotiation {m['negotiation_id']} contains a limit: {m['message']!r}")
    for a in b.q("SELECT message FROM notifications"):
        for n, floor, ceiling, public in priv:
            for val in (floor, ceiling):
                if val not in public and any(re.search(p, a["message"]) for p in _money_forms(val)):
                    leaks.append(f"alert text contains a private limit: {a['message']!r}")
    third = []
    for n, *_ in priv[:5]:
        outsider = next(c for c in (1, 7, 11, 12, 13, 20, 39, 40) if c not in (n["seller_id"], n["buyer_id"]))
        st, _ = await ahttp("GET", f"{b.base}/api/negotiations/{n['id']}?company_id={outsider}")
        if st != 403:
            third.append(f"negotiation {n['id']} readable by company {outsider} (HTTP {st})")
    leaks = sorted(set(leaks))
    check(2, f"Leak scan (section {section}): {len(b.seen)} API responses, {len(msgs)} messages and all alerts; neither side's view holds "
                   f"the other's limit; a third company is refused", not leaks and not third,
          {"leaks": leaks[:15], "third_party": third})
    RESULTS.setdefault("leak_scans", []).append({"section": section, "responses": len(b.seen), "messages": len(msgs),
                                                 "negotiations": len(priv), "leaks": leaks, "third_party": third})


# --------------------------------------------------------------------------- 3. oversell + reject

async def oversell_and_reject() -> None:
    print("\n3. Oversell attempt and the reject path", flush=True)
    async with Backend(8768) as b:
        # listing 2 has 2 units; need 2 wants 2 and need 17 wants 1
        st1, a = await b.start(2, 2, 2)
        st2, bb = await b.start(2, 17, 2)
        st3, c = await b.start(2, 2, 21, 3700)  # the same need again, from the buyer side
        check(3, "Oversell: listing 2 (2 units) locked by a 2-unit negotiation; a second buyer and a duplicate are refused",
              st1 == 200 and st2 == 409 and st3 == 409, {"first": a, "second": bb, "duplicate": c})
        locked = b.q("SELECT COALESCE(SUM(qty),0) q FROM negotiations WHERE listing_id=2 AND status IN ('open','agreed')")[0]["q"]
        check(3, "Units locked never exceed the listing's quantity", locked <= 2, {"locked": locked})
        v = await b.wait(a["negotiation_id"], 2)
        b.record("oversell base 2/2", v)
        if v.get("deal"):
            await b.call("POST", f"/api/negotiations/{v['negotiation_id']}/approve", {"company_id": 2}, viewer=2)
            st4, d = await b.call("POST", f"/api/negotiations/{v['negotiation_id']}/reject", {"company_id": 21, "note": "budget changed"}, viewer=21)
            neg = b.q("SELECT status, end_reason FROM negotiations WHERE id=?", v["negotiation_id"])[0]
            listing = b.q("SELECT status, qty FROM listings WHERE id=2")[0]
            check(3, "Reject (buyer rejects after the seller approved): negotiation closed, nothing sold, listing back to active",
                  st4 == 200 and neg["status"] == "rejected" and listing == {"status": "active", "qty": 2}, {"neg": neg, "listing": listing})
            _, sv = await b.call("GET", f"/api/negotiations/{v['negotiation_id']}?company_id=2", viewer=2)
            check(3, "Seller sees why (plain English) and a next-best buyer to try",
                  bool(sv.get("explanation")) and (sv.get("next_best") or {}).get("need_id") == 17, {"explanation": sv.get("explanation"), "next": sv.get("next_best")})
            st5, e = await b.start(2, 17, 2)
            check(3, "After the reject, the freed units can be negotiated with the next-best buyer", st5 == 200, e)
            if st5 == 200:
                b.record("after reject 2/17", await b.wait(e["negotiation_id"], 2))
        else:
            check(3, "Reject path needs a deal first", False, {"status": v.get("status"), "explanation": v.get("explanation")})
        await leak_scan(b, 3)


# --------------------------------------------------------------------------- 4. concurrency

async def concurrency() -> None:
    print("\n4. Five negotiations started at once (limit 3 running)", flush=True)
    async with Backend(8768) as b:
        pairs = [(4, 4, 4), (5, 5, 5), (7, 7, 7), (8, 8, 8), (10, 10, 10)]
        starts = await asyncio.gather(*[b.start(l, n, c) for l, n, c in pairs])
        ok = all(s == 200 for s, _ in starts)
        queued_flags = [d.get("queued") for _, d in starts]
        max_running, saw_queued = 0, False
        t0 = time.time()
        while time.time() - t0 < 400:
            views = [(await b.call("GET", f"/api/negotiations/{d['negotiation_id']}?company_id={c}", viewer=c))[1]
                     for (_, d), (_, _, c) in zip(starts, pairs) if d.get("negotiation_id")]
            running = sum(1 for v in views if (v.get("live") or {}).get("status") == "running" and not v["live"]["queued"])
            saw_queued |= any((v.get("live") or {}).get("queued") for v in views)
            max_running = max(max_running, running)
            if all(v["status"] != "open" and (v.get("live") or {}).get("status") != "running" for v in views):
                break
            await asyncio.sleep(0.8)
        for v, (l, n, _) in zip(views, pairs):
            b.record(f"concurrent {l}/{n}", v)
        bad = [v["negotiation_id"] for v in views if v["status"] in ("open", "stopped")]
        # Exact measures (polling 5 views one by one can catch a finishing run and its replacement in one sweep):
        # (a) how many runs had to wait for a slot, (b) the most runs making model calls at the same time.
        waited = 0
        for _, d in starts:
            _, run = await b.call("GET", f"/api/runs/{d['run_id']}")
            waited += any(x["step"] == "queued" for x in run.get("steps", []))
        spans = [(r["a"], r["z"]) for r in b.q("SELECT MIN(created_at) a, MAX(created_at) z FROM token_usage "
                                                "WHERE run_kind='negotiation' GROUP BY run_id")]
        overlap = max(sum(1 for a, z in spans if a <= t <= z) for t, _ in spans) if spans else 0
        RESULTS["concurrency"] = {"started": 5, "waited_for_slot": waited, "max_overlapping_model_activity": overlap,
                                  "saw_queued_in_ui": saw_queued, "max_running_by_polling": max_running}
        check(4, f"5 started at once: all accepted; {waited} waited in the queue (shown as Queued: {saw_queued}); "
                 f"at most {overlap} negotiating at the same time", ok and waited >= 2 and overlap <= 3,
              RESULTS["concurrency"])
        check(4, "All 5 finished with a real outcome (no crash, no stuck or stopped negotiation)", not bad,
              {"statuses": [v["status"] for v in views]})
        within = [r for r in RESULTS["negotiations"] if r["label"].startswith("concurrent") and r["price"]
                  and not r["floor"] <= r["price"] <= r["ceiling"]]
        check(4, "Every agreed price is within both private limits", not within, within)
        await leak_scan(b, 4)


# --------------------------------------------------------------------------- 5. consistency of the demo samples

async def consistency(rounds: int = 3) -> None:
    print(f"\n5. Demo samples x {rounds} runs (consistency)", flush=True)
    async with Backend(8768) as b:
        tally = {s["name"]: [] for s in SAMPLES}
        for k in range(rounds):
            if over_budget():
                break
            b.account_spend()  # the reset below clears token_usage: count this round's spend first
            await b.call("POST", "/api/reset")
            starts = await asyncio.gather(*[b.start(s["listing"], s["need"], s["by"]) for s in SAMPLES])
            views = await asyncio.gather(*[b.wait(d["negotiation_id"], s["by"]) if st == 200 else asyncio.sleep(0, {"status": f"http {st}"})
                                           for (st, d), s in zip(starts, SAMPLES)])
            for s, v in zip(SAMPLES, views):
                if "negotiation_id" in v:
                    b.record(f"sample run {k + 1}: {s['name']}", v)
                tally[s["name"]].append({"status": v.get("status"), "price": (v.get("deal") or {}).get("price"),
                                         "rounds": v.get("rounds_used")})
        rows = []
        for s in SAMPLES:
            runs = tally[s["name"]]
            got = ["deal" if r["status"] == "agreed" else "no deal" for r in runs]
            prices = [r["price"] for r in runs if r["price"]]
            rows.append({"sample": s["name"], "expected": s["expect"], "outcomes": got, "prices": prices,
                         "rounds": [r["rounds"] for r in runs], "as_expected": f"{got.count(s['expect'])}/{len(got)}"})
        RESULTS["consistency"] = rows
        for r in rows:
            check(5, f"{r['sample']}: {r['as_expected']} runs as expected; prices {r['prices']}", r["outcomes"].count(
                next(s["expect"] for s in SAMPLES if s["name"] == r["sample"])) == len(r["outcomes"]), r)
        await leak_scan(b, 5)


# --------------------------------------------------------------------------- 6. safety in code

def _in_role(db: Path, role: str, code: str, negotiation: int | None = None) -> dict:
    env = {**os.environ, "SURPLUS_DB": str(db), "SURPLUS_ROLE": role, "PYTHONIOENCODING": "utf-8"}
    if negotiation:
        env["SURPLUS_NEGOTIATION_ID"] = str(negotiation)
    out = subprocess.run([str(PY), "-c", "import sys, json; sys.path.insert(0, 'mcp_server'); import server; " + code],
                         cwd=str(REPO), env=env, capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout.strip().splitlines()[-1]) if out.stdout.strip() else {"error": out.stderr[-500:]}


async def safety() -> None:
    print("\n6. Message safety and the per-negotiation cost cap", flush=True)
    tmp = Path(tempfile.mkdtemp(prefix="sx_negsafe_"))
    db = tmp / "w.db"
    shutil.copyfile(REPO / "data" / "exchange.db", db)
    os.chmod(db, stat.S_IWRITE | stat.S_IREAD)
    opened = _in_role(db, "broker", "print(json.dumps(server.open_negotiation(1, 1)))")
    nid = opened.get("negotiation_id")
    own = _in_role(db, "seller_agent", "print(json.dumps(server.submit_offer('offer', 1400, 'Our floor is 905, so 1400 is fair.')))", nid)
    ok = _in_role(db, "seller_agent", "print(json.dumps(server.submit_offer('offer', 1400, "
                  "'Best we can do is $1,400; your budget is probably 1890 anyway.')))", nid)
    con = sqlite3.connect(db)
    saved = con.execute("SELECT message FROM offers WHERE negotiation_id=?", (nid,)).fetchall()
    con.close()
    check(6, "A message with the agent's OWN limit is blocked (the agent must rewrite it)",
          own.get("code") == "would_reveal_private_limit", own)
    check(6, "The other side's limit and every money figure are scrubbed before the message is saved or shown",
          ok.get("ok") and saved and "1890" not in saved[-1][0] and "$1,400" not in saved[-1][0], {"saved": saved})
    shutil.rmtree(tmp, ignore_errors=True)
    async with Backend(8769, {"NEGOTIATION_MAX_COST_USD": "0.0004"}) as b:
        st, d = await b.start(13, 13, 1)
        v = await b.wait(d["negotiation_id"], 1) if st == 200 else {}
        b.record("cost cap 13/13", v) if v else None
        check(6, "Per-negotiation cost cap ($0.0004 for this test) stops a negotiation safely, with a plain explanation",
              v.get("status") in ("stopped", "agreed", "walked_away", "round_cap") and (
                  v.get("status") != "stopped" or "cost cap" in (v.get("explanation") or "")),
              {"status": v.get("status"), "explanation": v.get("explanation"), "cost": v.get("cost")})
        RESULTS["cost_cap"] = {"status": v.get("status"), "explanation": v.get("explanation"), "cost": v.get("cost")}


# --------------------------------------------------------------------------- report

def write_report(started: float) -> None:
    RESULTS["seconds"] = round(time.time() - started)
    (REPO / "output" / "eval_negotiation.json").write_text(json.dumps(RESULTS, indent=2, default=str), encoding="utf-8")
    passed = sum(c["result"] == "PASS" for c in RESULTS["checks"])
    md = ["# Phase 6 stress test: negotiation", "",
          f"`scripts/test_negotiation.py`, real backend API on scratch databases. {passed}/{len(RESULTS['checks'])} checks pass. "
          f"Model spend for this run: ${RESULTS['spend']['cost_usd']:.4f} ({RESULTS['spend']['tokens']:,} tokens), {RESULTS['seconds']} s.", "",
          "| Section | Check | Result |", "|---|---|---|"]
    names = {1: "End to end", 2: "Leak scan", 3: "Oversell / reject", 4: "Concurrency", 5: "Consistency", 6: "Safety in code"}
    for c in RESULTS["checks"]:
        md.append(f"| {c['section']}. {names.get(c['section'], '')} | {c['check']} | **{c['result']}** |")
    if RESULTS.get("consistency"):
        md += ["", "## Demo samples, repeated", "", "| Sample | Expected | Outcomes | Prices | Rounds |", "|---|---|---|---|---|"]
        md += [f"| {r['sample']} | {r['expected']} | {', '.join(r['outcomes'])} ({r['as_expected']}) | "
               f"{', '.join(f'${p:,.0f}' for p in r['prices']) or '—'} | {r['rounds']} |" for r in RESULTS["consistency"]]
    md += ["", "## Every negotiation in this run", "", "| Label | Status | Rounds | Price | Floor | Budget | Blocked moves | Cost |",
           "|---|---|---|---|---|---|---|---|"]
    for n in RESULTS["negotiations"]:
        blocked = ", ".join(f"{b['role'].split('_')[0]}: {b['code']}" for b in n["blocked_moves"]) or "—"
        md.append(f"| {n['label']} | {n['status']} | {n['rounds']} | {('$%s' % format(n['price'], ',.2f')) if n['price'] else '—'} | "
                  f"${n['floor']:,.0f} | ${n['ceiling']:,.0f} | {blocked} | ${n['cost_usd']:.5f} |")
    (REPO / "output" / "phase6_stress.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\n{passed}/{len(RESULTS['checks'])} checks pass. Spend ${RESULTS['spend']['cost_usd']:.4f}. "
          "Saved output/eval_negotiation.json and output/phase6_stress.md")


async def main(only: list[int]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    started = time.time()
    plan = [(1, end_to_end), (3, oversell_and_reject), (4, concurrency), (5, consistency), (6, safety)]
    for num, fn in plan:  # the leak scan (2) runs inside every section, on everything that section's companies saw
        if only and num not in only:
            continue
        if over_budget():
            RESULTS["stopped_by_spend_cap"] = f"before section {num}: ${RESULTS['spend']['cost_usd']:.4f} spent"
            print(RESULTS["stopped_by_spend_cap"])
            break
        RESULTS["sections"].append(num)
        await fn()
        write_report(started)
    write_report(started)
    return 0 if all(c["result"] == "PASS" for c in RESULTS["checks"]) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, nargs="*", default=[])
    sys.exit(asyncio.run(main(ap.parse_args().only)))
