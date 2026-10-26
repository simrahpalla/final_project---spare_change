# Spare Change: design direction

> **Turn spare parts into spare change.**
> A marketplace for industrial surplus, run by AI agents. A plant pastes a messy description of a part it no longer needs. Agents clean up the listing, check it, find buyers whose machines it fits, price it, and negotiate. A human approves every deal.

**Status: APPROVED** (decisions in §7). **Built in Phase 4:** the nav with the account switcher and alerts, the Sell screen with every state, the right rail, and the impact layer. Buy, Marketplace and Negotiations show friendly placeholders until Phases 5 and 6. This direction **replaces** the blue-and-yellow style in `AGENTS.md` for this project. The first-screen mockup is `output/design/mockup_sell.html` (screenshot: `output/screenshots/phase4-mockup-sell.png`).

---

## 1. Brand

| | |
|---|---|
| Name | **Spare Change** (replaces "Surplus Exchange" in the UI, README, CLAUDE.md and page titles) |
| Tagline | Turn spare parts into spare change. |
| Logo | A 22 px safety-orange circle with a white **¢**, followed by the wordmark "Spare Change" in white (on navy) or navy (on white), semibold. |
| Voice | Plain, specific, operational. Talks like a good procurement colleague: "3 plants run this PLC. Riverbend's line is down." No hype, no exclamation marks. |

## 2. Style: the "Workshop" direction

A clean B2B operations tool that a plant manager or procurement lead finds credible: the calm structure of Stripe's dashboard or Linear, with McMaster-Carr's spec density for part details.

- White background, generous spacing, thin 1 px borders `#D5DCE5`, **8 px corners**, no gradients, no heavy shadows. At most a 1 px hairline shadow on the sticky nav.
- Sans-serif: **Inter** (bundled with the app, not loaded from a CDN, so it works offline for graders), falling back to the system UI font. **Monospace only for part numbers** (`ui-monospace, "SF Mono", Consolas`).
- Numbers use tabular figures (`font-variant-numeric: tabular-nums`) so prices and tokens line up.

### Color tokens: one accent per side, each status has one meaning

| Token | Hex | Used for | Never used for |
|---|---|---|---|
| `navy` | `#0C2340` | Top nav, headings, structure, primary-button text | — |
| `blue` | `#2563EB` | **The Buy side's accent** (added in Phase 5): the same jobs orange does on Sell, used only on the Buy tab | Status, decoration, body text |
| `orange` | `#F97316` | **The brand accent, and the Sell side's:** primary button fill, match-score chips, the suggested-price card's top bar, the logo | Status, decoration, body text |
| `orange-text` | `#C2410C` | Orange *text* on white (score numbers, the suggested price figure) | Fills |
| `green` / `green-bg` | `#3B6D11` / `#EAF3DE` | **Only** "Compliance passed" and "Deal approved" | Anything else |
| `red` / `red-bg` | `#B91C1C` / `#FEF2F2` | **Only** "Blocked" | Errors (errors are neutral, see §6) |
| `teal` / `teal-bg` | `#0F766E` / `#E6F4F1` + leaf icon | **Only** sustainability / impact numbers | Status |
| grays | `#0F172A` text · `#5B6575` secondary · `#8A94A6` muted · `#D5DCE5` border · `#F5F7FA` subtle fill | Everything else, including "Held for review" and "Needs clarification" (gray chip + icon) | — |

**Contrast check (WCAG AA = 4.5:1 for normal text):**
- White on `#F97316`: **2.8:1 ✗**
- **Navy on `#F97316`: 5.6:1 ✓**
- `#C2410C` on white: 5.2:1 ✓
- Green on green-bg: 5.4:1 ✓
- Teal on teal-bg: 4.8:1 ✓
- Red on red-bg: 5.9:1 ✓
- White on navy: 15.8:1 ✓

