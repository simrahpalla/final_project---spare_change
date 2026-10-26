# Phase 6: morning summary

Overnight run, 2026-10-26, about 00:50–02:50. Branch **`phase6`** (not merged, nothing pushed). Phase 6 itself took about 1 hour 5 minutes of the 4-hour timebox (started 01:43). **The LLM buyer works reliably, so the rule-based fallback was not needed.**

## What works

- **Phase 5 fixes 1–3 (+4)**, committed first: race re-check, double-submit guard, quantity/price caps, sold-listing wording. Phase 5 stress test went from 6/9 to **9/9**.
- **Starting a negotiation** from a match alert (bell), a Buy match, a Sell match with an open need, or **Ready to start** on the Negotiations tab. The starting company reviews **its own** floor/budget first ("Only your agent sees this."). Units are locked at once.
- **Live view** (polls every second): seller bubbles left, buyer right, "Round X of N", a price-by-round chart with **only the viewer's own limit line**, the viewer's own agent's **private reason** under each of its moves, and the viewer's own agent's **blocked moves** (dashed red), never the other side's.
- **Outcomes:** deal card with price, quantity, impact line and the result against **your own** limit ("$495 above your floor" / "$490 under your budget"). **Each company approves its own side; nothing closes until both do.** Approved → units sold (listing *sold* when none are left), need *filled*, related match alerts closed. Reject → nothing sold, listing back on the market. Walk-away / round cap → plain-English reason and the next-best match with a Start button.
- **Limits and cost:** 3 negotiations at once, the rest show **Queued**. Per-negotiation cap $0.05 / 80k tokens. The rail's cost meter shows each negotiation's cost (about $0.0006–$0.003 each).
- **Message safety:** a message with the agent's own limit is refused; every money figure (and either limit as a bare number) becomes `[price]` before it is saved or shown.
- **Demo samples** (Negotiations tab, "Ready to start"): Hartwell → Riverbend (clear deal), Hartwell → Prairie Packaging (narrow deal), Summit → Ironclad (clear), Redwood → Coastal Electronics (narrow), and **Cascade Paper & Board** (new 6th demo account) → Northwoods Pulp (walk-away).

## Test results

| Test | Result |
|---|---|
| `scripts/test_negotiation.py` (Phase 6, real API) → `output/eval_negotiation.json`, `output/phase6_stress.md` | **29/29** |
| 1. End to end: seller posts → buyer alerted → negotiate → both approve → listing sold, need filled, alerts closed | 10/10 |
| 2. Leak scan: every API response either company saw (~980), every message, note and alert; third company refused (403) | 0 leaks |
| 3. Oversell (units locked, duplicate refused) and reject path (listing back to active, next-best offered) | 5/5 |
| 4. 5 started at once: 2 waited in the queue, never more than 3 at once, all finished, prices inside both limits | 3/3 |
| 5. Demo samples × 3 runs | **15/15 as expected** (clear deals $1,390–1,425 and $975–985; narrow $122–125 and $250–255; walk-away 3/3) |
| 6. Message with own limit blocked; other limit and figures scrubbed; cost cap stops safely | 3/3 |
| MCP smoke (46 tools, all roles) | **100/100** |
| Regression: Phase 5 stress / two-sided / match check / data checks | 9/9 · 17/17 · 5/5 · 8/8 |
| Regression: Phase 3 concurrency (27 jobs at 6 at once, incl. 4 negotiations) → `output/phase6_regression_phase3.json` | 27/27, 0 crashes |

**Spend:** about **$0.26 and ~2.2M tokens** for the whole overnight session (estimated from each test's logged spend; the full Phase 6 suite was $0.038 / 312k tokens). Far below the $2.00 / 10M cap, so no test was skipped.

## What failed along the way (all fixed, details in the decisions log)

- **Narrow deal walked away 3/3** in the first repeat runs: the buyer agent quit at round 6 when a final offer at its budget would have closed. Fixed in both negotiator prompts ("with your last offer, make your best offer within your limit"), now 3/3 deals.
- **Queue display:** five simultaneous starts all saw a free slot, so none showed "Queued". Fixed: a negotiation shows Queued until it holds a slot.
- **Busy pair said "budget locked"** instead of "already in a negotiation". Fixed (check before saving the limit).
- **Two test-side bugs** (the race-test case and a leak-scan false positive), fixed in the tests, not the app.

## Decisions I made without you (see `output/phase6_decisions.md`, items marked **Q**)

1. **No low temperature:** `gpt-6-luna` is a reasoning model and ignores `temperature`. Consistency comes from the prompts, the code rules, and samples whose outcome follows from the limits (measured: 15/15).
2. **Messages carry no money figures** (scrubbed to `[price]`); the price is the offer's own field. Blocking a message that hit the *other* side's limit would itself tell the agent that number.
3. **A request without a max price can't be negotiated** until the buyer sets one (the seller sees "the buyer hasn't set a budget yet"), rather than inventing a budget.
4. **Added a 6th demo account (Cascade Paper & Board)** for the walk-away sample, since none of the 5 featured accounts had a no-overlap pair.
5. **One alert per buyer per listing** even if the buyer has two needs the listing fills.
6. **Partial quantities:** selling 1 of 3 units leaves the listing active with 2.

## What you need to do in the morning

1. **Review and merge the branch** (from the repo folder):
   - `git log --oneline main..phase6` (4 commits)
   - `git checkout main` then `git merge phase6`
2. **Start the app**, then click **Reset demo**.
3. **Screenshots** (`output/screenshots/`):
   - **phase6-negotiation-live:** as Hartwell, Negotiations → Ready to start → Prairie Packaging → Start. Capture while the bubbles are appearing (it takes about 20 s, 5–6 rounds).
   - **phase6-seller-view** and **phase6-buyer-view**, the same negotiation: when it ends, capture Hartwell's view ("Your floor $122"), then switch to **Prairie Packaging** (account menu → Show all companies) and capture its view ("Your budget $131"). Each shows only its own limit and private reasons.
   - **phase6-deal-approved:** approve as Prairie Packaging, switch back to Hartwell, approve → "Deal closed · Both companies approved".
   - **phase6-offer-blocked:** see below.
4. **About phase6-offer-blocked:** the display is built and tested. Blocked moves come from the server's refusal log and are shown only to the blocked side. But after the prompt fix the agents stayed inside their limits in every final run: 0 blocked moves in 24 negotiations. Options:
   - (a) Run a few narrow negotiations (Prairie Packaging, Coastal Electronics) and capture one if it happens.
   - (b) Use the automated evidence instead: `phase6_stress.md` section 6, where a message containing the agent's own floor is refused by code.
   - (c) Ask me for a real-user way to trigger it. I didn't add one overnight, because a "force a blocked move" switch would be a feature only for grading.
5. **Anything to review:** the **Q** items above, and whether you're happy with the new demo account and the message-scrub rule.
6. `impact_research.md` at the repo root is still untracked. I never touched it.
