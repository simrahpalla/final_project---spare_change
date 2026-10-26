"""FastAPI backend for Spare Change. It also serves the built React dashboard.

Start from the repo folder (with the venv active):
    uvicorn main:app --app-dir backend --port 8000
then open http://localhost:8000.

How it fits together
- All marketplace data goes through the surplus-exchange MCP server. The backend never opens the
  database itself (reset only copies the original file over the working copy).
- MCP processes are started ONCE, at startup, one per shared role (broker, system, human_approver), and
  every run reuses them (backend/mcp_pool.py). Startup happens in the background, so the page loads at
  once and shows "Starting up…" until /api/health reports the tools are ready.
- MCP stdio servers are subprocesses. On Windows, uvicorn can run the app on an event loop that
  cannot start subprocesses, so MCP and agent work runs on a private event loop in a background
  thread (AgentLoop). Routes hand work to it and await the result.
- frontend/dist (the built dashboard) is mounted at "/", so one command starts everything.
"""

import asyncio
import os
import sys
import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent

import audit
import config
from agents import Exchange, RunState
from llm import make_model, usage_breakdown
from mcp_pool import McpPool

sys.path.insert(0, str(config.REPO_DIR / "scripts"))
from reset_db import reset as reset_working_db  # noqa: E402


class AgentLoop:
    """A private asyncio loop in a daemon thread (Proactor on Windows, so subprocesses work)."""

    def __init__(self):
        self.loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name="agent-loop", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def submit(self, coro):
        """Schedule a coroutine on the agent loop without waiting (returns a concurrent future)."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    async def run(self, coro):
        """Run a coroutine on the agent loop and await its result from the request loop."""
        return await asyncio.wrap_future(self.submit(coro))

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)


class Runtime:
    """Long-lived state: the MCP pool and the agents, created once on the agent loop."""

    def __init__(self):
        self.pool: McpPool | None = None
        self.exchange: Exchange | None = None
        self.active_runs = 0

    async def startup(self) -> None:
        pool = McpPool()
        try:
            # Build the agents BEFORE the pool can report "ready", so no request ever sees ready-but-no-agents.
            exchange = Exchange(pool=pool)
        except Exception as e:  # noqa: BLE001 - e.g. missing PORTKEY_API_KEY; shown in /api/health
            pool.status, pool.error = "failed", f"{type(e).__name__}: {e}"
            self.pool = pool
            return
        self.exchange, self.pool = exchange, pool
        self.neg_slot = asyncio.Semaphore(config.MAX_CONCURRENT_NEGOTIATIONS)  # created on the agent loop
        await pool.start()

    async def shutdown(self) -> None:
        if self.pool:
            await self.pool.stop()

    def require_ready(self) -> Exchange:
        if not self.pool or self.pool.status == "starting":
            raise HTTPException(503, "Starting up… the marketplace tools are still loading. Try again in a few seconds.")
        if self.pool.status != "ready" or not self.exchange:
            raise HTTPException(503, f"The marketplace tools failed to start: {self.pool.error}")
        return self.exchange


agent_loop = AgentLoop()
runtime = Runtime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    agent_loop.start()
    agent_loop.submit(runtime.startup())  # in the background: the page loads immediately
    yield
    try:
        agent_loop.submit(runtime.shutdown()).result(timeout=15)
    except Exception:  # noqa: BLE001 - shutting down anyway
        pass
    agent_loop.stop()


app = FastAPI(title="Spare Change", lifespan=lifespan)
app.add_middleware(  # only needed for the Vite dev server; the built app is same-origin
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    """Setup status for the dashboard header. Never returns the key itself."""
    return {
        "ok": True,
        "model": config.MODEL_NAME,
        "key_found": bool(os.getenv("PORTKEY_API_KEY")),
        "key_source": config.env_source(),
        "frontend_built": config.FRONTEND_DIST.exists(),
        "mcp": runtime.pool.info() if runtime.pool else {"status": "starting"},
        "active_runs": runtime.active_runs,
    }


async def _ping_model() -> dict:
    agent = Agent(make_model(), instructions="You are a connectivity check. Reply in five words or fewer.")
    result = await agent.run("Say hello to Spare Change.")
    return {"reply": result.output, **usage_breakdown(result.usage)}


@app.post("/api/llm-check")
async def llm_check() -> dict:
    """One tiny gpt-6-luna call, to prove the key and model work. Logged to the audit trail."""
    run_id = "llm-check-" + uuid.uuid4().hex[:8]
    try:
        out = await agent_loop.run(_ping_model())
    except Exception as e:  # noqa: BLE001 - reported to the dashboard
        audit.log(run_id, "system", "llm_check", error=f"{type(e).__name__}: {e}")
        raise HTTPException(502, f"Model call failed: {type(e).__name__}: {e}") from e
    audit.log(run_id, "system", "llm_check", args={"model": config.MODEL_NAME}, result=out)
    return {"run_id": run_id, "model": config.MODEL_NAME, **out}


class SellerFlowIn(BaseModel):
    listing_id: int | None = None
    text: str | None = None
    seller_id: int | None = None


class NeedFlowIn(BaseModel):
    text: str | None = None
    buyer_id: int | None = None
    need_id: int | None = None
    max_price: float | None = Field(default=None, ge=0, le=10_000_000)
    urgency: Literal["low", "normal", "high", "line_down"] | None = None
    downtime_cost_per_day: float | None = Field(default=None, ge=0)


class NegotiationIn(BaseModel):
    listing_id: int
    need_id: int


async def _run(coro_factory):
    ex = runtime.require_ready()
    runtime.active_runs += 1
    try:
        return await agent_loop.run(coro_factory(ex))
    finally:
        runtime.active_runs -= 1


@app.post("/api/seller-flow")
async def seller_flow(body: SellerFlowIn) -> dict:
    """Pasted text (or a seeded listing) -> listing -> compliance -> matches -> price -> outreach."""
    if not body.listing_id and not (body.text is not None and body.seller_id):
        raise HTTPException(422, "Give a listing_id, or text plus seller_id.")
    return await _run(lambda ex: ex.run_seller_flow(listing_id=body.listing_id, text=body.text, seller_id=body.seller_id))


def _negotiation_public(result: dict | None) -> dict | None:
    """A negotiation run's steps hold BOTH agents' private reasoning (which may name their own limits). Outside the
    company-scoped view (/api/negotiations/{id}?company_id=) only outcome-level fields are returned."""
    if not result:
        return result
    return {k: result.get(k) for k in ("run_id", "outcome", "totals", "agent_calls", "negotiation", "deal")} | {
        "steps": [{"step": x["step"], "status": x["status"]} for x in result.get("steps", [])]}


@app.post("/api/negotiations")
async def negotiate(body: NegotiationIn) -> dict:
    """Seller agent vs buyer agent for one listing / need (CLI/tests). A deal waits for both companies' approval."""
    return _negotiation_public(await _run(lambda ex: ex.run_negotiation(body.listing_id, body.need_id, slot=runtime.neg_slot)))