→ **Decision for you:** primary buttons use the orange fill with **navy** text, not white, so they pass. The other option is a white "¢" and white text on a darker orange `#EA580C` (3.6:1, which passes for large text only).

### Type scale (laptop)

| Role | Size / weight |
|---|---|
| Page title | 22 / 600 |
| Section title | 15 / 600 |
| Body | 14 / 400, line-height 1.5 |
| Small / labels | 12 / 500, gray, sentence case (no all-caps) |
| Key figures (prices, scores) | 20–24 / 600, tabular |
| Part numbers | 13 mono |

### Spacing and shape

- 4 px base grid. Card padding 16–20 px. 16 px gaps between cards, 24 px between sections.
- Radius 8 px for cards, inputs and buttons; chips are 999 px pills.
- Icons are 16 px, 1.5 px stroke (Lucide style), always next to a text label.

## 3. Layout

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ (¢) Spare Change    Sell   Buy      Marketplace   Negotiations                     🔔 3      │  navy, 56 px, sticky
├───────────────────────────────────────────────────────────────┬──────────────────────────────┤
│ MAIN (fills the space left of the rail)                       │ RIGHT RAIL (fixed 340 px)    │
│                                                               │ ┌──────────────────────────┐ │
│                                                               │ │ Agent activity           │ │
│                                                               │ │ ✓ Pre-screen (code)      │ │
│                                                               │ │ ✓ Listing agent          │ │
│                                                               │ │ ◌ Matching agent…        │ │
│                                                               │ └──────────────────────────┘ │
│                                                               │ ┌──────────────────────────┐ │
│                                                               │ │ Cost this run            │ │
│                                                               │ │ $0.0007 · 4,723 tokens   │ │
│                                                               │ │ 58% cached               │ │
│                                                               │ │ Session $0.01 of $2.00 ▓░│ │
│                                                               │ └──────────────────────────┘ │
│                                                               │ ┌──────────────────────────┐ │
│                                                               │ │ 🍃 Impact this session   │ │  teal
│                                                               │ │ $4,275 vs $137 scrap     │ │
│                                                               │ │ 1.1 kg · est. 63 kg CO2e │ │
│                                                               │ └──────────────────────────┘ │
└───────────────────────────────────────────────────────────────┴──────────────────────────────┘
```

- Sized for **1280–1440 px** (the screenshot width for the report and slides). At 1280: main = 1280 − 340 rail − 3×24 gutters ≈ 868 px.
- **Below 1100 px**, the rail moves under the main content. It's a nice-to-have, not the target.
- The rail is sticky (`top: 72px`), so agent activity and cost stay visible while the results scroll.
- **The alerts bell** shows unread `notifications` (new matches, deals pending approval) as a count, and opens a 360 px dropdown list.

### 3.1 Demo account switcher: "what a real company sees"

There are no logins, so the nav has an account switcher that works like signing in:

```
… Negotiations                         [ (H) Hartwell Precision Components ▾  demo ]  🔔 2
                                         ┌───────────────────────────────────────────┐
                                         │ Signed in as (demo, no password)           │
                                         │ Sellers with surplus                       │
                                         │  ● Hartwell Precision Components · Dayton  │
                                         │    Lakeshore Packaging Co. · Kenosha  …    │
                                         │ Buyers with open needs                     │
                                         │    Riverbend Foods · Cedar Rapids · 1 need │
                                         │ ──────────────────────────────────────────  │
                                         │ Reset demo data                            │
                                         └───────────────────────────────────────────┘
