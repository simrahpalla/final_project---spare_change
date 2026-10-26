# Phase 6 follow-up: limits captured up front + auto-negotiate (end-to-end + leak scan)

`scripts/test_negotiation.py`, real backend API on scratch databases. 13/13 checks pass. Model spend for this run: $0.0057 (34,816 tokens), 104 s.

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
| 2. Leak scan | Leak scan (section 1): 75 API responses, 8 messages and all alerts; neither side's view holds the other's limit; a third company is refused | **PASS** |

## Every negotiation in this run

| Label | Status | Rounds | Price | Floor | Budget | Blocked moves | Cost |
|---|---|---|---|---|---|---|---|
| e2e Prairie -> Tidewater (auto) | agreed | 2 | $330.00 | $230 | $415 | — | $0.00079 |
| buyer-side auto Riverbend <- Hartwell | agreed | 6 | $180.00 | $122 | $238 | — | $0.00239 |
