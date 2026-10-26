# Cost check by hand

Prices typed into `scripts/verify_costs.py` (not read from the app): input $0.10, cached input $0.01, cache write $0.125, output $0.50 per 1M tokens. `input` below is the uncached part.

## seller run (Hartwell posts the Siemens CPUs)

| Agent | Calls | Input | Cached | Cache write | Output | Logged cost | By hand |
|---|---|---|---|---|---|---|---|
| listing_agent | 2 | 252 | 1,195 | 2,144 | 95 | $0.00035265 | 252 × $0.10 + 1,195 × $0.01 + 2,144 × $0.125 + 95 × $0.50 (per 1M) = $0.00035265 |
| compliance_guard | 1 | 674 | 0 | 0 | 111 | $0.00012290 | 674 × $0.10 + 0 × $0.01 + 0 × $0.125 + 111 × $0.50 (per 1M) = $0.00012290 |
| matching_agent | 1 | 126 | 0 | 1,593 | 451 | $0.00043723 | 126 × $0.10 + 0 × $0.01 + 1,593 × $0.125 + 451 × $0.50 (per 1M) = $0.00043723 |
| matching_agent | 1 | 126 | 0 | 1,639 | 458 | $0.00044647 | 126 × $0.10 + 0 × $0.01 + 1,639 × $0.125 + 458 × $0.50 (per 1M) = $0.00044647 |
| pricing_agent | 1 | 707 | 0 | 0 | 315 | $0.00022820 | 707 × $0.10 + 0 × $0.01 + 0 × $0.125 + 315 × $0.50 (per 1M) = $0.00022820 |

**By hand $0.00158745 · logged $0.00158745 · shown in the app $0.001587 → match**

## negotiation #1 (Hartwell vs Riverbend, agreed in 2 rounds)

| Agent | Calls | Input | Cached | Cache write | Output | Logged cost | By hand |
|---|---|---|---|---|---|---|---|
| seller_negotiator | 3 | 378 | 1,193 | 2,518 | 213 | $0.00047098 | 378 × $0.10 + 1,193 × $0.01 + 2,518 × $0.125 + 213 × $0.50 (per 1M) = $0.00047098 |
| buyer_negotiator | 3 | 378 | 2,458 | 1,421 | 161 | $0.00032051 | 378 × $0.10 + 2,458 × $0.01 + 1,421 × $0.125 + 161 × $0.50 (per 1M) = $0.00032051 |

**By hand $0.00079148 · logged $0.00079149 · shown in the app $0.000791 → match**

## Every run behind tokenomics.json

| Group | Runs | Logged ≠ hand | Mean cost | tokenomics.json avg | Same |
|---|---|---|---|---|---|
| seller_flow | 21 | 0 | $0.000991 | $0.000991 | yes |
| buy_request | 21 | 0 | $0.000763 | $0.000763 | yes |
| negotiation (Phase 3 part, full token split) | 18 | 0 | $0.002202 | — | — |

**All checks match: True**