@app.post("/api/reset")
async def reset() -> dict:
    """Restore the working database from the original. Refused while runs are in progress."""
    if runtime.active_runs:
        raise HTTPException(409, f"{runtime.active_runs} run(s) in progress. Try again when they finish.")
    reset_working_db(config.ORIGINAL_DB, config.WORKING_DB)
    runs.clear()
    session_impact.clear()
    audit.log("reset-" + uuid.uuid4().hex[:8], "system", "reset", result="working copy restored from the original")
    return {"ok": True, "message": "Demo data restored."}


# --------------------------------------------------------------------------- live runs (the UI polls these)

runs: dict[str, RunState] = {}          # run_id -> live state, newest last (kept small)
session_impact: dict[int, dict] = {}    # listing_id -> latest impact estimate this session
RUNS_KEPT = 50


def _register(state: RunState, coro) -> dict:
    """Start a run on the agent loop without waiting; the UI polls GET /api/runs/{run_id}."""
    runtime.require_ready()
    runs[state.run_id] = state
    while len(runs) > RUNS_KEPT:
        runs.pop(next(iter(runs)))
    runtime.active_runs += 1

    def done(fut) -> None:
        runtime.active_runs -= 1
        result = state.result or {}
        impact = next((s for s in result.get("steps", []) if s["step"] == "impact"), None)
        if impact and str(result.get("outcome", "")).startswith("listed"):
            session_impact[impact["listing_id"]] = impact
        if fut.exception() and state.status != "done":  # never leave the UI spinning
            state.status, state.result = "done", {"run_id": state.run_id, "outcome": "error: something went wrong on our "
                                                  "side. Nothing was published. Please try again.", "steps": state.steps,
                                                  "totals": state.totals(), "agent_calls": state.agent_calls}

    agent_loop.submit(coro).add_done_callback(done)
    return {"run_id": state.run_id, "status": "running"}


@app.post("/api/seller-flow/start")
async def seller_flow_start(body: SellerFlowIn) -> dict:
    """Start the seller flow and return at once with a run_id to poll."""
    if not body.listing_id and not ((body.text or "").strip() and body.seller_id):
        raise HTTPException(422, "Paste a description of the part first.")
    ex = runtime.require_ready()
    state = RunState(kind="seller_flow", subject=f"listing:{body.listing_id}" if body.listing_id else f"seller:{body.seller_id}")
    return _register(state, ex.run_seller_flow(listing_id=body.listing_id, text=body.text, seller_id=body.seller_id, state=state))


