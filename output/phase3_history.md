# Phase 3 history (recorded 2026-10-26, before Phases 4-6)

Kept for the report: how the first Phase 3 stress run compared with the fixed code, and the concurrency crash counts before vs. after MCP process reuse. The current results are in `phase3_stress.md` (regenerated on the final code by `scripts/run_all_evidence.py`).

## Concurrency: crash counts before vs. after process reuse

Generated 2026-10-26T01:50:57+00:00 by `scripts/concurrency_test.py`. Same 27 jobs (23 seller flows + 4 negotiations) at each level. **Before** numbers were recorded in the earlier stress runs (process-per-run, 5 s startup timeout). **After** sends the jobs through the backend API, which starts the MCP processes once and reuses them.

| Setup | At once | Jobs | Crashes | Friendly errors | Reconnects | Wall time | Median job | Source |
|---|---|---|---|---|---|---|---|---|
| **Before:** process-per-run, 5 s startup timeout | 6 | 13 | **12** (92%) | — | — | — | — | first stress attempt: 12/13 'Client failed to connect: Failed to initialize' |
| **Before:** process-per-run, 5 s startup timeout | 2 | 59 | **3** (5%) | — | — | — | — | stress run before fixes: 3/59 'MCPError: Connection closed' (output/phase3_stress_before_fixes.md) |
| **After:** shared MCP processes via backend API (30 s first start, 15 s per call, 1 reconnect) | 2 | 27 | **0** (0%) | 0 | 0 | 44.9 s | 1.8 s | this run |
| **After:** shared MCP processes via backend API (30 s first start, 15 s per call, 1 reconnect) | 6 | 27 | **0** (0%) | 0 | 0 | 20.3 s | 2.0 s | this run |
| Interim: process-per-run (30 s startup timeout, no reuse) | 6 | 27 | **0** (0%) | 0 | — | 91.2 s | 16.3 s | this run |

- Backend startup: MCP tools ready after 2.1 s (once, then reused by all 27 jobs).
- **Bug this test caught (fixed):** the first run at 6 at once had 26/27 requests refused with "tools failed to start". /api/health reported ready a moment before the agents were built, so requests arriving in that window were refused. Fix: build the agents before the pool can report ready (backend/main.py `Runtime.startup`). Both runs above are after the fix.
<!-- concurrency:end -->

## Summary: first run vs. final code

| | First run | After the 6 fixes | Final (plus process reuse) |
|---|---|---|---|
| Strict PASS | 5/13 | 12/13 (the 1 FAIL was a checker bug) | **13/13** |
| Listing fields correct | 147/150 | 126/126 | **126/126** |
| Top-1 / top-3 matches | 18/18 · 21/21 | 18/18 · 21/21 | **18/18 · 21/21** |
| Obvious bad records with 0 model calls | 1/4 | 4/4 | **4/4** |
| Deal rate on deal-likely pairs | 50% | 100% | **100%** |
| Same outcome in all 3 runs | 83% | 83% | **100%** |
| Crashes in 59 runs (2 at once) | 3 | 0 | **0** |
| Cost of the whole suite | $0.070 | $0.065 | **$0.065** |

Earlier reports are kept as `output/phase3_stress_before_fixes.md` (first run, with a hand-reviewed analysis) and `output/phase3_stress_after_fixes.md`.

**One remaining observation (not a FAIL):** pair 2/17 (floor $2,610, ceiling $2,690, a $80 gap) ends with the buyer walking away in all 3 runs. A deal was possible but narrow, and the buyer is a low-urgency shelf spare. That's sensible behaviour, but a stronger seller concession schedule might close it. Worth revisiting in Phase 6 or Phase 9.
