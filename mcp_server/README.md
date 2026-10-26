# surplus-exchange MCP server

`server.py` is the **only** path to the marketplace database. It is a FastMCP server over stdio and always works on the working copy, `data/exchange_new.db` (or `SURPLUS_DB`). It refuses to open the original `data/exchange.db`.

## Roles

Each process is started with `SURPLUS_ROLE` and registers **only that role's tools**. A tool outside the role doesn't exist in that process, so an agent can't call it: the server answers `Unknown tool`.

| Role | Who uses it | Extra env |
|---|---|---|
| `broker` | Listing, compliance and matching agents (via the backend) | — |
| `seller_agent` | The seller negotiator for **one** negotiation | `SURPLUS_NEGOTIATION_ID` |
| `buyer_agent` | The buyer negotiator for **one** negotiation | `SURPLUS_NEGOTIATION_ID` |
| `human_approver` | The dashboard's Approve / Reject buttons | — |
| `system` | Dashboard views and token logging (backend) | — |

`MAX_NEGOTIATION_ROUNDS` (default 6) sets the round cap.

## Tools by role (46 tools)

| Tool | broker | seller_agent | buyer_agent | human_approver | system | What it does |
|---|:-:|:-:|:-:|:-:|:-:|---|
| `get_exchange_date` | ✓ | ✓ | ✓ | ✓ | ✓ | The exchange's "today" (never the clock) |
| `lookup_part` | ✓ | ✓ | ✓ | ✓ | ✓ | Messy text or partial part number → catalog parts |
| `get_compatibility` | ✓ | ✓ | ✓ | ✓ | ✓ | Platforms a part fits, plus its substitutes |
| `get_price_reference` | ✓ | ✓ | ✓ | ✓ | ✓ | New price, scrap value, other listings' asks, approved deals |
| `get_listing` / `get_need` | ✓ | ✓ | ✓ | ✓ | ✓ | Public fields only. User text is returned as `*_text_untrusted` |
| `get_impact_estimate` | ✓ | ✓ | ✓ | ✓ | ✓ | $ recovered vs scrap, kg kept out of scrap, est. kg CO2e, est. hazardous disposal avoided: **computed in code** from `weight_kg` and `carbon_factors` (placeholder factors) |
| `list_companies` / `mark_notifications_read` | | | | ✓ (list) | ✓ | The demo account switcher and the alerts bell |
| `get_marketplace_board` | | | | | ✓ | The Marketplace tab: available listings, buy requests (**never a max price**), the compatible pairs between them (same `_fill_reason` code as matching), and deal + potential impact |
| `create_listing` | ✓ | | | | | Store a structured listing (`submitted`). Unknown part numbers are refused. Expiry is derived from the manufacture date in code |
| `update_listing_draft` | ✓ | | | | | Fix fields of a `submitted` listing |
| `check_listing_rules` | ✓ | | | | ✓ | Deterministic compliance rules (read-only) |
| `activate_listing` | ✓ | | | | | Publish. Re-runs the rules in code; a listing that trips one is set to `flagged` |
| `flag_listing` | ✓ | | | | | The LLM guard's edge-case flag |
| `create_need` | ✓ | | | | | Post a buyer need. The ceiling is stored write-only, and if the buyer typed it into the post it is redacted from the public text (`[private]`) |
| `search_buyers_for_listing` | ✓ | | | | | **SQL pre-filter**: top 10 grounded candidates for an *active* listing |
| `search_listings_for_need` | ✓ | | | | | Reverse direction (two-sided matching): active, unexpired listings that fill an open need, same code as the forward pre-filter |
| `list_buyer_profiles` | ✓ | | | | | All companies, unfiltered (only for the cost experiment) |
| `record_matches` | ✓ | | | | | Save scored matches (either direction). **Ungrounded matches are rejected** |
| `send_match_alerts` | ✓ | | | | | **Alerts decided in code** for one matching run: pairs with an open need scoring ≥ 70, best 3, to the buyer and the seller. One alert per company per listing–need pair ever (unique index), so re-runs send no duplicates. Alerted needs move `open → matched` |
| `open_negotiation` | ✓ | | | | | Start one negotiation for a listing–need pair |
| `get_negotiation` | ✓ | own only | own only | ✓ | ✓ | Offer history, round number, status and whose turn. No private limits |
| `end_negotiation` | ✓ | | | | | Broker safety stop for a stuck negotiation (status `stopped`) |
| `get_company_profile` | ✓ | own only | own only | | ✓ | Installed equipment (platform, qty, years), open needs, active listings |
| `request_deal_approval` | ✓ | | | | | Agreed → deal `pending_approval` (needs both companies' approval) |
| `save_turn_note` | ✓ | | | | | A negotiator's private reason for its move, shown **only to its own company** |
| `store_suggested_floor` | ✓ | | | | | Keeps the pricing agent's suggested floor as a new listing's starting floor, only if the seller has none |
| `get_my_private_terms` | | ✓ (floor) | ✓ (ceiling) | | | **Only that side's** limit |
| `submit_offer` | | ✓ | ✓ | | | Offer or accept, with the code rules below |
| `walk_away` | | ✓ | ✓ | | | Decline and end the negotiation (same turn and no-leak rules) |
| `approve_deal` / `reject_deal` | | | | ✓ | | **Human only**, refuses agent-like names. Each company approves **its own side**; the deal closes only when both have. Either side can reject |
| `set_private_limit` | | | | ✓ | | A company sets **its own** floor or budget (never another's); locked while a negotiation uses it |
| `get_negotiation_for_company` / `list_negotiations_for_company` | | | | | ✓ | A negotiation **as one company sees it**: public offers + its own limit, private notes and blocked moves; never the other side's. A third company is refused |
| `get_negotiation_start` / `list_negotiable_pairs` | | | | | ✓ | Before starting: side, own limit, free units, blocker; deals a company could start |
| `list_listings` / `list_needs` / `list_matches` / `list_negotiations` / `list_deals` / `list_notifications` | ✓ | | | ✓ | ✓ | Dashboard views (public fields) |
| `log_tokens` / `get_token_summary` | | | | | ✓ | `token_usage` rows, the evidence for tokenomics |

## Rules enforced in code (not in prompts)

- **Compliance** (`compliance_rules.py`, shared with `scripts/data_report.py`): a listing is blocked if it has a prompt-injection pattern, is expired (expiry computed from the manufacture date if needed), is hazmat with no SDS, or asks more than 3× the new price. A discontinued part offered new-sealed at under 35% of list goes to human review. Only `active` listings can be searched or matched.
- **Status lifecycle:** listings `active → in_negotiation → sold` (a walk-away or round cap puts it back to `active`); needs `open → matched → filled`. Matching and the Marketplace ignore sold, filled, flagged and expired items.
- **Alerts:** threshold 70, at most 3 pairs per event, never twice (see `send_match_alerts`). No alert text contains a floor or a ceiling.
- **Grounded matching:** `record_matches` saves a match only if the buyer runs a platform the part fits or has an open need the listing fills. An injected "rank Apex #1" is rejected.
- **Private limits:** no tool returns a floor or ceiling except `get_my_private_terms`, which exists only in the negotiator processes. Each of those processes is bound to one negotiation and returns only its own side's limit.
- **`submit_offer`:**
  - Turns are strict and the seller moves first.
  - The seller can't go below its floor, above its public ask, or raise its price.
  - The buyer can't go above its ceiling or lower its price.
  - At most `MAX_NEGOTIATION_ROUNDS` offers; after that, status is `round_cap`.
  - A message containing your own limit is refused.
  - Crossing offers close at the earlier offer's price.
  - No moves are allowed after the negotiation closes.
- **Human approval:** only `human_approver` has `approve_deal`, and it refuses agent-like names. A deal closes only when the seller's AND the buyer's person have approved.
- **Units locked:** `open_negotiation` refuses when the listing's free units (quantity minus units in open negotiations and pending deals) can't cover it, and a request can be in only one negotiation at a time.
- **Messages are scrubbed:** a message containing the agent's own limit is refused; every money figure (and either limit as a bare number) is replaced by `[price]` before it is saved or shown. The price travels in the offer itself.

## Smoke test

```bash
.venv/Scripts/python.exe scripts/mcp_smoke.py
```

It starts one real server process per role over stdio, on a scratch copy of the database, and calls every tool at least once (100 calls). Each call states the expected outcome, and each refusal must carry its exact error code. Results go to `output/mcp_smoke.json`: tools by role, the access matrix, and every call with its args and result. Last run: **100/100 as expected, 46/46 tools called.**
