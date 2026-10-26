# Phase 6 stress test: negotiation

`scripts/test_negotiation.py`, real backend API on scratch databases. 34/34 checks pass. Model spend for this run: $0.0425 (337,851 tokens), 213 s.

| Section | Check | Result |
|---|---|---|
| 1. End to end | Seller (Prairie) posts 1 seal kit: listed, Tidewater alerted | **PASS** |
| 1. End to end | The pricing agent's suggested floor is saved to seller_private (with a one-line reason), not yet confirmed | **PASS** |
| 1. End to end | Auto-negotiate waits for the seller to confirm its floor (no negotiation started yet) | **PASS** |
| 1. End to end | Human touchpoint 1: Prairie confirms the floor -> the negotiation with Tidewater starts by itself | **PASS** |
| 1. End to end | Tidewater is told its agent started negotiating (bell) | **PASS** |
| 1. End to end | Agents reach a deal within both limits (code-enforced) | **PASS** |
| 1. End to end | Human touchpoint 2 (buyer): approves its side; the deal still waits for the seller | **PASS** |
| 1. End to end | Seller approves too: deal closed, listing sold, need filled, related alerts closed | **PASS** |
| 1. End to end | Deal card per side: measured against each company's own limit | **PASS** |
| 1. End to end | Sold listing and filled need are gone from the Marketplace | **PASS** |
| 1. End to end | Buyer (Riverbend) posts without a max price: a budget is suggested from the new price and downtime, saved, not confirmed | **PASS** |
| 1. End to end | Riverbend confirms its budget -> the negotiation with Hartwell (input cards) starts by itself | **PASS** |
| 2. Leak scan | Leak scan (section 1): 31 API responses, 8 messages and all alerts; neither side's view holds the other's limit; a third company is refused | **PASS** |
| 3. Oversell / reject | Oversell: listing 2 (2 units) locked by a 2-unit negotiation; a second buyer and a duplicate are refused | **PASS** |
| 3. Oversell / reject | Units locked never exceed the listing's quantity | **PASS** |
| 3. Oversell / reject | Reject (buyer rejects after the seller approved): negotiation closed, nothing sold, listing back to active | **PASS** |
| 3. Oversell / reject | Seller sees why (plain English) and a next-best buyer to try | **PASS** |
| 3. Oversell / reject | After the reject, the freed units can be negotiated with the next-best buyer | **PASS** |
| 2. Leak scan | Leak scan (section 3): 27 API responses, 8 messages and all alerts; neither side's view holds the other's limit; a third company is refused | **PASS** |
| 4. Concurrency | 5 started at once: all accepted; 2 waited in the queue (shown as Queued: True); at most 2 negotiating at the same time | **PASS** |
| 4. Concurrency | All 5 finished with a real outcome (no crash, no stuck or stopped negotiation) | **PASS** |
| 4. Concurrency | Every agreed price is within both private limits | **PASS** |
| 2. Leak scan | Leak scan (section 4): 155 API responses, 15 messages and all alerts; neither side's view holds the other's limit; a third company is refused | **PASS** |
| 2. Leak scan | Leak scan (section 5): 85 API responses, 24 messages and all alerts; neither side's view holds the other's limit; a third company is refused | **PASS** |
| 2. Leak scan | Leak scan (section 5): 73 API responses, 25 messages and all alerts; neither side's view holds the other's limit; a third company is refused | **PASS** |
| 5. Consistency | Hartwell -> Riverbend (clear deal): 3/3 runs as expected; prices [1425.0, 1425.0, 1400.0] | **PASS** |
| 5. Consistency | Summit -> Ironclad (clear deal): 3/3 runs as expected; prices [985.0, 985.0, 985.0] | **PASS** |
| 5. Consistency | Hartwell -> Prairie Packaging (narrow deal): 3/3 runs as expected; prices [123.0, 122.0, 125.0] | **PASS** |
| 5. Consistency | Redwood -> Coastal Electronics (narrow deal): 3/3 runs as expected; prices [255.0, 250.0, 252.0] | **PASS** |
| 5. Consistency | Cascade -> Northwoods (walk-away): 3/3 runs as expected; prices [] | **PASS** |
| 2. Leak scan | Leak scan (section 5): 78 API responses, 24 messages and all alerts; neither side's view holds the other's limit; a third company is refused | **PASS** |
| 6. Safety in code | A message with the agent's OWN limit is blocked (the agent must rewrite it) | **PASS** |
| 6. Safety in code | The other side's limit and every money figure are scrubbed before the message is saved or shown | **PASS** |
| 6. Safety in code | Per-negotiation cost cap ($0.0004 for this test) stops a negotiation safely, with a plain explanation | **PASS** |

