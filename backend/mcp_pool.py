"""Persistent MCP connections: started once, reused by every run.

Starting an MCP server process costs ~3 s (loading fastmcp), more on a OneDrive/antivirus machine. So:
- The backend starts ONE process per shared role (broker, system, human_approver) at startup, and every
  run reuses them. Only that first start gets the long STARTUP_TIMEOUT (30 s).
- Negotiator processes are bound to one negotiation (that is how a side can read only ITS OWN limit), so
  they are started when a negotiation opens and reused for all of its turns.
- Every code call on a shared connection holds that connection's lock for the call itself (milliseconds),
  has a CALL_TIMEOUT (15 s), and on a timeout or dropped connection reconnects ONCE (logged in the audit
  trail as mcp_reconnect) before giving up with McpUnavailable (a friendly message).
"""

import asyncio
import json
import time

from pydantic_ai.mcp import MCPToolset, StdioTransport

import audit
import config

STARTUP_TIMEOUT = 30  # seconds for a server process to start (first start only)
CALL_TIMEOUT = 15     # seconds for one tool call
SHARED_ROLES = ("broker", "system", "human_approver")


class McpUnavailable(Exception):
    """The tool server didn't answer, even after one reconnect."""

    friendly = "The marketplace database service isn't responding. Nothing was changed. Please try again in a minute."


def mcp_transport(role: str, negotiation_id: int | None = None) -> StdioTransport:
    """Launch spec for one MCP server process. The Portkey key is NOT passed to it."""
    env = {"SURPLUS_ROLE": role, "SURPLUS_DB": str(config.WORKING_DB), "FASTMCP_LOG_LEVEL": "WARNING",
           "MAX_NEGOTIATION_ROUNDS": str(config.MAX_NEGOTIATION_ROUNDS)}
    if negotiation_id:
        env["SURPLUS_NEGOTIATION_ID"] = str(negotiation_id)
    return StdioTransport(command=str(config.MCP_PYTHON), args=[str(config.MCP_SERVER)], env=env, cwd=str(config.REPO_DIR))


def as_dict(res) -> dict:
    if isinstance(res, dict):
        return res.get("result", res) if set(res) == {"result"} else res
    if isinstance(res, str):
        try:
            return as_dict(json.loads(res))
        except ValueError:
            return {"ok": False, "message": res}
    return {"result": res}


class RoleConnection:
    """One MCP server process for one role (optionally bound to one negotiation)."""

    def __init__(self, role: str, negotiation_id: int | None = None):
        self.role, self.negotiation_id = role, negotiation_id
        self.label = f"{role}:{negotiation_id}" if negotiation_id else role
        self.toolset = MCPToolset(mcp_transport(role, negotiation_id), id=self.label.replace(":", "_"),
                                  init_timeout=STARTUP_TIMEOUT, read_timeout=CALL_TIMEOUT)
        self.lock = asyncio.Lock()
        self.reconnects = 0
        self.started = False

    async def start(self, attempts: int = 2) -> None:
        for attempt in range(1, attempts + 1):
            try:
                await self.toolset.__aenter__()
                self.started = True
                return
            except Exception:  # noqa: BLE001 - one retry, then raised
                if attempt == attempts:
                    raise
                await asyncio.sleep(2)

    async def stop(self) -> None:
        if self.started:
            self.started = False
            try:
                await self.toolset.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001 - shutting down anyway
                pass

    async def _reconnect(self, tool: str, error: Exception, run_id: str | None) -> None:
        self.reconnects += 1
        audit.log(run_id or "mcp-pool", f"mcp:{self.label}", "mcp_reconnect", tool=tool,
                  error=f"{type(error).__name__}: {error}", result=f"reconnect #{self.reconnects}")
        await self.stop()
        await self.start()

    async def call(self, tool: str, args: dict, run_id: str | None = None) -> dict:
        """A code-made tool call: 15 s timeout, one reconnect, then McpUnavailable."""
        async with self.lock:
            for attempt in (1, 2):
                try:
                    if not self.started:
                        await self.start()
                    return as_dict(await asyncio.wait_for(self.toolset.direct_call_tool(tool, args), CALL_TIMEOUT))
                except Exception as e:  # noqa: BLE001 - timeouts and dropped connections
                    if attempt == 2:
                        audit.log(run_id or "mcp-pool", f"mcp:{self.label}", "mcp_unavailable", tool=tool,
                                  error=f"{type(e).__name__}: {e}")
                        raise McpUnavailable(f"{self.label}.{tool}: {type(e).__name__}: {e}") from e
                    await self._reconnect(tool, e, run_id)


class McpPool:
    """The shared, long-lived connections. status: starting -> ready (or failed)."""

    def __init__(self, roles=SHARED_ROLES):
        self.conns = {r: RoleConnection(r) for r in roles}
        self.status, self.error, self.startup_seconds = "starting", None, None

    def __getitem__(self, role: str) -> RoleConnection:
        return self.conns[role]

    async def start(self) -> None:
        t0 = time.perf_counter()
        try:
            await asyncio.gather(*(c.start() for c in self.conns.values()))
            self.status = "ready"
        except Exception as e:  # noqa: BLE001 - reported by /api/health
            self.status, self.error = "failed", f"{type(e).__name__}: {e}"
        self.startup_seconds = round(time.perf_counter() - t0, 1)
        audit.log("mcp-pool", "system", "mcp_startup", result=self.info())

    async def stop(self) -> None:
        await asyncio.gather(*(c.stop() for c in self.conns.values()))
        self.status = "stopped"

    def info(self) -> dict:
        return {"status": self.status, "error": self.error, "startup_seconds": self.startup_seconds,
                "roles": {r: {"started": c.started, "reconnects": c.reconnects} for r, c in self.conns.items()}}
