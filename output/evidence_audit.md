# Evidence audit: Phases 7, 8 and 9 (report sections: tokenomics, safety, agent design, quality)

Rule from CLAUDE.md: a report section without proof from the real app gets at most half points. Proof means real token counts from logs or the UI, a screenshot or test of a defense actually stopping an attack, one real run traced step by step with screenshots, and real user evidence (Phase 10).

## 1. What we already had, and which section it supports

| File in `output/` | What it proves | Tokenomics | Safety | Agent design trace | Quality |
|---|---|:-:|:-:|:-:|:-:|
| `phase3_stress.json` / `.md` (59 real runs) | coverage of all 27 listings, messy inputs, made-up facts, bad records blocked with 0 model calls, negotiation limits and consistency, leak/extraction attempt, caps, permissions (21/21 out-of-role calls refused), timeouts / malformed output, cost per test | per-run token totals | attacks, malfunction, overspending | per-agent steps of every run | extraction 126/126, top-1 18/18, top-3 21/21 |
| `phase3_stress_before_fixes.*`, `phase3_stress_after_fixes.md` | what broke first and how it was fixed | | malfunction found → fixed | | |
| `concurrency_test.json` | 0 crashes at 6 requests at once (before vs. after process reuse) | | reliability | | |
| `mcp_smoke.json` (every tool, every role) | every tool, every role; refusals with exact error codes (agent names can't approve, ungrounded match rejected) | | attacks (role isolation) | tools by role | |
| `match_check_test.json` + `screenshots/phase4-matching-error.webp` | a real matching mix-up, caught by the code fact-check | | malfunction (made-up facts) | | fact-check 5/5 |
| `eval_reverse.json` | buy requests matched in reverse; 0 model calls when nothing fits | $ per need flow | overspending (code before models) | | 23/23 |
| `two_sided_test.json`, `phase5_stress.json` / `.md` | alerts, privacy, symmetry, self-match, lifecycle, need-side attacks, race, exact reset; tokens per alert event | tokens per alert event | attacks + leaks | | symmetry (max gap 5) |
| `negotiation_suite.json`, `phase6_stress.md` | end to end, leak scans (~1,000 responses), oversell/reject, concurrency, demo samples × 3, message scrub, cost cap | $ per negotiation | attacks, malfunction, overspending | | outcomes vs. expectations |
| `phase6_stress.md` section 1, `eval_demo_pair.json` | limits confirmed up front → auto-negotiate → both approve; featured pair repeated | | leak scan | the two human touchpoints | deals |
| `audit_trail.json` (append-only, ~1,000 entries) | every agent start/end, tool call and result, limit and block, per run id | | evidence of blocks | **the step-by-step trace** | |
| `runs/*.json` (CLI runs) | full step lists with tokens per agent | per-run tokens | | **traceable runs** | |
| `data_report.md`, `answer_keys.json` | data quality (11/11) and the hand-written answer keys | | | | ground truth |
| `screenshots/` (phase0–phase6) | setup, data, smoke test, CLI run, Sell result with rail + cost, blocked injection, alerts, Buy, Marketplace, negotiation live/seller view/deal | cost meter in the UI (`phase4-sell-result`, `phase6-negotiation-live`) | `phase4-blocked`, `phase6-seller-view` + `phase6-negotiation-live` | Sell result + rail | |
| `harness.md`, `design.md`, `phase6_decisions.md` | design, rules in code, decisions | | | design narrative | |

## 2. Gaps found (before this pass)

**Tokenomics**
- No cost **report**: real token counts existed but spread over five files; no average per seller flow / buy request / negotiation, no per-user or 100 / 10,000-user projection.
- The **cost-cutting experiment** (SQL pre-filter vs. no pre-filter, tokens *and* accuracy) had never been run: `list_buyer_profiles` existed for it but nothing used it.

**Safety**
- No single **`safety_tests.json`** grouping attacks / malfunction / overspending.
- Missing tests: **session budget cap** stop; **per-run token cap** stop; an agent doing the **wrong action repeatedly** (rogue offers outside its limit → refused, loop stopped). Already covered, so not redone: `approve_deal` by agents (Phase 3 #8a, 4 roles + the listing agent), negotiation floor leak (Phase 3 #6, Phase 6 leak scans), round / request caps (Phase 3 #7), per-negotiation cost cap (Phase 6).
- **Found while re-running:** since Phase 6's limits-up-front change, `/api/runs/{id}` returned the posting company's suggested floor/budget to anyone with the run id. Fixed (only the posting company gets them) and re-tested (Phase 5 stress 9/9).

**Quality (Phase 9)**
- No consolidated **`eval_matching.json`**; results were in Phase 3, Phase 5 and the match-check files.
- `eval_negotiation.json` held only the Phase 6 suite; Phase 3's 18 negotiations and the auto-negotiate runs were elsewhere, and no file showed the effect of the Phase 6 prompt fix (narrow deals walked away before it).

**Agent design trace** (not in Phases 7–9, listed so nothing is missed)
- Every run is fully logged (`audit_trail.json`, `runs/*.json`) and the Sell screenshot shows the rail, but there is **no single write-up tracing one real run** step by step (agent → tool → result → tokens) next to its screenshot.

## 3. Filled in this pass
- `scripts/prefilter_experiment.py` → `prefilter_experiment.json` (18 listings × 2 arms).
- `scripts/cost_report.py` → `tokenomics.json` + `tokenomics.md` (from real logged runs only; stated assumptions for per-user use).
- `scripts/safety_extra.py` → `safety_extra.json` (rogue negotiator, session budget, token cap).
- `scripts/consolidate_evals.py` → `safety_tests.json`, `eval_matching.json`, `eval_negotiation.json` (every entry names its source file).
- Phase 6 suite and Phase 3/5 regressions re-run on the current code.

### Results of this pass
The numbers now live in one generated place, **`output/evidence_index.md`** (with consistency checks), so they can't drift between documents. `scripts/run_all_evidence.py` regenerates everything.

### Findings to report honestly
- **Privacy gap found and fixed:** after the limits-up-front change, run results exposed the posting company's suggested floor/budget to anyone with the run id; now only the posting company gets them (leak scan re-run: 9/9).
- **Compliance guard false positive:** "1 x 1756-L61 controller wanted as shelf spare" was flagged (1 of 21 real buy requests). Not fixed; worth one sentence in the safety/quality section (the guard errs on the side of caution).
- **Token cap accounting:** the model call that crosses the per-run token cap is stopped, but its tokens are not written to `token_usage` (at most one call per run).
- **Generous suggested budget:** with high downtime the suggested budget (85% of new) is above the seller's opening offer, so the buyer's agent accepts at once; the screenshots used an edited budget ($180).

### Screenshots still to take
- **None strictly required for Phases 7–9:** the cost meter is already visible in `phase4-sell-result` and `phase6-negotiation-live`; the defense screenshots are `phase4-blocked` (injection stopped before any model call) and the seller/buyer views (each sees only its own limit).
- **Recommended:** one **fresh Sell run in the final design** for the agent-design trace (`phase7-sell-run.webp`): Hartwell → Siemens PLC example → Find buyers, scrolled so the rail (agent steps + cost), the listing, the top buyers and the "Confirm floor" card are visible.
- **Optional:** `phase8-budget-cap.webp` (the friendly message when the session budget is reached) if you want a UI screenshot for overspending; the test evidence already covers it.

## 4. Still open after this pass
- **Agent design trace** write-up of one real run (see above). Optional: a fresh Sell screenshot in the final design.
- **Impact (Phase 10):** a real user trying it, timed, and sourced numbers to replace the placeholder carbon factors.
- **Report and slides (Phase 11)** that cite these files.