## Demo samples, repeated

| Sample | Expected | Outcomes | Prices | Rounds |
|---|---|---|---|---|
| Hartwell -> Riverbend (clear deal) | deal | deal, deal, deal (3/3) | $1,425, $1,425, $1,400 | [2, 2, 2] |
| Summit -> Ironclad (clear deal) | deal | deal, deal, deal (3/3) | $985, $985, $985 | [5, 5, 5] |
| Hartwell -> Prairie Packaging (narrow deal) | deal | deal, deal, deal (3/3) | $123, $122, $125 | [5, 6, 5] |
| Redwood -> Coastal Electronics (narrow deal) | deal | deal, deal, deal (3/3) | $255, $250, $252 | [5, 5, 5] |
| Cascade -> Northwoods (walk-away) | no deal | no deal, no deal, no deal (3/3) | — | [7, 7, 7] |

## Every negotiation in this run

| Label | Status | Rounds | Price | Floor | Budget | Blocked moves | Cost |
|---|---|---|---|---|---|---|---|
| e2e Prairie -> Tidewater (auto) | agreed | 2 | $330.00 | $230 | $415 | — | $0.00079 |
| buyer-side auto Riverbend <- Hartwell | agreed | 6 | $180.00 | $122 | $238 | — | $0.00239 |
| oversell base 2/2 | agreed | 2 | $3,350.00 | $2,610 | $3,780 | — | $0.00067 |
| after reject 2/17 | agreed | 6 | $2,610.00 | $2,610 | $2,690 | — | $0.00219 |
| concurrent 4/4 | agreed | 2 | $435.00 | $305 | $455 | — | $0.00072 |
| concurrent 5/5 | agreed | 7 | $2,340.00 | $2,210 | $2,340 | — | $0.00262 |
| concurrent 7/7 | agreed | 2 | $1,075.00 | $690 | $1,490 | — | $0.00065 |
| concurrent 8/8 | agreed | 2 | $2,600.00 | $1,915 | $2,985 | — | $0.00067 |
| concurrent 10/10 | agreed | 2 | $2,890.00 | $1,985 | $4,150 | — | $0.00067 |
| sample run 1: Hartwell -> Riverbend (clear deal) | agreed | 2 | $1,425.00 | $905 | $1,890 | — | $0.00079 |
| sample run 1: Summit -> Ironclad (clear deal) | agreed | 5 | $985.00 | $790 | $985 | — | $0.00197 |
| sample run 1: Hartwell -> Prairie Packaging (narrow deal) | agreed | 5 | $123.00 | $122 | $131 | — | $0.00196 |
| sample run 1: Redwood -> Coastal Electronics (narrow deal) | agreed | 5 | $255.00 | $248 | $262 | — | $0.00196 |
| sample run 1: Cascade -> Northwoods (walk-away) | round_cap | 7 | — | $655 | $640 | — | $0.00273 |
| sample run 2: Hartwell -> Riverbend (clear deal) | agreed | 2 | $1,425.00 | $905 | $1,890 | — | $0.00074 |
| sample run 2: Summit -> Ironclad (clear deal) | agreed | 5 | $985.00 | $790 | $985 | — | $0.00197 |
| sample run 2: Hartwell -> Prairie Packaging (narrow deal) | agreed | 6 | $122.00 | $122 | $131 | — | $0.00219 |
| sample run 2: Redwood -> Coastal Electronics (narrow deal) | agreed | 5 | $250.00 | $248 | $262 | — | $0.00196 |
| sample run 2: Cascade -> Northwoods (walk-away) | round_cap | 7 | — | $655 | $640 | — | $0.00273 |
| sample run 3: Hartwell -> Riverbend (clear deal) | agreed | 2 | $1,400.00 | $905 | $1,890 | — | $0.00066 |
| sample run 3: Summit -> Ironclad (clear deal) | agreed | 5 | $985.00 | $790 | $985 | — | $0.00197 |
| sample run 3: Hartwell -> Prairie Packaging (narrow deal) | agreed | 5 | $125.00 | $122 | $131 | — | $0.00185 |
| sample run 3: Redwood -> Coastal Electronics (narrow deal) | agreed | 5 | $252.00 | $248 | $262 | — | $0.00186 |
| sample run 3: Cascade -> Northwoods (walk-away) | round_cap | 7 | — | $655 | $640 | — | $0.00283 |
| cost cap 13/13 | stopped | 2 | — | $122 | $131 | — | $0.00069 |