```

- Choosing a company sets **who you are on every tab**. You post listings as that company (Sell), post needs as it (Buy), see its alerts in the bell, and negotiate on its side.
- **A company strip** under the page title shows the account as a real customer would see it: name, location, industry, the machines it runs ("runs 6× Siemens S7-1500, 2× hydraulic press"), active listings and open needs. Seeing the installed equipment explains *why* the agents match the way they do.
- **Private numbers follow the account.** A floor or ceiling is shown only when the signed-in company owns it, with a lock icon and "only you see this". Switching from the seller (Hartwell) to the buyer (Riverbend) makes the floor disappear and the ceiling appear. This makes the privacy design visible in a demo.
- The bell shows **that company's** notifications (new matches, deals awaiting approval).
- **Five featured demo accounts** sit at the top of the menu, each with a role tag and a one-line "what to try". The other 45 companies are behind **"Show all companies"**:

  | Account | Role | Opens with | What it shows |
  |---|---|---|---|
  | Hartwell Precision Components (default) | Seller | Its S7-300 CPU post | Happy path: Riverbend Foods ranked first (line down) |
  | Summit Automation Surplus | Seller · distributor | Its 1756-EN2T post | Substitute match: the buyer asked for the discontinued ENBT |
  | Redwood Coatings | Seller | An expired IPA solvent post | Blocked by the expiry rule before any matching |
  | Riverbend Foods | Buyer · line down | Empty box + hint | Its own alerts and ceiling (Buy tab, Phase 5) |
  | Tidewater Dairy | Buyer | Empty box + hint | Gets an alert when someone lists a CR 15 seal kit |

- **The paste box opens with the signed-in company's own post**, so a first-time visitor (or grader) can just click **Find buyers**. Buyers open with an empty box and a hint.
- **"Try:" chips are scenarios that sign in as the company that would post them:** Siemens PLC (as Hartwell), EN2T substitute (as Summit), Expired solvent (as Redwood), CR 15 seal kits (as Prairie Mills Flour, which alerts Tidewater). **Injection test** keeps the current account and is labelled "test", so no real-looking company is cast as the attacker.
- "Reset demo data" restores the database.

### Right rail

**Contrast decision (after Phase 4 review, Option B):** the main column is the only white surface. The rail is **one gray sidebar panel** (`#F1F4F8`, 1 px `#C9D2DE` left edge, full height) whose sections are separated by thin rules, so it reads as supporting information. The cards that carry the answer (paste box, Listing, Top buyers, Price) get a **firmer border** (`#A9B4C3`), and the suggested-price card a full orange outline. Option A (beige rail cards) was rejected: beige would have been a fourth tint next to navy, orange and teal. Mockups: `output/design/phase4-contrast-*.png`.

1. **Agent activity:** one row per step, in run order. Each row: icon + agent name + a short result, e.g. "✓ Matching agent · 3 buyers" or "⊘ Compliance rules · blocked: expired". Code steps are labelled "(code)" so you can see where no model was called. States: spinner (working), ✓ gray-green (done), ⊘ red (blocked), – gray (skipped).
2. **Cost meter:**
   - **This run:** $ cost, tokens (input / cached / output), % cached, and requests.
   - **Session:** a thin bar of spend against `SESSION_BUDGET_USD`. Gray fill, turning orange above 80%.
   - Every value comes from the `token_usage` table.
3. **Impact this session (teal):** $ recovered vs scrap value, kg kept out of scrap, est. kg CO2e avoided, each with an "est." info tooltip.

## 4. Screens

### 4.1 Sell (the first screen)