@app.post("/api/need-flow/start")
async def need_flow_start(body: NeedFlowIn) -> dict:
    """Start the buyer's wanted-post flow (need -> compliance -> reverse matching -> alerts); poll the run_id."""
    if not body.need_id and not ((body.text or "").strip() and body.buyer_id):
        raise HTTPException(422, "Describe the part you need first.")
    ex = runtime.require_ready()
    state = RunState(kind="need_flow", subject=f"need:{body.need_id}" if body.need_id else f"buyer:{body.buyer_id}")
    return _register(state, ex.run_need_flow(text=body.text, buyer_id=body.buyer_id, need_id=body.need_id,
                                             max_price=body.max_price, urgency=body.urgency,
                                             downtime_cost_per_day=body.downtime_cost_per_day, state=state))


@app.get("/api/marketplace")
async def marketplace() -> dict:
    """Public board: available listings, wanted needs (never a buyer's max price), match pairs, deal impact."""
    return await _system("get_marketplace_board")


class StartNegotiationIn(BaseModel):
    listing_id: int
    need_id: int
    company_id: int
    my_limit: float | None = Field(default=None, gt=0, le=10_000_000)


class DecisionIn(BaseModel):
    company_id: int
    note: str = Field(default="", max_length=300)


async def _tool(role: str, tool: str, **args) -> dict:
    runtime.require_ready()
    return await agent_loop.run(runtime.pool[role].call(tool, args))


def _refused(res: dict, status: int = 409) -> None:
    if not res.get("ok"):
        code = 403 if res.get("code") in ("not_yours", "not_your_negotiation") else status
        raise HTTPException(code, res.get("message", "Not allowed."))


@app.get("/api/negotiations/start-info")
async def negotiation_start_info(listing_id: int, need_id: int, company_id: int) -> dict:
    """Before starting: the pair, this company's side and ITS OWN current limit, free units, and any blocker."""
    res = await _tool("system", "get_negotiation_start", listing_id=listing_id, need_id=need_id, company_id=company_id)
    _refused(res, 404)
    return res


@app.post("/api/negotiations/start")
async def negotiation_start(body: StartNegotiationIn) -> dict:
    """The signed-in company starts a negotiation, optionally adjusting its OWN limit first. Units are locked at once;
    the agents start when one of the concurrent slots is free (until then the negotiation shows as queued)."""
    ex = runtime.require_ready()
    ids = {"listing_id": body.listing_id, "need_id": body.need_id, "company_id": body.company_id}
    info = await _tool("system", "get_negotiation_start", **ids)
    _refused(info, 404)
    if not info.get("can_start"):  # before touching the limit: a busy pair shouldn't say "your budget is locked"
        raise HTTPException(409, info.get("blocker") or "This negotiation can't start.")
    if body.my_limit is not None and body.my_limit != (info["my_limit"] or {}).get("value"):
        key = {"listing_id": body.listing_id} if info["side"] == "seller" else {"need_id": body.need_id}
        _refused(await _tool("human_approver", "set_private_limit", company_id=body.company_id, value=body.my_limit, **key), 400)
        info = await _tool("system", "get_negotiation_start", **ids)
    if not info.get("can_start"):
        raise HTTPException(409, info.get("blocker") or "This negotiation can't start.")
    if (info["my_limit"] or {}).get("value") is None:
        word = "floor" if info["side"] == "seller" else "budget"
        raise HTTPException(400, f"Set your {word} first. Only your agent sees it.")
    state = RunState(kind="negotiation", subject=f"listing:{body.listing_id}/need:{body.need_id}")
    opened = await _tool("broker", "open_negotiation", listing_id=body.listing_id, need_id=body.need_id, run_id=state.run_id)
    _refused(opened)
    nid = opened["negotiation_id"]
    queued = runtime.neg_slot.locked()
    _register(state, ex.run_negotiation(body.listing_id, body.need_id, state=state, negotiation_id=nid, slot=runtime.neg_slot))
    return {"negotiation_id": nid, "run_id": state.run_id, "queued": queued}


@app.get("/api/companies/{company_id}/negotiations")
async def company_negotiations(company_id: int) -> dict:
    """This company's negotiations (newest first) and the deals it could start."""
    mine = await _tool("system", "list_negotiations_for_company", company_id=company_id)
    pairs = await _tool("system", "list_negotiable_pairs", company_id=company_id)
    for n in mine["negotiations"]:
        st = runs.get(n["run_id"] or "")
        n["queued"] = bool(st and st.status == "running" and st.current == "queued")
        n["running"] = bool(st and st.status == "running")
    return {"negotiations": mine["negotiations"], "ready": pairs["pairs"]}


