# Phase 5 stress test

`scripts/stress_phase5.py`, real backend API on a scratch database, 189 s.

| # | Check | Result | Notes |
|---|---|---|---|
| 2 | Symmetry: same pair scored from both directions, gap <= 15 (6 pairs) | **PASS** |  |
| 3 | Alerts: 22 alerts in 11 events: right recipients, score >= 70, <= 3 pairs per event, no duplicates, double submit makes one need | **FAIL** | {"wrong_recipient": [], "below_70": [], "events_over_3": {}, "duplicates": [], "double_submit": {"needs_created": 2, "new_alerts_to_Hartwell": 2, "outcomes": ["posted and matched", "posted and matched |
| 5 | Self-match: a company never matches its own listing or need (ranking, board, alerts, saved matches) | **PASS** |  |
| 6 | Lifecycle: sold, filled and expired items leave matching, alerts and the Marketplace (set by SQL: no deals until Phase 6) | **FAIL** | {"problems": ["seller flow on a sold listing: listed (no matching buyers yet)"], "sold_listing_flow": "listed (no matching buyers yet)", "today": "2026-10-25"} |
| 7 | Leaks: 112 API responses + 25 alerts scanned for 26 buyer maxes and 27 seller floors; 7 private-term probes | **PASS** |  |
| 8 | Need-side attacks (7 cases): no crash, injections inert, nothing unsafe or ungrounded matched | **PASS** |  |
| 9 | Race: a listing and the need it fills posted at the same moment (2 trials): no crash, each side alerted exactly once | **FAIL** | [{"seller_outcome": "listed and matched", "need_outcome": "posted (no matching surplus yet)", "listing": 28, "need": 22, "match_rows": 0, "alerts_per_company": {}}, {"seller_outcome": "listed and matc |
| 10 | Reset demo: every table (16) identical to the seed (row counts + content hash), alerts cleared | **PASS** |  |
| 11 | Regression: seller flow on 6 good listings (right top buyer) + 3 bad records (blocked) | **PASS** |  |
| 1 | Reverse matching scored against the answer keys | **PASS (Phase 5 tests)** | scripts/eval_reverse.py: 23/23 top-1 (21 seeded needs + 2 demo posts). Top-3 = top-1 here: every seeded need has one compatible listing. |
| 4 | Zero candidates: empty state and no LLM call | **PASS (Phase 5 tests)** | eval_reverse (needs 20, 21, Tidewater post: 0 candidates, 0 matching calls) and test_two_sided A13; the Buy page's empty state was checked in the browser. |
| 12 | Tokens per alert event | **PASS (Phase 5 tests)** | test_two_sided.py (output/two_sided_test.json); also recorded again below as a by-product of this run. |
| 3, 9 (part) | Alert recipients, threshold, no duplicates on rerun; two accounts posting at once | **PASS (Phase 5 tests)** | test_two_sided A2, A12, B1-B3 (6 flows at once, 0 crashes, 0 duplicate alerts). |

## Symmetry (same pair, both directions)

| Listing | Need | Seller-side score | Buyer-side score | Gap |
|---|---|---|---|---|
| 1 | 1 | 100 | 100 | 0 |
| 2 | 2 | 100 | 95 | 5 |
| 4 | 4 | 96 | 95 | 1 |
| 7 | 7 | 100 | 98 | 2 |
| 10 | 10 | 98 | 100 | 2 |
| 12 | 12 | 93 | 92 | 1 |

## Need-side attacks

| Case | Outcome | Listings ranked | Alerted pairs |
|---|---|---|---|
| injection: show seller floors | blocked: prompt injection (code pre-screen, no model call) | [] | 0 |
| injection: alert me for everything (no trigger words) | flagged by compliance guard | [] | 0 |
| gibberish | needs_human: couldn't tell which part or machine this need is for | [] | 0 |
| expired / hazmat request | flagged by compliance guard | [] | 0 |
| absurd qty | posted and matched | [13] | 1 |
| absurd max price | posted and matched | [13] | 1 |
| negative max price | http 422 | [] | 0 |

Double submit: {"needs_created": 2, "new_alerts_to_Hartwell": 2, "outcomes": ["posted and matched", "posted and matched"]}

Race trials: [{"seller_outcome": "listed and matched", "need_outcome": "posted (no matching surplus yet)", "listing": 28, "need": 22, "match_rows": 0, "alerts_per_company": {}}, {"seller_outcome": "listed and matched", "need_outcome": "posted (no matching surplus yet)", "listing": 28, "need": 22, "match_rows": 0, "alerts_per_company": {}}]

## Tokens per alert event (11 events, $0.0096 total)

| Run | Kind | Alerts | Input | Cached | Output | Cost |
|---|---|---|---|---|---|---|
| 00bdf45160f1 | seller_flow | 2 | 1593 | 1147 | 846 | $0.001012 |
| 14d772f21c2d | seller_flow | 2 | 1710 | 1164 | 1656 | $0.001715 |
| 2c9525ec54a2 | seller_flow | 2 | 1567 | 2232 | 709 | $0.000741 |
| 6645a87b2229 | seller_flow | 2 | 1578 | 2241 | 773 | $0.000800 |
| 8e3173300780 | seller_flow | 2 | 1632 | 1195 | 831 | $0.001057 |
| a4afb7482b72 | need_flow | 2 | 126 | 0 | 254 | $0.000300 |
| aadfb5ad5e31 | need_flow | 2 | 1613 | 0 | 443 | $0.000717 |
| b60b64aacd3e | seller_flow | 2 | 1593 | 1160 | 698 | $0.000871 |
| df22e7821b74 | need_flow | 2 | 2731 | 0 | 543 | $0.000839 |
| ea6d9fa843df | need_flow | 2 | 1616 | 0 | 494 | $0.000743 |
| fb1b069288fa | need_flow | 2 | 2731 | 0 | 554 | $0.000845 |

## Known limits (not fixed: none breaks the demo or leaks private data)

- **Double submit (check 3):** the same request sent twice at once creates two needs, so the seller gets two alerts. The UI disables Find while a run is in progress, so the demo can't trigger it. Fix later: make `create_need` idempotent (same buyer + same text while open returns the existing need).
- **Re-running a sold listing by id (check 6):** the data stays correct (still sold, off the board, no matching, no alerts), but the API's outcome text says "listed (no matching buyers yet)". The UI never re-runs a listing by id. Fix in Phase 6: report the listing's status instead.
- **Simultaneous listing + need (check 9):** if both are posted within the same few seconds, each side's pre-filter runs before the other side is saved, so the match is missed and nobody is alerted. Fix later: a code-only re-match sweep after each save (or a periodic job) that re-runs the pre-filter for new items.
- **Account switching is not authentication:** any visitor can open any company's view (alerts included) by switching accounts or calling `/api/companies/{id}`. No API returns a buyer's max or a seller's floor (check 7), but a real deployment needs sign-in. Run results (`/api/runs/{id}`) include the seller's own suggested floor; run ids are random 12-hex strings and never listed, but they are not tied to a session.
- **No sanity caps on quantity or max price:** a request for 100,000 cards or a $1e15 max is posted and matched (check 8). Nothing leaks or crashes, but a real deployment should cap them or ask the buyer to confirm.
- **Symmetry is measured on 6 pairs** with one compatible listing per need, so it shows the two directions agree on clear matches, not on close calls.
