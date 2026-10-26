r"""Concurrency test: shared MCP processes (through the backend API) vs one set of processes per run.

    .venv\Scripts\python.exe scripts\concurrency_test.py                  # backend at 2 and 6, process-per-run at 6
    .venv\Scripts\python.exe scripts\concurrency_test.py --modes backend --levels 6

The same 27 jobs run at each concurrency level: 23 seller flows (listings 2-27 except the 4 negotiated
listings) and 4 negotiations (1/1, 3/3, 5/5, 11/11).
- backend: starts the real FastAPI backend (uvicorn) on a scratch copy of the DB, waits for /api/health to
  report the MCP tools ready, then fires the jobs at /api/seller-flow and /api/negotiations.
- process: the old way, each job in its own process that starts its own MCP servers (scripts/_stress_worker.py).
A "crash" is an exception, an HTTP 5xx, or a run that ended in an unexpected error. A friendly error
("the AI service didn't respond…") is counted separately.
Writes output/concurrency_test.json and a "Concurrency" section in output/phase3_stress.md.
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
from datetime import datetime, timezone
from pathlib import Path

import urllib.error
import urllib.request

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from stress_phase3 import PY, run_worker  # noqa: E402

OUT_JSON, MD = REPO / "output" / "concurrency_test.json", REPO / "output" / "phase3_stress.md"
NEGOTIATIONS = [(1, 1), (3, 3), (5, 5), (11, 11)]
SELLER = [i for i in range(2, 28) if i not in {n[0] for n in NEGOTIATIONS}]
PORT = 8765

# Recorded before process reuse (process-per-run, pydantic-ai's 5 s MCP startup timeout).
BEFORE = [
    {"setup": "process-per-run, 5 s startup timeout", "concurrency": 6, "jobs": 13, "crashes": 12,
     "source": "first stress attempt: 12/13 'Client failed to connect: Failed to initialize'"},
    {"setup": "process-per-run, 5 s startup timeout", "concurrency": 2, "jobs": 59, "crashes": 3,
     "source": "stress run before fixes: 3/59 'MCPError: Connection closed' (output/phase3_stress_before_fixes.md)"},
]


def http(method: str, url: str, body: dict | None = None, timeout: float = 900) -> tuple[int, dict]:
    """Tiny JSON HTTP client (standard library only)."""
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


async def ahttp(method: str, url: str, body: dict | None = None, timeout: float = 900) -> tuple[int, dict]:
    return await asyncio.to_thread(http, method, url, body, timeout)


def jobs() -> list[tuple[str, dict]]:
    return ([(f"listing {i}", {"mode": "seller", "listing_id": i}) for i in SELLER]
            + [(f"negotiate {l}/{n}", {"mode": "negotiate", "listing_id": l, "need_id": n}) for l, n in NEGOTIATIONS])


def classify(outcome: str | None, crashed: bool) -> str:
    if crashed:
        return "crash"
    o = outcome or ""
    if o.startswith("error: something went wrong"):
        return "crash"  # caught, but an unexpected error
    if o.startswith("error:"):
        return "friendly_error"
    return "ok"


def kill_tree(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        os.killpg(os.getpgid(pid), 9)


async def run_backend(level: int) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="sx_conc_"))
    db, audit_path = tmp / "w.db", tmp / "audit.json"
    shutil.copyfile(REPO / "data" / "exchange.db", db)
    os.chmod(db, stat.S_IWRITE | stat.S_IREAD)
    env = {**os.environ, "SURPLUS_DB": str(db), "SURPLUS_AUDIT": str(audit_path), "PYTHONIOENCODING": "utf-8"}
    log = open(tmp / "uvicorn.log", "w", encoding="utf-8")
    proc = subprocess.Popen([str(PY), "-m", "uvicorn", "main:app", "--app-dir", "backend", "--port", str(PORT)],
                            cwd=str(REPO), env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
    base = f"http://127.0.0.1:{PORT}"
    t0 = time.time()
    startup, mcp = None, {}
    results = []
    try:
        if True:
            while time.time() - t0 < 180:
                try:
                    mcp = (await ahttp("GET", f"{base}/api/health", timeout=5))[1]["mcp"]
                    if mcp["status"] != "starting":
                        break
                except (OSError, KeyError, ValueError):
                    pass
                await asyncio.sleep(0.5)
            startup = round(time.time() - t0, 1)
            print(f"  backend up in {startup}s, tools {mcp.get('status')} (MCP startup {mcp.get('startup_seconds')}s)", flush=True)
            sem = asyncio.Semaphore(level)

            async def one(label, spec):
                async with sem:
                    s = time.time()
                    path = "/api/negotiations" if spec["mode"] == "negotiate" else "/api/seller-flow"
                    body = {k: v for k, v in spec.items() if k != "mode"}
                    try:
                        status, data = await ahttp("POST", base + path, body)
                        crashed = status >= 500
                        outcome = data.get("outcome") or data.get("detail")
                    except Exception as e:  # noqa: BLE001
                        crashed, outcome, data = True, f"{type(e).__name__}: {e}", {}
                    kind = classify(outcome, crashed)
                    print(f"  [{kind:<14}] {label:<18} {time.time() - s:5.0f}s  {str(outcome)[:70]}", flush=True)
                    return {"job": label, "result": kind, "outcome": outcome, "seconds": round(time.time() - s, 1),
                            "cost_usd": (data.get("totals") or {}).get("cost_usd", 0)}

            t1 = time.time()
            results = await asyncio.gather(*(one(l, s) for l, s in jobs()))
            wall = round(time.time() - t1, 1)
    finally:
        kill_tree(proc.pid)
        log.close()
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else []
    reconnects = [e for e in audit if e["action"] == "mcp_reconnect"]
    unavailable = [e for e in audit if e["action"] == "mcp_unavailable"]
    con = sqlite3.connect(db)
    refused = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='refused_calls'").fetchone()[0]
    con.close()
    shutil.rmtree(tmp, ignore_errors=True)
    return summarize("shared MCP processes via backend API (30 s first start, 15 s per call, 1 reconnect)", level, results,
                     wall, startup_seconds=startup, mcp_startup_seconds=mcp.get("startup_seconds"),
                     reconnects=len(reconnects), unavailable=len(unavailable), refused_table=bool(refused))


async def run_process(level: int) -> dict:
    sem = asyncio.Semaphore(level)
    t1 = time.time()
    raw = await asyncio.gather(*(run_worker(sem, spec, label) for label, spec in jobs()))
    wall = round(time.time() - t1, 1)
    results = [{"job": r["label"], "result": classify((r.get("result") or {}).get("outcome"), r.get("crashed", False)),
                "outcome": (r.get("result") or {}).get("outcome") or r.get("error"), "seconds": r["seconds"],
                "cost_usd": r["tokens"]["cost_usd"]} for r in raw]
    return summarize("process-per-run (30 s startup timeout, no reuse)", level, results, wall)


def summarize(setup: str, level: int, results: list, wall: float, **extra) -> dict:
    count = lambda k: sum(r["result"] == k for r in results)  # noqa: E731
    lat = sorted(r["seconds"] for r in results)
    return {"setup": setup, "concurrency": level, "jobs": len(results), "ok": count("ok"), "crashes": count("crash"),
            "friendly_errors": count("friendly_error"), "wall_seconds": wall,
            "median_job_seconds": lat[len(lat) // 2] if lat else None, "cost_usd": round(sum(r["cost_usd"] or 0 for r in results), 4),
            "crash_details": [f"{r['job']}: {r['outcome']}" for r in results if r["result"] != "ok"], **extra, "jobs_detail": results}


def write_section(runs: list) -> None:
    rows = ["| Setup | At once | Jobs | Crashes | Friendly errors | Reconnects | Wall time | Median job | Source |",
            "|---|---|---|---|---|---|---|---|---|"]
    for b in BEFORE:
        rows.append(f"| **Before:** {b['setup']} | {b['concurrency']} | {b['jobs']} | **{b['crashes']}** ({b['crashes'] / b['jobs']:.0%}) | — | — | — | — | {b['source']} |")
    for r in runs:
        tag = "**After:**" if r["setup"].startswith("shared") else "Interim:"
        rows.append(f"| {tag} {r['setup']} | {r['concurrency']} | {r['jobs']} | **{r['crashes']}** ({r['crashes'] / r['jobs']:.0%}) | "
                    f"{r['friendly_errors']} | {r.get('reconnects', '—')} | {r['wall_seconds']} s | {r['median_job_seconds']} s | this run |")
    backend = [r for r in runs if r["setup"].startswith("shared")]
    notes = [f"- Backend startup: MCP tools ready after {r['mcp_startup_seconds']} s (once, then reused by all {r['jobs']} jobs)."
             for r in backend[:1]]
    notes.append("- **Bug this test caught (fixed):** the first run at 6 at once had 26/27 requests refused with \"tools failed to "
                 "start\". /api/health reported ready a moment before the agents were built, so requests arriving in that window "
                 "were refused. Fix: build the agents before the pool can report ready (backend/main.py `Runtime.startup`). "
                 "Both runs above are after the fix.")
    for r in runs:
        if r["crash_details"]:
            notes.append(f"- {r['setup']} @ {r['concurrency']}: " + "; ".join(x[:110] for x in r["crash_details"][:6]))
    section = ("<!-- concurrency:start -->\n## Concurrency: crash counts before vs. after process reuse\n\n"
               f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `scripts/concurrency_test.py`. Same 27 jobs "
               "(23 seller flows + 4 negotiations) at each level. **Before** numbers were recorded in the earlier stress runs "
               "(process-per-run, 5 s startup timeout). **After** sends the jobs through the backend API, which starts the MCP "
               "processes once and reuses them.\n\n" + "\n".join(rows) + "\n\n" + "\n".join(notes) + "\n<!-- concurrency:end -->\n")
    md = MD.read_text(encoding="utf-8") if MD.exists() else ""
    md = re.sub(r"<!-- concurrency:start -->.*?<!-- concurrency:end -->\n?", "", md, flags=re.S)
    MD.write_text(md.rstrip() + "\n\n" + section, encoding="utf-8")


async def main(args) -> int:
    if args.section_only:  # rewrite the phase3_stress.md section from the saved JSON (e.g. after a stress rerun)
        write_section(json.loads(OUT_JSON.read_text(encoding="utf-8"))["runs"])
        print("Rewrote the Concurrency section from output/concurrency_test.json")
        return 0
    runs = []
    for mode in args.modes.split(","):
        for level in [int(x) for x in args.levels.split(",")]:
            if mode == "process" and level not in args.process_levels:
                continue
            print(f"\n=== {mode} @ {level} at once ===", flush=True)
            runs.append(await (run_backend(level) if mode == "backend" else run_process(level)))
            r = runs[-1]
            print(f"  -> {r['ok']}/{r['jobs']} ok, {r['crashes']} crash(es), {r['friendly_errors']} friendly error(s), "
                  f"wall {r['wall_seconds']}s", flush=True)
    OUT_JSON.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "before": BEFORE, "runs": runs}, indent=2), encoding="utf-8")
    write_section(runs)
    print("\nWrote output/concurrency_test.json and the Concurrency section of output/phase3_stress.md")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--modes", default="backend,process")
    p.add_argument("--levels", default="2,6")
    p.add_argument("--process-levels", type=lambda s: [int(x) for x in s.split(",")], default=[6])
    p.add_argument("--section-only", action="store_true", help="only rewrite the report section from the saved JSON")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(main(p.parse_args())))
