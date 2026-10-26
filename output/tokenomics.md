# Tokenomics

Model `gpt-6-luna` via Portkey. Every number below is from real logged runs (`scripts/cost_report.py`).

| Run | Runs measured | Avg cost | Avg tokens | Avg model calls | Cached share of input |
|---|---|---|---|---|---|
| Seller flow: post -> listing agent -> compliance -> matching -> pricing -> outreach | 21 | $0.00073 | 6033 | 4.9 | 44% |
| Buy request (new post): need agent -> guard -> matching -> alerts | 21 | $0.00076 | 5368 | 4.4 | 10% |
| Re-match an existing request (matching agent only) | 21 | $0.00030 | — | 1.0 | — |
| Negotiation (both agents, until deal / walk-away / cap) | 42 | $0.00190 | 17055 | 6.7 | 39% |

**Per user per month** (assumption: 10 listings, 4 buy requests, 6 negotiations): **$0.0217**

| Users | Per month | Per year |
|---|---|---|
| 1 | $0.02 | $0.26 |
| 100 | $2.17 | $26.08 |
| 10,000 | $217.30 | $2,607.60 |

## Cost-cutting experiment: the SQL pre-filter

| | With pre-filter | Every company |
|---|---|---|
| Companies sent to the matching agent | 2.6 | 49.0 |
| Avg tokens per matching call | 1,974 | 8,217 |
| Avg cost per matching call | $0.000390 | $0.001231 |
| Top-1 correct (18 labelled listings) | 18/18 | 18/18 |
| Picks code would reject as ungrounded | 0 | 0 |

Token reduction 76%, cost reduction 68% per matching call. The company list is only 50 here; without a pre-filter the prompt grows with every company that joins, while the pre-filter keeps it at the compatible few.

## Other savings

- **Code before models:** phase3_stress.md test 4b: the 4 obvious bad records were blocked with 0 model requests; a buy request with no compatible listing skips the matching agent (eval_reverse: 3 needs, 0 matching calls).
- **Prompt caching (Portkey / OpenAI):** 44% of seller-flow input tokens were served from cache (billed at $0.01 / 1M instead of $0.10 / 1M).
- **Code suggests the buyer's budget:** no model call for the budget (Phase 6 follow-up); the seller's floor comes with the pricing agent call that already runs.

## Caps that stop overspending

- `MAX_MODEL_REQUESTS` = 30
- `MAX_TOKENS_PER_RUN` = 150000
- `MAX_NEGOTIATION_ROUNDS` = 6
- `NEGOTIATION_MAX_COST_USD` = 0.05
- `SESSION_BUDGET_USD` = 2.0