```
Sell surplus parts
Paste what you have. Agents identify the part, check it's safe to sell, find plants that run it, and suggest a price.

┌ Paste box (4 lines) ────────────────────────────────────────────────────────────────┐
│ e.g. "3x CPU 315-2DP pulled working from our S7-300 line, ~$1425 ea, Dayton OH"     │
└──────────────────────────────────────────────────────────────────────────────────────┘
Try: (Siemens PLC) (Expired solvent) (Injection test)                                             [ Find buyers ]
(posting as the account chosen in the nav switcher)

LISTING ─────────────────────────────────────────────────────────────── [✓ Compliance passed]
 6ES7315-2AG10-0AB0  Siemens · PLC CPU · SIMATIC S7-300 CPU 315-2 DP, 256 KB
 Qty 3 · Used, working · Ask $1,425 / unit · Dayton, OH · Fits: Siemens S7-300 · Discontinued by OEM

TOP BUYERS (3 of 3 compatible plants)
 [100] Riverbend Foods · Cedar Rapids, IA    Line down on S7-300 at $12k/day; runs 4× S7-300 (18 yrs)   need #1
 [ 58] Oakridge Dairy Co-op · Eau Claire, WI  Runs 3× S7-300 (16 yrs): likely future spare
 [ 56] Prairie Packaging · Sioux Falls, SD    Runs 5× S7-300 (15 yrs): likely future spare

PRICE  ┌ New ──────┐  ┌ Suggested ask ──┐  ┌ Scrap ────┐
       │ $2,966    │  │ $1,425  (orange)│  │ $45.64    │   Floor you'd accept (only you see this): $1,000
       └───────────┘  └─────────────────┘  └───────────┘   Why: 48% of new, in the used-working band; obsolete…

🍃 Recovers $4,275 vs. $137 scrap · 1.1 kg kept out of scrap · est. 63 kg CO2e avoided ⓘ      (teal strip)

OUTREACH EMAIL to Riverbend Foods                                                      [ Copy ]
 Subject: Working Siemens S7-300 CPU 315-2 DP available, for your line-down need
 Hello Riverbend Foods, Spare Change has three used-working …
```

**States:**
- **Blocked:** one red card replaces everything below the listing. "⊘ Blocked: this chemical expired on 31 Jul 2026 (exchange date 25 Oct 2026). Expired chemicals can't be listed." Then a gray line: "Matching, pricing and outreach were skipped." The rail shows those steps as "– skipped".
- **Held for review:** a gray card with an icon. "Held for a person to review: discontinued part offered new-sealed far below list price (counterfeit risk)."
- **Needs clarification:** a gray card. "This post lists 2 different items (3× 1756-IB16; 2× 1756-OB16E). Post one listing per item." It has a button: "Split into 2 listings".
- **No buyers:** an empty state. "No plant on Spare Change runs a Mitsubishi MELSEC-Q yet. Your listing is live, and you'll get an alert when a matching need is posted."
- **Loading:** the result area shows a skeleton per section, named for the working agent: "Listing agent reading your post…", "Matching agent finding buyers…", "Pricing agent checking new and scrap prices…".

### 4.2 Buy (Phase 5; first called Wanted)

Mirrors Sell for buyers:
- **Inputs:** "Post what you need" box, buying-as selector, urgency chips (Line down / High / Normal / Low), downtime cost per day, and a private max price ("only you see this").
- **Results:**
  - Need card: part or "any [family] for [machine]", urgency badge (gray; *line down* uses navy text and a ⚠ icon, not red)
  - Matched listings, each a row: part (mono) · seller · condition · ask · score · reason
  - "Start negotiation" button on each row
- The same right rail.

### 4.3 Marketplace (Phase 5)

```
🍃 Across all approved deals: $X recovered vs $Y scrap · Z kg kept out of scrap · est. N kg CO2e avoided   (teal summary row)

For sale (21)                                  │  To buy (21)
┌ 6ES7315-2AG10-0AB0 · S7-300 CPU · qty 3 ┐    │  ┌ Riverbend Foods · S7-300 CPU · line down ┐
│ Hartwell · $1,425 · used, working        │◀━━━▶│ $12k/day · need #1            [2 matches] │
└──────────────────────────── [3 buyers] ──┘    │  └──────────────────────────────────────────┘
```

- Two columns of compact cards. Each card carries an orange match-count chip.
- Hovering or clicking a card highlights its matches in the other column. No drawn lines, which get messy.
- Filter chips at the top: All / Has matches / Line down / Chemicals.

