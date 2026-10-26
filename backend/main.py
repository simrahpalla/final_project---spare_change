"""FastAPI backend for Surplus Exchange. It also serves the built React dashboard.

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
from pydantic import BaseModel
from pydantic_ai import Agent

import audit
import config
from agents import Exchange
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


app = FastAPI(title="Surplus Exchange", lifespan=lifespan)
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
    result = await agent.run("Say hello to Surplus Exchange.")
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


@app.post("/api/negotiations")
async def negotiate(body: NegotiationIn) -> dict:
    """Seller agent vs buyer agent for one listing / need. A deal waits for human approval."""
    return await _run(lambda ex: ex.run_negotiation(body.listing_id, body.need_id))


@app.post("/api/reset")
async def reset() -> dict:
    """Restore the working database from the original. Refused while runs are in progress."""
    if runtime.active_runs:
        raise HTTPException(409, f"{runtime.active_runs} run(s) in progress. Try again when they finish.")
    reset_working_db(config.ORIGINAL_DB, config.WORKING_DB)
    audit.log("reset-" + uuid.uuid4().hex[:8], "system", "reset", result="working copy restored from the original")
    return {"ok": True, "message": "Working database restored from data/exchange.db."}


# Serve the built dashboard last, so /api routes take priority.
if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="dashboard")
else:
    @app.get("/")
    def no_frontend() -> dict:
        return {"error": "frontend/dist is missing. Run `npm install && npm run build` in frontend/."}
