# Timed self-test: manual process vs. Spare Change

> **Measured by the author, not an independent user.** This is the "own tests" evidence for the Impact section. It is not a user study, and no user feedback or quotes are recorded here. A pilot with a plant maintenance manager is planned (see `output/impact_model.md`, *Planned pilot*).

**Tester:** Simrah Palla (author) · **Date:** ________ · **Device / browser:** ________

## What to do, for each of the 2 items

Use a stopwatch. Start when you begin the task; stop when the result is ready to send. Do the manual way first, so the app's answers don't help you.

**Manual way (today's process):**
1. Write a marketplace-style listing for the part (title, part number, condition, quantity, price), as you would on eBay or a surplus site.
2. Look up the part's compatibility (which machines or PLC platforms it fits, and any replacement part numbers) with Google or the maker's site.
3. Find 3 plausible buyers (companies likely to run that machine) with Google or LinkedIn, and note why each fits.

**Spare Change way:**
1. Sign in as the seller (account menu), paste the same messy description on **Sell**, and click **Find buyers**.
2. Stop when the listing, the compliance check, the top buyers with reasons and the suggested price are on screen.

### How to do the manual way (no supply-chain background needed)

Cap each step at **15 minutes**. If you're not done by then, write "15:00+ (not finished)": that is a real result.

**Step 1: write the listing. Fill in this template** (decode everything from the seller's text):
> **Title:** [brand] [model / part number] [what it is] – [quantity] available
> **Part number:** ______ · **Brand:** ______ · **Condition:** new / used-working / refurbished / for parts · **Quantity:** ______
> **Price:** $____ each · **Location / shipping:** ______
> **Notes:** firmware, damage, what's not included (e.g. memory cards)

**Step 2: compatibility.** Search the part number plus "datasheet" or "replacement":
- S7-300 CPU: search `6ES7315-2AG10-0AB0` and open the Siemens product page (support.industry.siemens.com). Note the **product family** (which PLC system it belongs to) and whether there's a **successor** part.
- EN2T: search `1756-EN2T replaces` or `1756-ENBT discontinued`. Note which **system** it plugs into (ControlLogix) and which **older module** it replaces.
- Write 1–2 lines: "fits ______; replaces / is replaced by ______."

**Step 3: find 3 plausible buyers.** A plausible buyer is a real company with **evidence it runs that system**. The easiest evidence is a job posting:
- Search Google, Indeed or LinkedIn Jobs for `"S7-300" maintenance technician` (Item A) or `"ControlLogix" maintenance technician` (Item B). A plant hiring people to maintain that system runs it.
- Prefer plants in manufacturing (food and beverage, packaging, automotive parts, paper, metals) and, for Item A, within shipping distance of Dayton, Ohio.
- For each buyer, write one line: **company, city, evidence** (e.g. "job post mentions S7-300").

**Suggested items** (both are in the demo data; use these descriptions for both ways):
- **Item A:** Hartwell's S7-300 CPUs: *"clearing out old S7-300 stuff after line 2 retrofit to 1500s. have 3x CPU 315-2DP (6ES7 315-2AG10), pulled wrking last month, fw 2.6, few scuffs on housing. no MMCs. ~$1425 ea. pickup dayton or we ship"*
- **Item B:** Summit's EN2T modules: *"3 ea AB 1756-EN2T enet modules, used, tested, current firmware. $1,095 ea"*

## Results (fill in)

| Item | Manual: listing (mm:ss) | Manual: compatibility (mm:ss) | Manual: 3 buyers (mm:ss) | **Manual total** | **Spare Change total** | Notes |
|---|---|---|---|---|---|---|
| A: S7-300 CPU (6ES7315-2AG10-0AB0) | | | | | | |
| B: 1756-EN2T | | | | | | |

**Quality check (fill in):** did the manual search find the same compatible platforms and replacement relationships as the app (e.g. EN2T replaces the discontinued ENBT)? Were the 3 manual buyers plausible, and how sure were you of each?

| Item | Manual found the right compatibility? | Manual buyers plausible? (0–3) | App buyers plausible? (0–3) | Notes |
|---|---|---|---|---|
| A | | | | |
| B | | | | |

## How to report it

State the times side by side, with the label "measured by the author, not an independent user". Note two biases honestly: you designed the app (you know what to search for, which favours the manual time), and you are not a supply-chain specialist (which may slow the manual time). The manual steps followed the how-to above; nobody supplied the answers. Under Limits and next steps: *"Next step: a pilot with a plant maintenance manager."*
