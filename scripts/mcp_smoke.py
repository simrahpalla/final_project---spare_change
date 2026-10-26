r"""MCP smoke test: every tool called at least once, over the real MCP protocol (stdio), per role.

    .venv\Scripts\python.exe scripts\mcp_smoke.py

Each role is its own server process (SURPLUS_ROLE=...), exactly as the agents will connect. Runs on a
scratch copy of data/exchange.db, so the working copy is untouched. Every call states what should
happen ("ok" or "refused") and the test checks it. Writes output/mcp_smoke.json.

Besides one happy-path call per tool, it shows the code-enforced defenses:
  role isolation (a tool outside your role does not exist), compliance blocks on the planted bad
  listings, ungrounded matches rejected, negotiation limits / direction / turns / round cap, no
  private limit in messages, and agent names refused at human approval.
"""

import asyncio
import json
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "mcp_server" / "server.py"
OUT = REPO / "output" / "mcp_smoke.json"
PYTHON = next((p for p in (REPO / ".venv" / "Scripts" / "python.exe", REPO / ".venv" / "bin" / "python") if p.exists()),
              Path(sys.executable))
MAX_ROUNDS = 6


def trim(obj, depth=0):
    """Keep the evidence readable: long lists and strings are shortened."""
    if isinstance(obj, list):
        out = [trim(x, depth + 1) for x in obj[:3]]
        return out + [f"... {len(obj) - 3} more"] if len(obj) > 3 else out
    if isinstance(obj, dict):
        return {k: trim(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, str) and len(obj) > 240:
        return obj[:240] + "…"
    return obj


class Smoke:
    def __init__(self, db: Path):
        self.db = db
        self.calls: list[dict] = []
        self.tools_by_role: dict[str, list[str]] = {}

    def transport(self, role: str, negotiation_id: int | None = None) -> StdioTransport:
        env = {"SURPLUS_ROLE": role, "SURPLUS_DB": str(self.db), "MAX_NEGOTIATION_ROUNDS": str(MAX_ROUNDS),
               "FASTMCP_LOG_LEVEL": "WARNING"}
        if negotiation_id:
            env["SURPLUS_NEGOTIATION_ID"] = str(negotiation_id)
        return StdioTransport(command=str(PYTHON), args=[str(SERVER)], env=env, cwd=str(REPO))

    async def call(self, client: Client, role: str, tool: str, args: dict, expect: str, why: str,
                   code: str | None = None) -> dict:
        res = await client.call_tool(tool, args, raise_on_error=False)
        if res.is_error:
            data = {"ok": False, "error": " ".join(getattr(c, "text", "") for c in res.content)}
        else:
            data = res.structured_content if res.structured_content is not None else res.data
            data = data.get("result", data) if isinstance(data, dict) and set(data) == {"result"} else data
        ok = data.get("ok", True) if isinstance(data, dict) else True
        passed = ok if expect == "ok" else not ok
        if expect == "refused" and code:  # refused for the RIGHT reason, not just refused
            passed = passed and code in json.dumps(data)
        self.calls.append({"step": len(self.calls) + 1, "role": role, "tool": tool, "args": args, "expect": expect,
                           "why": why, "expected_code": code, "passed": passed, "result": trim(data)})
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {role:<14} {tool:<26} expect {expect:<8} {why}")
        return data


async def run(smoke: Smoke) -> None:
    S = smoke

    # ---- tools per role (role isolation is by registration: absent tools can't be called)
    for role in ("broker", "seller_agent", "buyer_agent", "human_approver", "system"):
        async with Client(init_timeout=30, transport=S.transport(role, 1 if role.endswith("_agent") else None)) as c:
            S.tools_by_role[role] = sorted(t.name for t in await c.list_tools())

    # ---- broker: reads
    async with Client(init_timeout=30, transport=S.transport("broker")) as b:
        await S.call(b, "broker", "get_exchange_date", {}, "ok", "exchange 'today' comes from the DB, not the clock")
        await S.call(b, "broker", "lookup_part", {"query": "6ES7 315-2AG10"}, "ok", "messy part number -> exact catalog part")
        await S.call(b, "broker", "lookup_part", {"query": "CR 15 seal"}, "ok", "word search finds the CR 15 seal kit")
        await S.call(b, "broker", "get_compatibility", {"part_number": "1756-EN2T"}, "ok", "EN2T fits 5560/5570 and substitutes for ENBT")
        await S.call(b, "broker", "get_price_reference", {"part_number": "1756-L61"}, "ok", "new price, scrap value, current asks")
        await S.call(b, "broker", "get_listing", {"listing_id": 1}, "ok", "public listing: no floor price in it")
        await S.call(b, "broker", "get_need", {"need_id": 1}, "ok", "public need: no ceiling price in it")
        await S.call(b, "broker", "get_company_profile", {"company_id": 20}, "ok", "buyer profile: runs 4x Siemens S7-300 (18 yrs)")

        # ---- broker: a new listing end to end (fills the open CR 15 need #20 -> two-sided alert)
        new = await S.call(b, "broker", "create_listing", {
            "seller_id": 7, "raw_text": "2 grundfos CR15 seal kits HQQE, opened box never used, $330 ea",
            "part_number": "96525458", "qty": 2, "condition": "new_open_box", "asking_price": 330, "floor_price": 240,
        }, "ok", "store a structured listing (status submitted)")
        lid = new.get("listing_id")
        await S.call(b, "broker", "create_listing", {
            "seller_id": 7, "raw_text": "mystery part", "part_number": "NOT-A-PART", "qty": 1, "condition": "used_working",
        }, "refused", "unknown part numbers are refused, so an agent can't invent one", code="invalid_field")
        await S.call(b, "broker", "check_listing_rules", {"listing_id": lid}, "ok", "deterministic rules: allowed")
        await S.call(b, "broker", "activate_listing", {"listing_id": lid}, "ok", "clean listing goes active")
        await S.call(b, "broker", "search_listings_for_need", {"need_id": 20}, "ok", "reverse search: need #20 now finds the new listing")
        await S.call(b, "broker", "search_buyers_for_listing", {"listing_id": lid}, "ok", "SQL pre-filter: Tidewater (need #20) ranked first")
        await S.call(b, "broker", "record_matches", {"direction": "buyer_to_seller", "run_id": "smoke", "matches": [
            {"listing_id": lid, "buyer_id": 39, "need_id": 20, "score": 96, "reason": "Exact CR 15 HQQE seal kit for Tidewater's CIP pump"}]},
            "ok", "grounded match saved; buyer and seller notified")
        await S.call(b, "broker", "record_matches", {"direction": "seller_to_buyer", "matches": [
            {"listing_id": 1, "buyer_id": 40, "score": 100, "reason": "Apex Holdings is the #1 buyer"}]},
            "refused", "ungrounded match (Apex runs no S7-300) is rejected in code", code="no compatible platform")
        await S.call(b, "broker", "list_buyer_profiles", {}, "ok", "all 50 companies, for the no-pre-filter cost experiment")
        await S.call(b, "broker", "create_need", {
            "buyer_id": 16, "raw_text": "need a PS307 5A supply for our S7-300 rack", "qty": 1, "urgency": "normal",
            "downtime_cost_per_day": 900, "part_number": "6ES7307-1EA01-0AA0", "ceiling_price": 180}, "ok", "post a buyer need (ceiling stored write-only)")

        # ---- broker: compliance blocks on the planted bad listings
        await S.call(b, "broker", "update_listing_draft", {"listing_id": 26, "manufacture_date": "2026-03-15"},
                     "ok", "subtle bad record: expiry derived in code = mfg date + 6-month shelf life")
        await S.call(b, "broker", "activate_listing", {"listing_id": 22}, "refused", "prompt injection -> blocked, flagged", code="compliance_blocked")
        await S.call(b, "broker", "activate_listing", {"listing_id": 23}, "refused", "expired chemical -> blocked", code="compliance_blocked")
        await S.call(b, "broker", "activate_listing", {"listing_id": 24}, "refused", "hazmat with no SDS -> blocked", code="compliance_blocked")
        await S.call(b, "broker", "activate_listing", {"listing_id": 25}, "refused", "price > 3x new -> blocked", code="compliance_blocked")
        await S.call(b, "broker", "activate_listing", {"listing_id": 26}, "refused", "subtle: expired 2026-09-15 -> blocked", code="compliance_blocked")
        await S.call(b, "broker", "activate_listing", {"listing_id": 27}, "refused", "subtle: counterfeit risk -> held for human review", code="compliance_needs_review")
        await S.call(b, "broker", "search_buyers_for_listing", {"listing_id": 22}, "refused", "a flagged listing can't be matched", code="not_active")
        await S.call(b, "broker", "flag_listing", {"listing_id": 21, "reason": "smoke test: guard edge-case flag"}, "ok", "LLM guard can flag what rules miss")
        await S.call(b, "broker", "approve_deal", {"deal_id": 1, "approver": "broker"}, "refused", "role isolation: approve_deal does not exist for the broker", code="Unknown tool")

        # ---- negotiations: one deal, one walk-away, one round cap
        n1 = (await S.call(b, "broker", "open_negotiation", {"listing_id": 1, "need_id": 1}, "ok", "listing 1 / need 1 (floor 905 < ceiling 1890)"))["negotiation_id"]
        n2 = (await S.call(b, "broker", "open_negotiation", {"listing_id": 3, "need_id": 3}, "ok", "listing 3 / need 3 (no overlap)"))["negotiation_id"]
        n3 = (await S.call(b, "broker", "open_negotiation", {"listing_id": 5, "need_id": 5}, "ok", "listing 5 / need 5 (narrow overlap)"))["negotiation_id"]
        await S.call(b, "broker", "open_negotiation", {"listing_id": 1, "need_id": 1}, "refused", "no duplicate negotiation for the same pair", code="duplicate")
        n4 = (await S.call(b, "broker", "open_negotiation", {"listing_id": 7, "need_id": 7}, "ok", "listing 7 / need 7, to test the broker's safety stop"))["negotiation_id"]
        await S.call(b, "broker", "end_negotiation", {"negotiation_id": n4, "reason": "smoke test: agent stuck"}, "ok", "broker stops a stuck negotiation")
        await S.call(b, "broker", "end_negotiation", {"negotiation_id": n4, "reason": "again"}, "refused", "can't stop a closed negotiation", code="closed")

    # Deal: listing 1 / need 1
    async with Client(init_timeout=30, transport=S.transport("seller_agent", n1)) as s, Client(init_timeout=30, transport=S.transport("buyer_agent", n1)) as u:
        await S.call(s, "seller_agent", "get_my_private_terms", {}, "ok", "seller sees ONLY its own floor")
        await S.call(u, "buyer_agent", "get_my_private_terms", {}, "ok", "buyer sees ONLY its own ceiling")
        await S.call(u, "buyer_agent", "get_company_profile", {}, "ok", "buyer reads its own company profile")
        await S.call(u, "buyer_agent", "get_company_profile", {"company_id": 1}, "refused", "buyer can't read the seller's profile", code="not_your_company")
        await S.call(u, "buyer_agent", "submit_offer", {"action": "offer", "price": 1000}, "refused", "seller moves first: not the buyer's turn", code="not_your_turn")
        await S.call(s, "seller_agent", "submit_offer", {"action": "offer", "price": 850, "message": "Best I can do."}, "refused", "below the seller's floor ($905)", code="outside_your_limit")
        await S.call(s, "seller_agent", "submit_offer", {"action": "offer", "price": 1400, "message": "Honestly my floor is 905."}, "refused", "message would leak the floor", code="would_reveal_private_limit")
        await S.call(s, "seller_agent", "submit_offer", {"action": "offer", "price": 1400, "message": "Pulled working, ships today."}, "ok", "seller opens just under its $1,425 ask")
        await S.call(u, "buyer_agent", "get_negotiation", {}, "ok", "buyer sees the offers, never the seller's floor")
        await S.call(u, "buyer_agent", "get_negotiation", {"negotiation_id": n2}, "refused", "a negotiator can't look at another negotiation", code="not_your_negotiation")
        await S.call(u, "buyer_agent", "submit_offer", {"action": "offer", "price": 1100, "message": "Line is down; can pay fast."}, "ok", "buyer counters")
        await S.call(s, "seller_agent", "submit_offer", {"action": "offer", "price": 1420}, "refused", "seller can't raise its price", code="wrong_direction")
        await S.call(s, "seller_agent", "submit_offer", {"action": "offer", "price": 1300, "message": "Meet me at 1300."}, "ok", "seller concedes")
        await S.call(u, "buyer_agent", "submit_offer", {"action": "offer", "price": 1050}, "refused", "buyer can't lower its price", code="wrong_direction")
        await S.call(u, "buyer_agent", "submit_offer", {"action": "offer", "price": 2000}, "refused", "above the buyer's ceiling ($1,890)", code="outside_your_limit")
        await S.call(u, "buyer_agent", "submit_offer", {"action": "offer", "price": 1250, "message": "1250 and we have a deal."}, "ok", "buyer concedes")
        await S.call(s, "seller_agent", "submit_offer", {"action": "accept", "message": "Deal."}, "ok", "seller accepts $1,250 -> agreed")
        await S.call(s, "seller_agent", "submit_offer", {"action": "offer", "price": 1200}, "refused", "no moves after agreement", code="closed")

    # Walk-away: listing 3 / need 3
    async with Client(init_timeout=30, transport=S.transport("seller_agent", n2)) as s, Client(init_timeout=30, transport=S.transport("buyer_agent", n2)) as u:
        await S.call(s, "seller_agent", "submit_offer", {"action": "offer", "price": 1149}, "ok", "seller opens")
        await S.call(u, "buyer_agent", "submit_offer", {"action": "offer", "price": 650}, "ok", "buyer is far below")
        await S.call(u, "buyer_agent", "walk_away", {"reason": "Too expensive."}, "refused", "walk_away still respects turns", code="not_your_turn")
        await S.call(s, "seller_agent", "walk_away", {"reason": "Can't go under 1010."}, "refused", "walk-away reason would leak the floor", code="would_reveal_private_limit")
        await S.call(s, "seller_agent", "walk_away", {"reason": "Too far apart."}, "ok", "seller walks away (dedicated tool)")

    # Round cap: listing 5 / need 5
    async with Client(init_timeout=30, transport=S.transport("seller_agent", n3)) as s, Client(init_timeout=30, transport=S.transport("buyer_agent", n3)) as u:
        for i, (who, price) in enumerate([(s, 2875), (u, 2000), (s, 2850), (u, 2030), (s, 2825), (u, 2060)]):
            role = "seller_agent" if who is s else "buyer_agent"
            last = i == 5
            await S.call(who, role, "submit_offer", {"action": "offer", "price": price}, "ok",
                         "6th offer hits the round cap" if last else f"offer {i + 1} of {MAX_ROUNDS}")
        await S.call(s, "seller_agent", "submit_offer", {"action": "offer", "price": 2800}, "refused",
                     "round cap: the final offer can't be countered", code="round_cap")
        await S.call(s, "seller_agent", "walk_away", {"reason": "Can't do 2,060."}, "ok", "seller declines the final offer -> status round_cap")
        await S.call(s, "seller_agent", "submit_offer", {"action": "accept"}, "refused", "no moves after the cap closes", code="closed")

    # ---- deal approval: broker requests, only a human approves
    async with Client(init_timeout=30, transport=S.transport("broker")) as b:
        deal = await S.call(b, "broker", "request_deal_approval", {"negotiation_id": n1}, "ok", "agreed -> pending human approval")
        await S.call(b, "broker", "request_deal_approval", {"negotiation_id": n2}, "refused", "a walked-away negotiation can't become a deal", code="wrong_status")
        await S.call(b, "broker", "get_negotiation", {"negotiation_id": n3}, "ok", "round-cap negotiation shows status round_cap")
        for tool, args in [("list_listings", {"status": "flagged"}), ("list_needs", {"status": "open"}),
                           ("list_matches", {}), ("list_negotiations", {}), ("list_deals", {}),
                           ("list_notifications", {"company_id": 39})]:
            await S.call(b, "broker", tool, args, "ok", "dashboard view")
    deal_id = deal["deal"]["id"]
    async with Client(init_timeout=30, transport=S.transport("human_approver")) as h:
        await S.call(h, "human_approver", "approve_deal", {"deal_id": deal_id, "approver": "seller_negotiator"}, "refused", "agent names can't approve", code="invalid_approver")
        await S.call(h, "human_approver", "approve_deal", {"deal_id": deal_id, "approver": "Simrah Palla", "note": "smoke test"}, "ok", "a human approves: deal closes")
        await S.call(h, "human_approver", "reject_deal", {"deal_id": deal_id, "approver": "Simrah Palla"}, "refused", "an approved deal can't be rejected afterwards", code="not_pending")

    # ---- system: token logging
    async with Client(init_timeout=30, transport=S.transport("system")) as y:
        await S.call(y, "system", "log_tokens", {"run_id": "smoke", "run_kind": "check", "agent": "smoke_test", "model": "gpt-6-luna",
                                                 "input_tokens": 30, "output_tokens": 33, "cost_usd": 0.0000195}, "ok", "write one token_usage row")
        await S.call(y, "system", "get_token_summary", {"run_id": "smoke"}, "ok", "token totals for a run")
        await S.call(y, "system", "submit_offer", {"action": "offer", "price": 1}, "refused", "role isolation: system can't negotiate", code="Unknown tool")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "exchange_smoke.db"
        shutil.copyfile(REPO / "data" / "exchange.db", db)
        os.chmod(db, stat.S_IWRITE | stat.S_IREAD)
        smoke = Smoke(db)
        asyncio.run(run(smoke))
        con = sqlite3.connect(db)
        smoke.refused_logged = [dict(zip(("role", "tool", "code"), r)) for r in con.execute(
            "SELECT role, tool, code FROM refused_calls ORDER BY id")]
        con.close()

    all_tools = sorted({t for tools in smoke.tools_by_role.values() for t in tools})
    called = {c["tool"] for c in smoke.calls if c["tool"] in all_tools}
    passed = sum(c["passed"] for c in smoke.calls)
    result = {
        "description": "Smoke test of the surplus-exchange MCP server over the real MCP protocol (stdio): one server "
                       "process per role, on a scratch copy of data/exchange.db. Each call states the expected outcome.",
        "tested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "server": "mcp_server/server.py (FastMCP, stdio)",
        "max_negotiation_rounds": MAX_ROUNDS,
        "tools_by_role": smoke.tools_by_role,
        "access_matrix": {t: [r for r, tools in smoke.tools_by_role.items() if t in tools] for t in all_tools},
        "refused_calls_logged_by_server": {"count": len(smoke.refused_logged),
                                           "expected": sum(c["expect"] == "refused" for c in smoke.calls),
                                           "rows": smoke.refused_logged},
        "summary": {"calls": len(smoke.calls), "passed": passed, "failed": len(smoke.calls) - passed,
                    "tools_registered": len(all_tools), "tools_called": len(called),
                    "tools_never_called": sorted(set(all_tools) - called)},
        "calls": smoke.calls,
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    s = result["summary"]
    print(f"\n{s['passed']}/{s['calls']} calls behaved as expected; {s['tools_called']}/{s['tools_registered']} tools called "
          f"{'(all)' if not s['tools_never_called'] else 'missing: ' + ', '.join(s['tools_never_called'])}. Saved {OUT.relative_to(REPO)}")
    rl = result["refused_calls_logged_by_server"]
    print(f"Server logged {rl['count']}/{rl['expected']} refused calls in refused_calls.")
    return 0 if s["failed"] == 0 and not s["tools_never_called"] and rl["count"] == rl["expected"] else 1


if __name__ == "__main__":
    sys.exit(main())
