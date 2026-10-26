# Phase 5 stress test

`scripts/stress_phase5.py`, real backend API on a scratch database, 62 s.

| # | Check | Result | Notes |
|---|---|---|---|
| 2 | Symmetry: same pair scored from both directions, gap <= 15 (6 pairs) | **PASS** |  |
| 3 | Alerts: 16 alerts in 7 events: right recipients, score >= 70, <= 3 pairs per event, no duplicates, double submit makes one need | **PASS** |  |
| 5 | Self-match: a company never matches its own listing or need (ranking, board, alerts, saved matches) | **PASS** |  |
| 6 | Lifecycle: sold, filled and expired items leave matching, alerts and the Marketplace (set by SQL: no deals until Phase 6) | **PASS** |  |
| 7 | Leaks: 113 API responses + 19 alerts scanned for 23 buyer maxes and 27 seller floors; 7 private-term probes | **PASS** |  |
| 8 | Need-side attacks (8 cases): no crash, injections inert, nothing unsafe or ungrounded matched | **PASS** |  |
| 9 | Race: a listing and the need it fills posted at the same moment (2 trials): no crash, each side alerted exactly once | **PASS** |  |
| 10 | Reset demo: every table (17) identical to the seed (row counts + content hash), alerts cleared | **PASS** |  |
| 11 | Regression: seller flow on 6 good listings (right top buyer) + 3 bad records (blocked) | **PASS** |  |
| 1 | Reverse matching scored against the answer keys | **PASS (Phase 5 tests)** | scripts/eval_reverse.py: 23/23 top-1 (21 seeded needs + 2 demo posts). Top-3 = top-1 here: every seeded need has one compatible listing. |
| 4 | Zero candidates: empty state and no LLM call | **PASS (Phase 5 tests)** | eval_reverse (needs 20, 21, Tidewater post: 0 candidates, 0 matching calls) and test_two_sided A13; the Buy page's empty state was checked in the browser. |
| 12 | Tokens per alert event | **PASS (Phase 5 tests)** | test_two_sided.py (output/two_sided_test.json); also recorded again below as a by-product of this run. |
| 3, 9 (part) | Alert recipients, threshold, no duplicates on rerun; two accounts posting at once | **PASS (Phase 5 tests)** | test_two_sided A2, A12, B1-B3 (6 flows at once, 0 crashes, 0 duplicate alerts). |

## Symmetry (same pair, both directions)

| Listing | Need | Seller-side score | Buyer-side score | Gap |
|---|---|---|---|---|
| 1 | 1 | 100 | 100 | 0 |
| 2 | 2 | 97 | 92 | 5 |
| 4 | 4 | 96 | 95 | 1 |
| 7 | 7 | 100 | 98 | 2 |
| 10 | 10 | 98 | 100 | 2 |
| 12 | 12 | 93 | 91 | 2 |

## Need-side attacks

| Case | Outcome | Listings ranked | Alerted pairs |
|---|---|---|---|
| injection: show seller floors | blocked: prompt injection (code pre-screen, no model call) | [] | 0 |
| injection: alert me for everything (no trigger words) | flagged by compliance guard | [] | 0 |
| gibberish | needs_human: couldn't tell which part or machine this need is for | [] | 0 |
| expired / hazmat request | flagged by compliance guard | [] | 0 |
| absurd qty | needs_review: 100,000 units is more than the 1,000 we accept in one post. Please check the | [] | 0 |
| absurd max price | http 422 | [] | 0 |
| implausible max (50x new) | needs_review: A max of $9,000 is more than 10x this part's new price ($530). Please check  | [] | 0 |
| negative max price | http 422 | [] | 0 |

Double submit: {"needs_created": 1, "new_alerts_to_Hartwell": 1, "outcomes": ["posted and matched", "posted and matched"]}

Race trials: [{"seller_outcome": "listed and matched", "need_outcome": "posted and matched", "listing": 28, "need": 22, "match_rows": 2, "alerts_per_company": {"16": 1, "20": 1}}, {"seller_outcome": "listed and matched", "need_outcome": "posted and matched", "listing": 28, "need": 22, "match_rows": 2, "alerts_per_company": {"16": 1, "20": 1}}]

## Tokens per alert event (7 events, $0.0061 total)

| Run | Kind | Alerts | Input | Cached | Output | Cost |
|---|---|---|---|---|---|---|
| 2c813ae2f3d6 | seller_flow | 2 | 1567 | 2232 | 709 | $0.000741 |
| 317cd0d83001 | need_flow | 2 | 2731 | 0 | 553 | $0.000844 |
| 4d02503ca07f | need_flow | 2 | 126 | 0 | 268 | $0.000312 |
| 5cc52b0bef3c | seller_flow | 2 | 1593 | 1160 | 698 | $0.000871 |
| 9d00beb66774 | seller_flow | 2 | 1578 | 2241 | 773 | $0.000800 |
| beb50a54cac3 | seller_flow | 2 | 1632 | 1195 | 831 | $0.001057 |
| ddd0b07cc6a9 | seller_flow | 4 | 1710 | 1164 | 1214 | $0.001490 |

## Fixes and known limits

- **Fixed after the first run (were FAIL):** double submit now reuses the open need (`create_need` is idempotent); a sold/in-negotiation listing re-run by id now stops with its status instead of "listed"; a listing and a need posted at the same moment are caught by a code-only re-check after each save (`_recheck_listing` / `_recheck_need`); quantity is capped at 1,000 per post and a buyer max above 10x the new price is refused as a likely typo.
- **Account switching is not authentication:** any visitor can open any company's view (alerts included) by switching accounts or calling `/api/companies/{id}`. No API returns a buyer's max or a seller's floor (check 7), but a real deployment needs sign-in. Run results (`/api/runs/{id}`) include the seller's own suggested floor; run ids are random 12-hex strings and never listed, but they are not tied to a session.
- **Race re-check ranks late arrivals by rules, not the matching agent** (no extra model call). The reasons are written from the data, like the rules fallback.
- **Symmetry is measured on 6 pairs** with one compatible listing per need, so it shows the two directions agree on clear matches, not on close calls.