**As built (Phase 5):**
- **Buy:** post box pre-filled with the demo buyer's sample need; three fields under it: private max price (lock icon, "only you see this"), urgency as a segmented control (navy when selected; leave it empty and the agent reads it from the post), and downtime cost per day. Results: need card (with lifecycle pill Open / Matched and the private max shown only here), "Surplus that fits" with a disabled **Start negotiation · Phase 6** button per row, and a gray "N alerts sent" line. Seller accounts get a hint pointing to the buyer demo accounts. Before a run, the page lists the account's open needs.
- **Marketplace:** teal impact summary on top (potential impact of listings that fill a buy request, plus closed deals, 0 until Phase 6); two columns, For sale | To buy; orange match-count badge per card; click a card to outline it in navy, tint its matches orange (with the code's "fits" reason), and dim the rest. "you" tag on the signed-in account's own items. Filter chips were left out: with ~20 items per column they weren't needed.
- **Alerts bell:** each new-match alert has a disabled "Start negotiation · coming in Phase 6" button.
- **Reset demo:** a visible outlined button in the nav (with a confirm), not hidden in the account menu.
- Lifecycle pills use gray and navy only: green stays reserved for passed/approved and red for blocked.

**Sell vs Buy: a colour per side (Phase 5 follow-up; mockup `output/design/mockup_buy_sell.html`, option B chosen):** the two pages looked identical, so **Sell stays orange and Buy is blue (#2563EB)**. Buy's colour shows up wherever Sell's orange does: the tab underline, the small page label, the 3 px top edge of the input card, the tinted company strip, the primary button (white text on blue) and the match scores. The **tagline is the page heading** on both: Sell "Turn spare parts into spare change.", Buy "Spare yourself the downtime." The page's job ("Sell surplus parts" / "Buy parts") is a small uppercase label with an icon (tag / magnifier) above it. Status colours don't change: green passed, red blocked, teal impact. **This amends the "one accent colour" rule:** the accent is now per side (orange on Sell, blue on Buy). The Marketplace, the nav and the logo stay orange and navy. Option A (a tinted header band) was built first and then replaced at the user's request; option C (an icon marker) was too subtle.

### 4.4 Negotiations (Phase 6)

```
Negotiation #1 · 6ES7315-2AG10-0AB0 × 1 · Hartwell (seller) ↔ Riverbend Foods (buyer)        Round 4 of 6

┌ Chat (left 60%) ─────────────────────────────┐  ┌ Price by round (right 40%) ────────────┐
│ Seller agent        $1,400                    │  │  navy line = seller offers              │
│ "Pulled working, ships today."                │  │  gray line = buyer offers               │
│                        $1,100   Buyer agent   │  │  orange dot = agreed price              │
│          "Line is down; can pay fast."        │  │  (no floor or ceiling lines: they're    │
│ Seller agent        $1,300                    │  │   private)                              │
└───────────────────────────────────────────────┘  └─────────────────────────────────────────┘

┌ Deal · pending human approval ────────────────────────────────────────────────────────────────┐
│ 1 × $1,250 · Hartwell → Riverbend Foods                                   [ Reject ] [ Approve ]│
│ 🍃 This deal recovers $1,204 vs. $46 scrap and avoids est. 21 kg CO2e ⓘ                         │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

- Seller bubbles are left (white with a gray border). Buyer bubbles are right (`#F5F7FA` fill). The price sits in bold above each message.
- The **round counter** "Round 4 of 6" turns into "Final offer: accept or decline" at the cap.
- **End states:**
  - Agreed: a deal card with Approve / Reject (Approve is the orange primary button)
  - Approved: a green "✓ Deal approved by …" with the impact line
  - Walked away / round cap: a gray card with the reason
- Neither private limit is ever drawn on the chart, since that would leak it.

## 5. Sustainability layer: subtle, data-driven

**Rule: every impact number is computed in code from the catalog, never written by the model.** The LLM may only *repeat* numbers it is given.

| Figure | Formula (per listing or deal) | Source |
|---|---|---|
| **$ recovered vs scrap** | sale value = price × qty (suggested ask before a deal, agreed price after), compared with scrap = `scrap_value` × qty | `part_catalog`, `deals` |
| **kg kept out of scrap** | `weight_kg` × qty | `part_catalog.weight_kg` (new column) |
| **est. kg CO2e avoided** | `weight_kg` × qty × `carbon_factors.kg_co2e_per_kg` for the part's family (or `kg_co2e_per_unit` × qty when the factor is per unit) | `carbon_factors` (new table) |
| **Hazardous waste disposal avoided** (chemicals that are hazmat or expire within 12 months) | containers × `disposal_cost_per_unit` | `carbon_factors.disposal_cost_per_unit` |

- **Method (shown in the ⓘ tooltip):** "Estimated emissions from manufacturing one new part that this reuse replaces. It doesn't yet subtract shipping or refurbishment. Factors are placeholders until they're replaced with sourced values."
- **New data (Phase 4 build, after approval):** `part_catalog.weight_kg`, and `carbon_factors(family, kg_co2e_per_kg, kg_co2e_per_unit, disposal_cost_per_unit, source, notes)`. The `source` column reads **"PLACEHOLDER: replace with sourced value in Phase 10"** for every row now.
- **Computed by:** a new MCP tool, `get_impact_estimate(listing_id, price=None)`, plus a session total from the backend. Both are plain code.
- **Rendering:** teal text on `#E6F4F1`, a 14 px leaf icon, "est." before every CO2 number, and a 1-decimal maximum (no false precision).

**Placeholder factors (illustration only, to be replaced in Phase 10):**

| Family | kg CO2e per kg | Note |
|---|---|---|
| PLC CPU / PLC I/O / Network | 60 | electronics-heavy |
| VFD drive / Servo amplifier | 25 | electronics + metal |
| Servo motor | 9 | copper + steel |
| Pump / Pump spare | 6 | stainless + SiC |
| Bearing | 3 | steel |
| Chemicals / lubricants | 2–6 | by product |

Hazardous disposal (placeholder): $300 per 55-gal drum.

## 6. UX rules

1. **10-second test:** each tab opens with a one-line explanation of what it does and the single primary action. One orange button per screen.
2. **Named loading states:** "Matching agent finding buyers…", never a bare spinner. Show the rail's step list at the same time.
3. **Blocked = red card + visibly skipped steps.** Nothing below the block looks "done".
4. **Friendly errors, never raw text:**
   - "The AI service didn't respond. Nothing was saved. Try again in a minute."
   - "Starting up… loading marketplace tools."
   - The technical detail goes to the audit trail, not the screen.
5. **Empty states** say what will happen next: "You'll get an alert when…"
6. **Sentence case everywhere:** "Find buyers", not "Find Buyers". Numbers use thousands separators. Money shows 2 decimals under $100 and 0 above.
7. **Private numbers are labelled:** a floor or ceiling only appears to its own side, with a lock icon and "only you see this".
8. **Laptop first:** checked at 1280 and 1440 px before every screenshot.

## 7. Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Button contrast | **Decided:** orange `#F97316` fill with **navy** text (5.6:1). `#C2410C` for orange text on white. |
| 2 | "Held for review" / "Needs clarification" | **Decided:** gray chip + icon (no new colour; red stays "blocked" only). |
| 3 | Price chart colours | **Decided:** seller line navy, buyer line gray, agreed price an orange dot; private limits never drawn. |
| 4 | Who is using the app (no logins) | **Decided:** a **demo account switcher in the top nav** (see §3.1). It applies to every tab. Real sign-in (e.g. SSO for plant staff) is listed under the report's "Limits + next steps". |
| 5 | Rename scope | **Decided:** everything a user or grader sees becomes "Spare Change" (UI, page title, README, CLAUDE.md, report, slides, **GitHub repo `spare-change`**). Internal code names (`surplus-exchange` MCP server, `SURPLUS_*` env vars, file names) stay. |
