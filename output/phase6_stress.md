# Phase 6 stress test: negotiation

`scripts/test_negotiation.py`, real backend API on scratch databases. 6/6 checks pass. Model spend for this run: $0.0281 (229,864 tokens), 346 s.

| Section | Check | Result |
|---|---|---|
| 5. Consistency | Hartwell -> Riverbend (clear deal): 3/3 runs as expected; prices [1400.0, 1400.0, 1425.0] | **PASS** |
| 5. Consistency | Summit -> Ironclad (clear deal): 3/3 runs as expected; prices [975.0, 985.0, 985.0] | **PASS** |
| 5. Consistency | Hartwell -> Prairie Packaging (narrow deal): 3/3 runs as expected; prices [123.0, 125.0, 123.0] | **PASS** |
| 5. Consistency | Redwood -> Coastal Electronics (narrow deal): 3/3 runs as expected; prices [252.0, 250.0, 262.0] | **PASS** |
| 5. Consistency | Cascade -> Northwoods (walk-away): 3/3 runs as expected; prices [] | **PASS** |
| 2. Leak scan | Leak scan (section 5): 819 API responses, 26 messages and all alerts; neither side's view holds the other's limit; a third company is refused | **PASS** |

## Demo samples, repeated

| Sample | Expected | Outcomes | Prices | Rounds |
|---|---|---|---|---|
| Hartwell -> Riverbend (clear deal) | deal | deal, deal, deal (3/3) | $1,400, $1,400, $1,425 | [2, 2, 2] |
| Summit -> Ironclad (clear deal) | deal | deal, deal, deal (3/3) | $975, $985, $985 | [5, 5, 5] |
| Hartwell -> Prairie Packaging (narrow deal) | deal | deal, deal, deal (3/3) | $123, $125, $123 | [5, 5, 5] |
| Redwood -> Coastal Electronics (narrow deal) | deal | deal, deal, deal (3/3) | $252, $250, $262 | [5, 5, 7] |
| Cascade -> Northwoods (walk-away) | no deal | no deal, no deal, no deal (3/3) | — | [7, 7, 7] |

## Every negotiation in this run

| Label | Status | Rounds | Price | Floor | Budget | Blocked moves | Cost |
|---|---|---|---|---|---|---|---|
| sample run 1: Hartwell -> Riverbend (clear deal) | agreed | 2 | $1,400.00 | $905 | $1,890 | — | $0.00066 |
| sample run 1: Summit -> Ironclad (clear deal) | agreed | 5 | $975.00 | $790 | $985 | — | $0.00194 |
| sample run 1: Hartwell -> Prairie Packaging (narrow deal) | agreed | 5 | $123.00 | $122 | $131 | — | $0.00196 |
| sample run 1: Redwood -> Coastal Electronics (narrow deal) | agreed | 5 | $252.00 | $248 | $262 | — | $0.00186 |
| sample run 1: Cascade -> Northwoods (walk-away) | round_cap | 7 | — | $655 | $640 | — | $0.00272 |
| sample run 2: Hartwell -> Riverbend (clear deal) | agreed | 2 | $1,400.00 | $905 | $1,890 | — | $0.00066 |
| sample run 2: Summit -> Ironclad (clear deal) | agreed | 5 | $985.00 | $790 | $985 | — | $0.00185 |
| sample run 2: Hartwell -> Prairie Packaging (narrow deal) | agreed | 5 | $125.00 | $122 | $131 | — | $0.00183 |
| sample run 2: Redwood -> Coastal Electronics (narrow deal) | agreed | 5 | $250.00 | $248 | $262 | — | $0.00196 |
| sample run 2: Cascade -> Northwoods (walk-away) | round_cap | 7 | — | $655 | $640 | — | $0.00283 |
| sample run 3: Hartwell -> Riverbend (clear deal) | agreed | 2 | $1,425.00 | $905 | $1,890 | — | $0.00079 |
| sample run 3: Summit -> Ironclad (clear deal) | agreed | 5 | $985.00 | $790 | $985 | — | $0.00185 |
| sample run 3: Hartwell -> Prairie Packaging (narrow deal) | agreed | 5 | $123.00 | $122 | $131 | — | $0.00196 |
| sample run 3: Redwood -> Coastal Electronics (narrow deal) | agreed | 7 | $262.00 | $248 | $262 | — | $0.00250 |
| sample run 3: Cascade -> Northwoods (walk-away) | round_cap | 7 | — | $655 | $640 | — | $0.00274 |
