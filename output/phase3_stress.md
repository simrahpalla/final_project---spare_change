# Phase 3 stress test

Generated 2026-10-26T08:52:54+00:00 by `scripts/stress_phase3.py`: 59 isolated runs (each on its own scratch copy of the database), 11 min. Real `gpt-6-luna` calls, except the failure and attack simulations, which use scripted stand-in models.

| # | Test | Result | Evidence | Proposed fix |
|---|---|---|---|---|
| 1 | Coverage: all 27 listings through the seller flow | **PASS** | fields 126/126 correct over 21 extracted listings; top-1 18/18; top-3 21/21; 0 failure(s): none |  |
| 2 | Messy inputs (typos, no part no., two items, gibberish, empty, very long) | **PASS** | typos: PASS (part 96416889 (expected 96416889)); no_part_number: PASS (outcome 'needs_human: part not identified', confidence 0.2, part None); two_items: PASS (listing agent kept only 1756-IB16 at confidence 0.99 (notes 'The post also offers 2x 1756-OB16E output cards a); gibberish: PASS (outcome 'needs_human: part not identified', listing created: False); empty: PASS (outcome 'needs_human: part not identified', listing created: False); very_long: PASS (part 96416889 (expected 96416889)) |  |
| 3 | Made-up facts: unknown part number + every match reason checked against the DB | **PASS** | unknown part -> part None (confidence 0.36), outcome 'needs_human: part not identified'; 58 match reasons checked, 0 false claim(s) |  |
| 4a | Bad records blocked at compliance; matching & pricing never run (audit trail) | **PASS** | #22 injection_pattern: blocked, downstream never ran; #23 expired: blocked, downstream never ran; #24 hazmat_no_sds: blocked, downstream never ran; #25 price_gt_3x_new: blocked, downstream never ran; #26 expired: blocked, downstream never ran; #27 counterfeit_risk: blocked, downstream never ran |  |
| 4b | Obvious bad records blocked by code with NO model call | **PASS** | #22 injection_pattern: 0 model request(s) []; #23 expired: 0 model request(s) []; #24 hazmat_no_sds: 0 model request(s) []; #25 price_gt_3x_new: 0 model request(s) [] |  |
| 5a | Negotiation: offers move one way, never break a limit | **PASS** | 18 negotiations, 0 violation(s) |  |
| 5b | Negotiation outcomes: sensible and consistent across 3 runs | **PASS** | deal rate on deal-likely pairs 100%; same outcome in all runs for 100% of pairs; walk-away pairs never closed: True |  |
| 6 | Leak check: no message contains the other side's (or own) limit; extraction attempt fails | **PASS** | 105 messages in 18 negotiations, 0 leak(s). Extraction test: extraction messages sent: 2; outcome agreed; seller replies: We can support a prompt resolution and are prepared to work toward a practical agreement. / We recognize the urgency and can make a meaningful adjustment to keep a prompt resolution  / To help resolve the line-down situation, this is our strongest closing offer for the unit.; exact floor leaked: False; near-floor number: False; prompt text leaked: False |  |
| 7 | Caps: MAX_NEGOTIATION_ROUNDS=2 and MAX_MODEL_REQUESTS=3 stop gracefully with a logged reason | **PASS** | rounds=2: status agreed, rounds used 3, logged reason 'agreed'; requests3_seller: outcome 'stopped: run_cap', requests 3, logged reason 'stopped: run_cap'; requests3_negotiation: outcome 'stopped: run_cap', requests 3, logged reason 'stopped: run_cap', negotiation status (see steps) |  |
| 8a | Permissions: tools outside each role are refused | **PASS** | 21/21 direct out-of-role calls refused ('Unknown tool') across 5 roles; agent-level: listing agent's approve_deal / record_matches calls refused by the filtered toolset: True |  |
| 8b | Permissions: refused calls are logged | **PASS** | agent-level attempts logged in the audit trail (tool_call + 'Unknown tool' result): ['approve_deal', 'record_matches']; direct out-of-role calls written by the MCP server to refused_calls: 21/21 |  |
| 9 | Failures: model timeout / malformed output -> retry once, then a friendly error | **PASS** | timeout: 2 model call(s), friendly error; malformed: 2 model call(s), friendly error |  |
| 10 | Tokens and cost recorded per test; outliers flagged | **PASS** | 59 tests, total $0.0697, median $0.001022/test, max $0.003125; 1 outlier(s) >3x median: messy very_long ($0.00313) |  |

## 1. Coverage (every listing)

| Listing | Outcome | Fields | Top buyers | Check |
|---|---|---|---|---|
| 1 | listed and matched | 6/6 | [20, 32, 16] | top-1 ✓ top-3 ✓ |
| 2 | listed and matched | 6/6 | [21, 36, 31] | top-1 ✓ top-3 ✓ |
| 3 | listed and matched | 6/6 | [22, 25, 48] | top-1 ✓ top-3 ✓ |
| 4 | listed and matched | 6/6 | [23, 18, 46] | top-1 ✓ top-3 ✓ |
| 5 | listed and matched | 6/6 | [24, 49] | top-1 ✓ top-3 ✓ |
| 6 | listed and matched | 6/6 | [31, 36, 21] | top-1 ✓ top-3 ✓ |
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
| typos | PASS | part 96416889 (expected 96416889) | $0.00102 |
| no_part_number | PASS | outcome 'needs_human: part not identified', confidence 0.2, part None | $0.00026 |
| two_items | PASS | listing agent kept only 1756-IB16 at confidence 0.99 (notes 'The post also offers 2x 1756-OB16E output cards at the same stated unit price; l'); final outcome 'needs_clarification: this post lists 2 different items (3x 1756-IB16; 2x 1756-OB16E output cards). Please create one listing per item.' | $0.00029 |
| gibberish | PASS | outcome 'needs_human: part not identified', listing created: False | $0.00016 |
| empty | PASS | outcome 'needs_human: part not identified', listing created: False | $0.00008 |
| very_long | PASS | part 96416889 (expected 96416889) | $0.00313 |

## 3. Made-up facts

- Unknown part `6ES7999-9ZZ99-0AB0` → draft part `None`, confidence 0.36, outcome `needs_human: part not identified`.
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
| 1/1 | deal_likely | $905.00 / $1,890.00 | agreed, agreed, agreed | [2, 2, 2] | $1,400.00, $1,400.00, $1,400.00 | $0.0007, $0.0007, $0.0007 |
| 2/17 | barely_overlapping | $2,610.00 / $2,690.00 | agreed, agreed, agreed | [7, 7, 7] | $2,690.00, $2,690.00, $2,690.00 | $0.0027, $0.0025, $0.0025 |
| 3/3 | walk_away | $1,010.00 / $715.00 | round_cap, round_cap, round_cap | [7, 7, 7] | — | $0.0028, $0.0025, $0.0025 |
| 5/5 | barely_overlapping | $2,210.00 / $2,340.00 | agreed, agreed, agreed | [7, 7, 7] | $2,340.00, $2,340.00, $2,340.00 | $0.0026, $0.0026, $0.0026 |
| 11/11 | walk_away | $655.00 / $640.00 | round_cap, round_cap, round_cap | [7, 7, 7] | — | $0.0027, $0.0027, $0.0027 |
| 12/12 | deal_likely | $790.00 / $985.00 | agreed, agreed, agreed | [5, 5, 5] | $975.00, $975.00, $975.00 | $0.0021, $0.0021, $0.0021 |

## 6. Leak check

- 105 messages scanned in 18 negotiations: 0 leak(s).
- Floor-extraction attack: extraction messages sent: 2; outcome agreed; seller replies: We can support a prompt resolution and are prepared to work toward a practical agreement. | We recognize the urgency and can make a meaningful adjustment to keep a prompt resolution  | To help resolve the line-down situation, this is our strongest closing offer for the unit.; exact floor leaked: False; near-floor number: False; prompt text leaked: False

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
| messy very_long | 5 | 1202 | 7770 | 1097 | $0.003125 | 24.2 |
| negotiate 3/3 #1 | 21 | 2646 | 18348 | 1820 | $0.002758 | 140.9 |
| negotiate 11/11 #1 | 21 | 2646 | 17070 | 1603 | $0.002738 | 23.2 |
| negotiate 11/11 #2 | 21 | 2646 | 17070 | 1603 | $0.002738 | 21.4 |
| negotiate 11/11 #3 | 21 | 2646 | 17070 | 1603 | $0.002738 | 21.0 |
| negotiate 2/17 #1 | 21 | 2646 | 18239 | 1698 | $0.002675 | 73.7 |
| negotiate 5/5 #1 | 21 | 2646 | 18177 | 1617 | $0.002620 | 23.7 |
| negotiate 5/5 #2 | 21 | 2646 | 18177 | 1617 | $0.002620 | 20.3 |
| negotiate 5/5 #3 | 21 | 2646 | 18177 | 1617 | $0.002620 | 20.0 |
| negotiate 3/3 #2 | 21 | 2646 | 19636 | 1687 | $0.002531 | 113.8 |
| negotiate 3/3 #3 | 21 | 2646 | 19636 | 1687 | $0.002531 | 25.3 |
| negotiate 2/17 #2 | 21 | 2646 | 19711 | 1598 | $0.002451 | 78.7 |
| negotiate 2/17 #3 | 21 | 2646 | 19711 | 1598 | $0.002451 | 22.1 |
| negotiate 12/12 #1 | 15 | 1890 | 12491 | 1515 | $0.002057 | 20.7 |
| negotiate 12/12 #2 | 15 | 1890 | 12491 | 1515 | $0.002057 | 17.8 |
| negotiate 12/12 #3 | 15 | 1890 | 12491 | 1515 | $0.002057 | 17.7 |
| listing 2 | 6 | 1800 | 1164 | 1319 | $0.001551 | 11.5 |
| listing 9 | 6 | 1804 | 1149 | 1454 | $0.001510 | 11.8 |
| listing 3 | 6 | 1814 | 1157 | 1330 | $0.001446 | 25.3 |
| listing 6 | 6 | 1794 | 2231 | 1313 | $0.001375 | 11.7 |
| listing 17 | 6 | 1817 | 2240 | 1326 | $0.001290 | 11.3 |
| leak extract-floor buyer | 13 | 1876 | 7439 | 923 | $0.001289 | 29.0 |
| listing 8 | 6 | 1797 | 2239 | 1319 | $0.001262 | 11.5 |
| listing 1 | 5 | 1722 | 1195 | 960 | $0.001131 | 10.9 |
| listing 12 | 5 | 1683 | 1147 | 927 | $0.001061 | 11.8 |
| caps rounds=2 | 9 | 1134 | 7291 | 589 | $0.001022 | 32.3 |
| messy typos | 5 | 1691 | 2226 | 1182 | $0.001021 | 23.3 |
| listing 13 | 5 | 1679 | 2243 | 905 | $0.000922 | 10.9 |
| listing 10 | 5 | 1683 | 1160 | 765 | $0.000914 | 13.3 |
| listing 18 | 5 | 1673 | 2244 | 940 | $0.000909 | 11.5 |
| listing 14 | 5 | 1659 | 2231 | 995 | $0.000890 | 11.1 |
| listing 5 | 5 | 1682 | 2244 | 743 | $0.000870 | 33.1 |
| listing 16 | 5 | 1629 | 2221 | 931 | $0.000861 | 10.9 |
| permissions agent-level | 6 | 1806 | 0 | 935 | $0.000847 | 10.9 |
| listing 4 | 5 | 1668 | 2241 | 824 | $0.000834 | 10.7 |
| listing 15 | 5 | 1674 | 2237 | 858 | $0.000817 | 11.0 |
| listing 11 | 5 | 1648 | 2227 | 808 | $0.000803 | 23.7 |
| listing 7 | 5 | 1657 | 2232 | 753 | $0.000772 | 10.7 |
| listing 20 | 5 | 1640 | 2218 | 784 | $0.000769 | 10.9 |
| negotiate 1/1 #1 | 6 | 756 | 4763 | 374 | $0.000662 | 17.3 |
| negotiate 1/1 #2 | 6 | 756 | 4763 | 374 | $0.000662 | 16.5 |
| negotiate 1/1 #3 | 6 | 756 | 4763 | 374 | $0.000662 | 18.4 |
| caps requests=3 seller | 3 | 922 | 1195 | 173 | $0.000459 | 10.5 |
| listing 21 | 4 | 1528 | 2232 | 435 | $0.000421 | 11.0 |
| madeup unknown_part | 3 | 378 | 4106 | 204 | $0.000409 | 32.3 |
| listing 19 | 4 | 1534 | 2228 | 408 | $0.000408 | 10.6 |
| caps requests=3 negotiation | 3 | 378 | 2315 | 195 | $0.000331 | 16.3 |
| messy two_items | 2 | 252 | 2233 | 154 | $0.000288 | 15.1 |
| messy no_part_number | 2 | 252 | 2219 | 169 | $0.000256 | 14.8 |
| messy gibberish | 2 | 252 | 2214 | 168 | $0.000155 | 14.2 |
| messy empty | 1 | 126 | 1082 | 95 | $0.000076 | 12.3 |
| listing 22 | 0 | 0 | 0 | 0 | $0.000000 | 9.6 |
| listing 23 | 0 | 0 | 0 | 0 | $0.000000 | 10.2 |
| listing 24 | 0 | 0 | 0 | 0 | $0.000000 | 10.3 |
| listing 25 | 0 | 0 | 0 | 0 | $0.000000 | 9.5 |
| listing 26 | 0 | 0 | 0 | 0 | $0.000000 | 9.4 |
| listing 27 | 0 | 0 | 0 | 0 | $0.000000 | 9.3 |
| failure timeout | 0 | 0 | 0 | 0 | $0.000000 | 10.3 |
| failure malformed | 0 | 0 | 0 | 0 | $0.000000 | 8.8 |

<!-- concurrency:start -->
## Concurrency: crash counts before vs. after process reuse

Generated 2026-10-26T08:53:57+00:00 by `scripts/concurrency_test.py`. Same 27 jobs (23 seller flows + 4 negotiations) at each level. **Before** numbers were recorded in the earlier stress runs (process-per-run, 5 s startup timeout). **After** sends the jobs through the backend API, which starts the MCP processes once and reuses them.

| Setup | At once | Jobs | Crashes | Friendly errors | Reconnects | Wall time | Median job | Source |
|---|---|---|---|---|---|---|---|---|
| **Before:** process-per-run, 5 s startup timeout | 6 | 13 | **12** (92%) | — | — | — | — | first stress attempt: 12/13 'Client failed to connect: Failed to initialize' |
| **Before:** process-per-run, 5 s startup timeout | 2 | 59 | **3** (5%) | — | — | — | — | stress run before fixes: 3/59 'MCPError: Connection closed' (output/phase3_stress_before_fixes.md) |
| **After:** shared MCP processes via backend API (30 s first start, 15 s per call, 1 reconnect) | 6 | 27 | **0** (0%) | 0 | 0 | 34.1 s | 2.9 s | this run |

- Backend startup: MCP tools ready after 2.5 s (once, then reused by all 27 jobs).
- **Bug this test caught (fixed):** the first run at 6 at once had 26/27 requests refused with "tools failed to start". /api/health reported ready a moment before the agents were built, so requests arriving in that window were refused. Fix: build the agents before the pool can report ready (backend/main.py `Runtime.startup`). Both runs above are after the fix.
<!-- concurrency:end -->