@app.get("/api/negotiations/{negotiation_id}")
async def negotiation_view(negotiation_id: int, company_id: int) -> dict:
    """One negotiation as ONE company sees it (its own limit, notes and blocked moves; never the other side's)."""
    res = await _tool("system", "get_negotiation_for_company", negotiation_id=negotiation_id, company_id=company_id)
    _refused(res, 404)
    st = runs.get(res.get("run_id") or "")
    res["live"] = ({"status": st.status, "queued": st.current == "queued", "working": st.current, "totals": st.totals()}
                   if st else None)
    return res


async def _decide(negotiation_id: int, body: DecisionIn, approve: bool) -> dict:
    view = await _tool("system", "get_negotiation_for_company", negotiation_id=negotiation_id, company_id=body.company_id)
    _refused(view, 404)
    if not view.get("deal"):
        raise HTTPException(409, "There is no deal to decide on yet.")
    me = view["listing"]["seller_name"] if view["side"] == "seller" else view["need"]["buyer_name"]
    args = {"deal_id": view["deal"]["deal_id"], "approver": f"{me} (demo user)", "side": view["side"]}
    if approve:
        res = await _tool("human_approver", "approve_deal", **args)
    else:
        res = await _tool("human_approver", "reject_deal", **args, note=body.note)
    _refused(res)
    return res


@app.post("/api/negotiations/{negotiation_id}/approve")
async def negotiation_approve(negotiation_id: int, body: DecisionIn) -> dict:
    """A person at the signed-in company approves ITS side of the deal. It closes when both sides have approved."""
    return await _decide(negotiation_id, body, True)


@app.post("/api/negotiations/{negotiation_id}/reject")
async def negotiation_reject(negotiation_id: int, body: DecisionIn) -> dict:
    """Either side rejects the deal: nothing is sold and the listing goes back on the market."""
    return await _decide(negotiation_id, body, False)


@app.get("/api/runs/{run_id}")
def run_status(run_id: str) -> dict:
    """Live progress: steps so far, the agent working now, token totals, and the result when done."""
    state = runs.get(run_id)
    if not state:
        raise HTTPException(404, "That run isn't available any more. Start a new one.")
    if state.kind == "negotiation":  # private reasoning lives only in the company-scoped view
        return {"run_id": run_id, "kind": state.kind, "status": state.status, "current": state.current,
                "steps": [{"step": x["step"], "status": x["status"]} for x in state.steps], "totals": state.totals(),
                "agent_calls": list(state.agent_calls), "result": _negotiation_public(state.result)}
    return {"run_id": run_id, "kind": state.kind, "status": state.status, "current": state.current,
            "steps": list(state.steps), "totals": state.totals(), "agent_calls": list(state.agent_calls),
            "result": state.result}


async def _system(tool: str, **args) -> dict:
    runtime.require_ready()
    return await agent_loop.run(runtime.pool["system"].call(tool, args))


@app.get("/api/companies")
async def companies() -> dict:
    """Every company, for the demo account switcher."""
    return await _system("list_companies")


@app.get("/api/companies/{company_id}")
async def company(company_id: int) -> dict:
    """What a signed-in company sees: its profile, machines, open needs, active listings and alerts."""
    profile = await _system("get_company_profile", company_id=company_id)
    if not profile.get("ok"):
        raise HTTPException(404, "No such company.")
    alerts = await _system("list_notifications", company_id=company_id)
    return {**profile, "alerts": alerts["notifications"][:10],
            "unread_alerts": sum(1 for a in alerts["notifications"] if not a["read"])}


@app.post("/api/companies/{company_id}/alerts/read")
async def alerts_read(company_id: int) -> dict:
    return await _system("mark_notifications_read", company_id=company_id)


@app.get("/api/session")
async def session() -> dict:
    """Session cost (from token_usage) and impact (from this session's listed items)."""
    tokens = await _system("get_token_summary")
    total = tokens["total"]
    impacts = list(session_impact.values())
    s = lambda k: round(sum(i.get(k) or 0 for i in impacts), 2)  # noqa: E731
    return {
        "cost_usd": total.get("cost_usd") or 0, "budget_usd": config.SESSION_BUDGET_USD,
        "requests": total.get("requests") or 0, "runs": total.get("runs") or 0,
        "impact": {"listings": len(impacts), "value_recovered": s("value_recovered"), "scrap_value": s("scrap_value_total"),
                   "kg_kept_out_of_scrap": s("kg_kept_out_of_scrap"), "est_kg_co2e_avoided": s("est_kg_co2e_avoided"),
                   "est_hazardous_disposal_avoided": s("est_hazardous_disposal_avoided"),
                   "placeholder_factors": any(i.get("placeholder_factors") for i in impacts),
                   "method": impacts[0]["method"] if impacts else None},
    }


# Serve the built dashboard last, so /api routes take priority.
if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="dashboard")
else:
    @app.get("/")
    def no_frontend() -> dict:
        return {"error": "frontend/dist is missing. Run `npm install && npm run build` in frontend/."}
