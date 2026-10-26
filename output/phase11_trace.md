# Phase 11 traced run (one real run, 2026-10-26)

Captured in one sitting after a demo reset (audit `reset-a4b0ae05`, 17:00:02 UTC). Run ids match `output/audit_trail.json`.

| Run | Kind | Requests | Input | Cached | Output | Cost |
|---|---|---|---|---|---|---|
| `bb3d14b89de2` | seller_flow | 5 | 1759 | 1195 | 902 | $0.001106 |
| `fe8ce4b551be` | negotiation | 6 | 756 | 3651 | 374 | $0.000791 |
| `808f89078e9c` | seller_flow | 0 | 0 | 0 | 0 | $0.0 |

The Sell screenshot shows **7,593 tokens, 18% cached** for run `bb3d14b89de2`: the UI counts input + cached + cache-write + output = 1,759 + 1,195 + 3,737 + 902, and cached % = 1,195 / (1,759 + 1,195 + 3,737). Same run, same $0.00111 (`token_usage`).

Deal 1 (negotiation 1, listing 28 → need 1): $1,425 × 1; seller approved 2026-10-26T17:03:50+00:00, buyer approved 2026-10-26T17:03:56+00:00. Approvals are recorded in the `deals` table (approved_by / *_approved_at). Need 1 status: filled; listing 28 keeps 2 of 3 units.

No blocked offer occurred in this run (the buyer accepted in round 2); blocked-move evidence comes from `output/phase6_stress.md` and `safety_tests.json`.

| Screenshot | Shows | Run |
|---|---|---|
| `phase11-sell-top.webp` | Hartwell pastes the S7-300 text; listing, compliance passed, agent activity, cost this run, session impact | `bb3d14b89de2` |
| `phase11-sell-buyers.webp` | Top buyers with fact-checked reasons (Riverbend 98), price card, impact strip, private floor confirm | `bb3d14b89de2` |
| `phase11-buyer-alert.png` | Riverbend's alerts: new match (score 98) and auto-negotiation started | `bb3d14b89de2 / fe8ce4b551be` |
| `phase11-negotiation-buyer.png` | Buyer view: own budget $1,890 only; seller offers $1,425, buyer agent accepts; private turn note | `fe8ce4b551be` |
| `phase11-negotiation-seller.png` | Seller view of the same negotiation: own floor $998 only | `fe8ce4b551be` |
| `phase11-deal-approved.png` | Deal closed, both companies approved; one-time $ and est. 7 kg CO2e; need marked filled | `deal 1` |
| `phase11-marketplace-after.webp` | Marketplace impact: Closed deals 1, $1,425 one-time, est. 7 kg CO2e | `-` |
| `phase11-injection-blocked.webp` | Injection test blocked by the code pre-screen before any model call: $0.00, 0 tokens | `808f89078e9c` |
