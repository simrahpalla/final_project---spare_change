"""FastAPI backend for Surplus Exchange. It also serves the built React dashboard.

Start from the repo folder (with the venv active):
    uvicorn main:app --app-dir backend --port 8000
then open http://localhost:8000.

How it fits together
- All marketplace data goes through the surplus-exchange MCP server (added in Phase 2). The
  backend never opens the database itself.
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
from pydantic_ai import Agent

import audit
import config
from llm import make_model, usage_breakdown


class AgentLoop:
    """A private asyncio loop in a daemon thread (Proactor on Windows, so subprocesses work)."""

    def __init__(self):
        self.loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name="agent-loop", daemon=True)

    def start(self) -> None:
        self.thread.start()

    async def run(self, coro):
        """Run a coroutine on the agent loop and await its result from the request loop."""
        return await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, self.loop))

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)


agent_loop = AgentLoop()


@asynccontextmanager
async def lifespan(_: FastAPI):
    agent_loop.start()
    yield
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


# Serve the built dashboard last, so /api routes take priority.
if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="dashboard")
else:
    @app.get("/")
    def no_frontend() -> dict:
        return {"error": "frontend/dist is missing. Run `npm install && npm run build` in frontend/."}
