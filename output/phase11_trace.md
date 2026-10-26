# Phase 11 traced run (one real run in the app, 2026-10-26)

Driven through the real UI (Playwright on Chrome) after a demo reset (audit `reset-3ca9e931`). Run ids match `output/audit_trail.json`; facts in `output/phase11_trace.json`. A narrow-overlap pair with normal urgency was chosen so the agents bargain for several rounds (the earlier traced run, a line-down S7-300 CPU deal that closed in 2 rounds, is superseded; its screenshots stay as `phase11-*`).

| Run | Kind | Model calls | Input (uncached) | Cached | Cache write | Output | Cost |
|---|---|---|---|---|---|---|---|
| `75d4ae25c9fd` | seller_flow | 5 | 1,683 | 2,243 | 2,240 | 759 | $0.00085 |
| `63eb88cf9061` | negotiation | 18 | 2,268 | 14,173 | 10,393 | 1,473 | $0.002404 |

1. **Seller post** (Hartwell Precision, Dayton OH): "also 12 of the SM321 32pt DI cards (6ES7 321-1BL00-0AA0) from the same 300 retrofit, pulled working. open to offers" → listing 28, part `6ES7321-1BL00-0AA0`, 12 units, compliance passed.
2. **Matches:** Prairie Packaging 94 (open request #13, 6 units, normal urgency); Riverbend Foods 62, Oakridge Dairy Cooperative 56. Price: ask $265 (new $530, scrap $7.84/unit); suggested floor $185.5, which Hartwell lowered to and confirmed at **$122** (human touchpoint 1).
3. **Buyer:** Prairie Packaging sees the match alert and clicks Start negotiation; its budget $131/unit was set when it posted the request.
4. **Negotiation:** seller offer $240 → buyer offer $100 → seller offer $195 → buyer offer $115 → seller offer $122 → buyer accept $122 (6 rounds). Blocked moves: none (seller 0, buyer 0).
5. **Approvals:** seller 2026-10-26T18:20:39+00:00, buyer 2026-10-26T18:20:49+00:00 (human touchpoint 2). Deal $122 × 6 = $732, $9 under the buyer's budget; est. 37.2 kg CO2e; request 13 filled; listing keeps 6 units.

Injection test (`808f89078e9c`, earlier session the same day): blocked by the code pre-screen, 0 model calls, $0.

| Screenshot | Shows |
|---|---|
| `trace-sell-top.webp` | listing, compliance passed, agent steps, cost of the run |
| `trace-sell-buyers.webp` | ranked buyers with checked reasons, price, suggested floor |
| `trace-buyer-alert.webp` | Prairie Packaging's match alert |
| `trace-neg-seller.webp`, `trace-neg-buyer.webp` (+ `-chart` crops for the slides) | the same negotiation from each side, each with only its own limit and its own agent's private reasons |
| `trace-deal-closed.webp` | deal closed, both companies approved |
| `trace-marketplace.webp` | Marketplace impact with the closed deal |
| `trace-full-*.webp` | uncropped page captures |
| `crop-injection-blocked.webp`, `crop-matching-error.webp` | cropped versions of `phase11-injection-blocked` and `phase4-matching-error` |
