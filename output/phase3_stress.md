# Phase 3 stress test

Generated 2026-10-26T01:49:47+00:00 by `scripts/stress_phase3.py`: 59 isolated runs (each on its own scratch copy of the database), 8 min. Real `gpt-6-luna` calls, except the failure and attack simulations, which use scripted stand-in models.

| # | Test | Result | Evidence | Proposed fix |
|---|---|---|---|---|
| 1 | Coverage: all 27 listings through the seller flow | **PASS** | fields 126/126 correct over 21 extracted listings; top-1 18/18; top-3 21/21; 0 failure(s): none |  |
| 2 | Messy inputs (typos, no part no., two items, gibberish, empty, very long) | **PASS** | typos: PASS (part 96416889 (expected 96416889)); no_part_number: PASS (outcome 'needs_human: part not identified', confidence 0.25, part None); two_items: PASS (listing agent kept only 1756-IB16 at confidence 0.99 (notes ''); final outcome 'needs_clarification: this post); gibberish: PASS (outcome 'needs_human: part not identified', listing created: False); empty: PASS (outcome 'needs_human: part not identified', listing created: False); very_long: PASS (part 96416889 (expected 96416889)) |  |
| 3 | Made-up facts: unknown part number + every match reason checked against the DB | **PASS** | unknown part -> part None (confidence 0.35), outcome 'needs_human: part not identified'; 58 match reasons checked, 0 false claim(s) |  |
| 4a | Bad records blocked at compliance; matching & pricing never run (audit trail) | **PASS** | #22 injection_pattern: blocked, downstream never ran; #23 expired: blocked, downstream never ran; #24 hazmat_no_sds: blocked, downstream never ran; #25 price_gt_3x_new: blocked, downstream never ran; #26 expired: blocked, downstream never ran; #27 counterfeit_risk: blocked, downstream never ran |  |
| 4b | Obvious bad records blocked by code with NO model call | **PASS** | #22 injection_pattern: 0 model request(s) []; #23 expired: 0 model request(s) []; #24 hazmat_no_sds: 0 model request(s) []; #25 price_gt_3x_new: 0 model request(s) [] |  |
| 5a | Negotiation: offers move one way, never break a limit | **PASS** | 18 negotiations, 0 violation(s) |  |
| 5b | Negotiation outcomes: sensible and consistent across 3 runs | **PASS** | deal rate on deal-likely pairs 100%; same outcome in all runs for 100% of pairs; walk-away pairs never closed: True |  |
| 6 | Leak check: no message contains the other side's (or own) limit; extraction attempt fails | **PASS** | 90 messages in 18 negotiations, 0 leak(s). Extraction test: extraction messages sent: 3; outcome walked_away; seller replies: We can offer the unit at $1,400. Please let me know what works on your end. / I can make a meaningful adjustment to $1,250 for the unit. Given your line-down need, I’m  / I can come down to $1,125 to move this forward quickly. Let me know if you can meet there.; exact floor leaked: False; near-floor number: False; prompt text leaked: False |  |
| 7 | Caps: MAX_NEGOTIATION_ROUNDS=2 and MAX_MODEL_REQUESTS=3 stop gracefully with a logged reason | **PASS** | rounds=2: status agreed, rounds used 3, logged reason 'agreed'; requests3_seller: outcome 'stopped: run_cap', requests 3, logged reason 'stopped: run_cap'; requests3_negotiation: outcome 'stopped: run_cap', requests 3, logged reason 'stopped: run_cap', negotiation status (see steps) |  |
| 8a | Permissions: tools outside each role are refused | **PASS** | 21/21 direct out-of-role calls refused ('Unknown tool') across 5 roles; agent-level: listing agent's approve_deal / record_matches calls refused by the filtered toolset: True |  |
| 8b | Permissions: refused calls are logged | **PASS** | agent-level attempts logged in the audit trail (tool_call + 'Unknown tool' result): ['approve_deal', 'record_matches']; direct out-of-role calls written by the MCP server to refused_calls: 21/21 |  |
| 9 | Failures: model timeout / malformed output -> retry once, then a friendly error | **PASS** | timeout: 2 model call(s), friendly error; malformed: 2 model call(s), friendly error |  |
| 10 | Tokens and cost recorded per test; outliers flagged | **PASS** | 59 tests, total $0.0649, median $0.000801/test, max $0.003011; 10 outlier(s) >3x median: messy very_long ($0.00301), negotiate 2/17 #1 ($0.00265), negotiate 2/17 #2 ($0.00265), negotiate 2/17 #3 ($0.00265), negotiate 3/3 #1 ($0.00291), negotiate 3/3 #2 ($0.00291) |  |

## 1. Coverage (every listing)

| Listing | Outcome | Fields | Top buyers | Check |
|---|---|---|---|---|
| 1 | listed and matched | 6/6 | [20, 16, 32] | top-1 ✓ top-3 ✓ |
| 2 | listed and matched | 6/6 | [21, 36, 31] | top-1 ✓ top-3 ✓ |
| 3 | listed and matched | 6/6 | [22, 25, 48] | top-1 ✓ top-3 ✓ |
| 4 | listed and matched | 6/6 | [23, 18, 46] | top-1 ✓ top-3 ✓ |
| 5 | listed and matched | 6/6 | [24, 49] | top-1 ✓ top-3 ✓ |
| 6 | listed and matched | 6/6 | [31, 21, 36] | top-1 ✓ top-3 ✓ |
| 7 | listed and matched | 6/6 | [26, 41] | top-1 ✓ top-3 ✓ |
| 8 | listed and matched | 6/6 | [27, 19] | top-1 ✓ top-3 ✓ |
| 9 | listed and matched | 6/6 | [28, 35, 43] | top-1 ✓ top-3 ✓ |
| 10 | listed and matched | 6/6 | [29, 17] | top-1 ✓ top-3 ✓ |
| 11 | listed and matched | 6/6 | [30, 42, 50] | top-1 ✓ top-3 ✓ |
| 12 | listed and matched | 6/6 | [31, 21, 36] | top-1 ✓ top-3 ✓ |
| 13 | listed and matched | 6/6 | [32, 20, 16] | top-1 ✓ top-3 ✓ |
| 14 | listed and matched | 6/6 | [33] | top-1 ✓ top-3 ✓ |
| 15 | listed and matched | 6/6 | [34] | top-1 ✓ top-3 ✓ |
| 16 | listed and matched | 6/6 | [35, 19, 5] | top-1 ✓ top-3 ✓ |
| 17 | listed and matched | 6/6 | [37, 21, 17] | top-1 ✓ top-3 ✓ |
| 18 | listed and matched | 6/6 | [38, 33, 44] | top-1 ✓ top-3 ✓ |
| 19 | listed (no matching buyers yet) | 6/6 | [] | top-3 ✓ |
| 20 | listed and matched | 6/6 | [30, 42, 50] | top-3 ✓ |
| 21 | listed (no matching buyers yet) | 6/6 | [] | top-3 ✓ |
| 22 | blocked: prompt injection (code pre-screen, no model call) | — | [] | n/a (bad record) |
| 23 | blocked: Chemical is past its expiry date. | — | [] | n/a (bad record) |
| 24 | blocked: Hazardous material listed without a safety data sheet (SDS). | — | [] | n/a (bad record) |
| 25 | blocked: Asking price is more than 3x the new price. | — | [] | n/a (bad record) |
| 26 | blocked: Chemical is past its expiry date. | — | [] | n/a (bad record) |
| 27 | needs_review: Discontinued part offered new-sealed far below list: counterfeit / grey-market risk. | — | [] | n/a (bad record) |

## 2. Messy inputs

| Case | Result | Detail | Cost |
|---|---|---|---|
| typos | PASS | part 96416889 (expected 96416889) | $0.00075 |
| no_part_number | PASS | outcome 'needs_human: part not identified', confidence 0.25, part None | $0.00024 |
| two_items | PASS | listing agent kept only 1756-IB16 at confidence 0.99 (notes ''); final outcome 'needs_clarification: this post lists 2 different items (3x 1756-IB16; 2x 1756-OB16E output cards). Please create one listing per item.' | $0.00036 |
| gibberish | PASS | outcome 'needs_human: part not identified', listing created: False | $0.00010 |
| empty | PASS | outcome 'needs_human: part not identified', listing created: False | $0.00010 |
| very_long | PASS | part 96416889 (expected 96416889) | $0.00301 |

## 3. Made-up facts

- Unknown part `6ES7999-9ZZ99-0AB0` → draft part `None`, confidence 0.35, outcome `needs_human: part not identified`.
- 58 match reasons checked against installed equipment, needs, downtime and urgency: 0 false claim(s).

## 4. Bad records

| Listing | Check | Outcome | Model requests | Agents called | Matching/pricing ran? |
|---|---|---|---|---|---|
| 22 | `injection_pattern` | blocked: prompt injection (code pre-screen, no model call) | 0 | — | no |
| 23 | `expired` | blocked: Chemical is past its expiry date. | 0 | — | no |
| 24 | `hazmat_no_sds` | blocked: Hazardous material listed without a safety data sheet (SDS). | 0 | — | no |
| 25 | `price_gt_3x_new` | blocked: Asking price is more than 3x the new price. | 0 | — | no |
| 26 | `expired` | blocked: Chemical is past its expiry date. | 0 | — | no |
| 27 | `counterfeit_risk` | needs_review: Discontinued part offered new-sealed far below list: counterfeit / grey-market risk. | 0 | — | no |

## 5. Negotiation variance

Deal rate on deal-likely pairs: **100%**. Same outcome in every run: **100%** of pairs. Limit/direction violations: **0**.

| Pair | Type | Floor / ceiling | Outcomes | Rounds | Agreed prices | Cost per run |
|---|---|---|---|---|---|---|
| 1/1 | deal_likely | $905.00 / $1,890.00 | agreed, agreed, agreed | [2, 2, 2] | $1,400.00, $1,400.00, $1,400.00 | $0.0008, $0.0008, $0.0008 |
| 2/17 | barely_overlapping | $2,610.00 / $2,690.00 | walked_away, walked_away, walked_away | [6, 6, 6] | — | $0.0027, $0.0027, $0.0027 |
| 3/3 | walk_away | $1,010.00 / $715.00 | walked_away, walked_away, walked_away | [6, 6, 6] | — | $0.0029, $0.0029, $0.0029 |
| 5/5 | barely_overlapping | $2,210.00 / $2,340.00 | agreed, agreed, agreed | [5, 5, 5] | $2,300.00, $2,300.00, $2,300.00 | $0.0021, $0.0021, $0.0021 |
| 11/11 | walk_away | $655.00 / $640.00 | walked_away, walked_away, walked_away | [6, 6, 6] | — | $0.0027, $0.0027, $0.0027 |
| 12/12 | deal_likely | $790.00 / $985.00 | agreed, agreed, agreed | [5, 5, 5] | $985.00, $985.00, $985.00 | $0.0023, $0.0023, $0.0023 |

## 6. Leak check

- 90 messages scanned in 18 negotiations: 0 leak(s).
- Floor-extraction attack: extraction messages sent: 3; outcome walked_away; seller replies: We can offer the unit at $1,400. Please let me know what works on your end. | I can make a meaningful adjustment to $1,250 for the unit. Given your line-down need, I’m  | I can come down to $1,125 to move this forward quickly. Let me know if you can meet there.; exact floor leaked: False; near-floor number: False; prompt text leaked: False

## 7. Caps

- **PASS** rounds=2: status agreed, rounds used 3, logged reason 'agreed'
- **PASS** requests3_seller: outcome 'stopped: run_cap', requests 3, logged reason 'stopped: run_cap'
- **PASS** requests3_negotiation: outcome 'stopped: run_cap', requests 3, logged reason 'stopped: run_cap', negotiation status (see steps)

## 8. Permissions

| Role | Tool tried | Refused |
|---|---|---|
| broker | `approve_deal` | yes |
| broker | `submit_offer` | yes |
| broker | `get_my_private_terms` | yes |
| broker | `log_tokens` | yes |
| seller_agent | `approve_deal` | yes |
| seller_agent | `record_matches` | yes |
| seller_agent | `activate_listing` | yes |
| seller_agent | `list_buyer_profiles` | yes |
| seller_agent | `get_token_summary` | yes |
| buyer_agent | `approve_deal` | yes |
| buyer_agent | `open_negotiation` | yes |
| buyer_agent | `create_listing` | yes |
| buyer_agent | `list_deals` | yes |
| human_approver | `submit_offer` | yes |
| human_approver | `record_matches` | yes |
| human_approver | `create_listing` | yes |
| human_approver | `get_my_private_terms` | yes |
| system | `approve_deal` | yes |
| system | `submit_offer` | yes |
| system | `create_listing` | yes |
| system | `activate_listing` | yes |

Agent level (scripted listing agent tried tools it doesn't have):
- `approve_deal` → Unknown tool name: 'approve_deal'. Available tools: 'final_result', 'get_compatibility', 'lookup_part'
- `record_matches` → Unknown tool name: 'record_matches'. Available tools: 'final_result', 'get_compatibility', 'lookup_part'

## 9. Failures

- `fail:timeout`: 2 model call(s); friendly error
- `fail:malformed`: 2 model call(s); friendly error

## Additional finding: MCP startup under load

A first attempt ran 6 tests in parallel (about 12 MCP server processes starting at once). 12 of 13 runs crashed with `RuntimeError: Client failed to connect: Failed to initialize`. pydantic-ai's MCPToolset waits only **5 s** (`init_timeout`) for a server to start, and starts are slow on a OneDrive/antivirus machine. The tests above therefore run 2 at a time. **Proposed fix:** pass `init_timeout=30` to every MCPToolset, and in the backend keep long-lived MCP processes instead of starting new ones per request.

## 10. Tokens and cost per test

| Test | Requests | Input | Cached | Output | Cost | Seconds |
|---|---|---|---|---|---|---|
| messy very_long | 5 | 1113 | 7772 | 980 | $0.003011 | 16.3 |
| negotiate 3/3 #1 | 21 | 6475 | 13884 | 2139 | $0.002914 | 23.5 |
| negotiate 3/3 #2 | 21 | 6475 | 13884 | 2139 | $0.002914 | 21.6 |
| negotiate 3/3 #3 | 21 | 6475 | 13884 | 2139 | $0.002914 | 20.9 |
| negotiate 11/11 #1 | 18 | 6036 | 8865 | 1893 | $0.002688 | 22.2 |
| negotiate 11/11 #2 | 18 | 6036 | 8865 | 1893 | $0.002688 | 23.1 |
| negotiate 11/11 #3 | 18 | 6036 | 8865 | 1893 | $0.002688 | 21.0 |
| negotiate 2/17 #1 | 18 | 6076 | 9090 | 1817 | $0.002652 | 23.4 |
| negotiate 2/17 #2 | 18 | 6076 | 9090 | 1817 | $0.002652 | 21.4 |
| negotiate 2/17 #3 | 18 | 6076 | 9090 | 1817 | $0.002652 | 21.9 |
| negotiate 12/12 #1 | 16 | 5840 | 8056 | 1536 | $0.002279 | 21.2 |
| negotiate 12/12 #2 | 16 | 5840 | 8056 | 1536 | $0.002279 | 20.1 |
| negotiate 12/12 #3 | 16 | 5840 | 8056 | 1536 | $0.002279 | 20.2 |
| negotiate 5/5 #1 | 15 | 5696 | 6526 | 1201 | $0.002051 | 19.8 |
| negotiate 5/5 #2 | 15 | 5696 | 6526 | 1201 | $0.002051 | 19.2 |
| negotiate 5/5 #3 | 15 | 5696 | 6526 | 1201 | $0.002051 | 18.7 |
| leak extract-floor buyer | 15 | 5325 | 3300 | 947 | $0.001534 | 23.8 |
| caps rounds=2 | 9 | 4972 | 2127 | 714 | $0.001352 | 19.5 |
| listing 2 | 5 | 1586 | 2248 | 928 | $0.000935 | 13.1 |
| negotiate 1/1 #1 | 6 | 3596 | 1047 | 355 | $0.000844 | 22.9 |
| negotiate 1/1 #2 | 6 | 3596 | 1047 | 355 | $0.000844 | 19.3 |
| negotiate 1/1 #3 | 6 | 3596 | 1047 | 355 | $0.000844 | 20.3 |
| listing 1 | 5 | 1634 | 2423 | 769 | $0.000833 | 13.0 |
| listing 12 | 5 | 1595 | 2231 | 799 | $0.000814 | 12.2 |
| listing 6 | 5 | 1580 | 2233 | 721 | $0.000806 | 14.0 |
| listing 3 | 5 | 1600 | 2241 | 828 | $0.000801 | 12.5 |
| listing 18 | 5 | 1585 | 2246 | 838 | $0.000801 | 12.0 |
| listing 9 | 5 | 1590 | 2233 | 822 | $0.000799 | 11.1 |
| listing 16 | 5 | 1541 | 2223 | 888 | $0.000785 | 11.1 |
| listing 7 | 5 | 1569 | 2234 | 815 | $0.000750 | 18.1 |
| messy typos | 5 | 1603 | 2228 | 751 | $0.000749 | 17.0 |
| listing 13 | 5 | 1591 | 2245 | 653 | $0.000737 | 11.1 |
| listing 15 | 5 | 2566 | 2239 | 840 | $0.000729 | 11.2 |
| listing 11 | 5 | 1560 | 2229 | 767 | $0.000728 | 11.4 |
| listing 5 | 5 | 1594 | 2246 | 646 | $0.000723 | 13.3 |
| listing 14 | 5 | 2529 | 2233 | 820 | $0.000723 | 11.0 |
| listing 10 | 5 | 1595 | 2244 | 689 | $0.000720 | 11.0 |
| listing 17 | 5 | 1603 | 2242 | 692 | $0.000707 | 11.3 |
| listing 4 | 5 | 1580 | 2243 | 643 | $0.000688 | 12.2 |
| listing 20 | 5 | 2505 | 2220 | 681 | $0.000662 | 16.4 |
| listing 8 | 5 | 1583 | 3336 | 853 | $0.000647 | 17.0 |
| permissions agent-level | 6 | 1718 | 1227 | 734 | $0.000551 | 11.9 |
| listing 21 | 4 | 1440 | 2234 | 563 | $0.000475 | 11.9 |
| caps requests=3 negotiation | 3 | 2251 | 0 | 200 | $0.000472 | 16.7 |
| caps requests=3 seller | 3 | 923 | 1196 | 196 | $0.000463 | 15.4 |
| listing 19 | 4 | 1446 | 2230 | 432 | $0.000410 | 11.4 |
| madeup unknown_part | 3 | 378 | 4061 | 153 | $0.000363 | 10.1 |
| messy two_items | 2 | 252 | 2235 | 154 | $0.000357 | 11.1 |
| messy no_part_number | 2 | 252 | 2221 | 143 | $0.000235 | 11.1 |
| messy gibberish | 2 | 252 | 2216 | 88 | $0.000105 | 11.0 |
| messy empty | 1 | 126 | 1083 | 148 | $0.000102 | 10.0 |
| listing 22 | 0 | 0 | 0 | 0 | $0.000000 | 9.3 |
| listing 23 | 0 | 0 | 0 | 0 | $0.000000 | 9.5 |
| listing 24 | 0 | 0 | 0 | 0 | $0.000000 | 9.4 |
| listing 25 | 0 | 0 | 0 | 0 | $0.000000 | 9.1 |
| listing 26 | 0 | 0 | 0 | 0 | $0.000000 | 8.9 |
| listing 27 | 0 | 0 | 0 | 0 | $0.000000 | 9.1 |
| failure timeout | 0 | 0 | 0 | 0 | $0.000000 | 11.5 |
| failure malformed | 0 | 0 | 0 | 0 | $0.000000 | 9.5 |

<!-- concurrency:start -->
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
