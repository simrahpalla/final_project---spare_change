# AI Prompts Log — Final Project (Surplus Exchange)

This file records the prompts I used while building my MGT 409 final project, Surplus Exchange.

## Project Context — Surplus Exchange

### Initial prompt

> hi there! Today we have a big task ahead of us - we are going to build my final project - look at the final project folder in the ai foundations folder

### What was missing

- It didn't link the official project requirements page, so the grading rubric and submission rules had to be added from the course site.
- It didn't say how to document the work as we go (an `AI_prompts.md` log and HW5-style output files).

### Follow-up prompt(s)

> great - just a couple things before we start. Here is the link to all the details about the project and what I need to submit and the grading etc so you can use it as reference throughout and make sure we are covering everything https://zlisto.github.io/mgt_409_fa26/project_requirements.html
>
> and then the image attached is what we submitted for hw 5 - i only include that to give you a reference point for the way in which the professor likes to see homework submissions and things documented - so if there are such things that we should do as we go along, lets make that happen - one example is /ai-prompts-md - which we should do for this project the same way we have done for homeworks

## Phase 0 — Set Up from the HW5 Skeleton

### Initial prompt

> Yes, start Phase 0: copy the HW5 skeleton into the final project folder as surplus-exchange, set up the .env lookup (repo folder then parent), have FastAPI serve the built frontend, and run a test call to gpt-6-luna.

### What was missing

- It didn't give the gpt-6-luna token prices (input, cached, cache write, output), so costs started with placeholder rates.

### Follow-up prompt(s)

> 2 - see image for the gpt 6 luna price
> 1 -i clicked enter - did it work

> Yes, make the Phase 0 commit for me. I'll take the screenshot myself.

## Phase 1 — Synthetic Marketplace Data

### Initial prompt

> Start Phase 1: build the seed script and synthetic database. Include the screenshot in the next commit.

### What was missing

- It didn't define what "solid enough" meant for the later phases. The follow-up added explicit data-quality checks: how many plausible buyers each listing has, matches that only work through compatibility, decoys, price logic, a mix of negotiation outcomes, messy raw text, subtle bad records, privacy of floors and ceilings, and reproducibility.
- It didn't ask for answer keys to score the agents against, a data report, or a reset script.

### Follow-up prompt(s)

> Before we close out Phase 1, I want to make sure the database is solid enough for the later phases (matching, negotiation, safety tests, evals). Please do the following and don't start Phase 2 yet
>
> 1. Write scripts/data_report.py that reads the working DB (no model calls) and prints a report, also saved to output/data_report.md:
>    - Row counts for every table
>    - For each listing: how many buyers could plausibly use it and why (installed equipment, compatibility/substitute, or open need)
>    - For each open need: how many listings could fill it
>    - Negotiation pairs split into: overlapping (deal likely), non-overlapping (walk away), barely overlapping (multiple rounds)
>    - The deliberately bad records, what's wrong with each, and which check should catch it
>
> 2. Run these checks and tell me PASS/FAIL for each, with a fix for every FAIL:
>    - Most listings have 1–3 plausible buyers; 2–3 listings have none. No listing has 10+.
>    - At least 5 matches only work through compatibility/substitutes (listing has a part number, buyer only lists the machine/platform), so keyword search would miss them.
>    - At least 3 decoys: same manufacturer but wrong platform/voltage/series.
>    - Prices are logical: scrap_value well below new_price, asking price in between, condition affects price, no suspiciously round numbers everywhere.
>    - Negotiation pairs are a mix of all three types above, not all easy deals.
>    - raw_text in listings is messy like a real plant manager wrote it (abbreviations, missing fields, typos), while the structured fields are the clean truth.
>    - Bad records: prompt injection, expired chemical, hazmat with no SDS, ~10x overpriced, plus 1–2 subtle ones. Each tagged with the expected outcome.
>    - Seller floors and buyer ceilings live only in the private tables, not in listings or needs.
>    - Seeding is reproducible (fixed random seed, rerun gives an identical DB), the original DB is never modified, and reset to the working copy works.
>    - Dataset is small enough to ship in the repo as the test dataset.
>
> 3. Create data/answer_keys.json, since you created the data you know the right answers:
>    - For each listing: the correct structured fields (to score the listing agent)
>    - For each listing and each need: the correct top match(es) (to score matching)
>    - For each negotiation pair: whether a deal should happen and the possible price range
>    - For each bad record: which check should block it
>    Make sure every answer key matches the DB (write a quick consistency check).
>
> 4. Fix anything that failed, reseed, and rerun the report until everything passes.
>
> 5. Pick 3 records for me to spot-check myself: one normal listing, one tricky compatibility match, one bad record. Show them in plain English.
>
> 6. Update output/harness.md (data section), note in the README that the data is synthetic and how to reset it, and log this prompt in AI_prompts.md.
>
> 7. give me a 100 word or so summary of how you fared agaisnt all these checks
> 8.
>
> Then stop at the checkpoint: list the evidence files produced, what I should commit, and the screenshot to take (phase1-data-report).

> do I need to do anything? I tried to run the script but i dont think it worked

> Got it, I'll cd first. Yes, go ahead with my Phase 1 data-hardening request: data_report.py, the checks, answer_keys.json, fixes, spot-checks, docs and summary. Don't start Phase 2.

## Phase 2 — MCP Server Tools with Role-Based Access

### Initial prompt

> Start Phase 2: build the MCP server tools with role-based access and the smoke test.

### What was missing

- It didn't say the smoke test would be slow on my machine (about 15 server processes start one after another), so the first run looked stuck.
- It didn't list a few tools I wanted. They were added in Phase 3: a dedicated `walk_away`, `end_negotiation` and `get_company_profile`.

### Follow-up prompt(s)

> i tried to run it but it didnt work

> here - is this fine

## Phase 3 — The Agents

### Initial prompt

> yes start phase 3 but during it, can you also add these few tools that I feel we are missing and test them too
>
> *(attached table)* `get_negotiation_state` (seller_agent, buyer_agent): negotiators need the offer history, round number and status, hiding the other side's limit · `walk_away` (or `end_negotiation`) (seller_agent, buyer_agent): `submit_offer` is the only way to act, so an agent can't decline · `save_matches` (broker): matching results must reach the `matches` table · `get_listing` / `get_buyer_profile` (broker, negotiators own side only): specific match reasons ("runs 4 S7-300 lines")

### What was missing

- It didn't account for tools that already existed under other names (`get_negotiation` = `get_negotiation_state`, `record_matches` = `save_matches`), so only the missing ones were added: `walk_away`, `end_negotiation` and `get_company_profile`.
- It didn't ask for a broad test of the agents. The happy-path sample was small, so a stress test followed.

### Follow-up prompt(s)

> Try again

> here 0 is this fine? if so, save them. wait to commit phase 3 till i say so

> Phase 3 works on the happy path, but the sample is small. Before Phase 4, I want to pressure test the agents. Don't change agent designs until you've reported results to me.
>
> Write scripts/stress_phase3.py and save the results to output/phase3_stress.json and a readable output/phase3_stress.md. Include:
>
> 1. Coverage: run EVERY listing through the seller flow. Score extracted fields and top-1/top-3 matches against data/answer_keys.json. List each failure with the reason.
> 2. Messy inputs: typos, no part number, two items in one paste, gibberish, empty input, a very long paste. The app should ask for clarification or report low confidence, never crash or confidently make things up.
> 3. Made-up facts: a part number not in the catalog should come back as unknown, not invented specs. Check every match reason against the DB and flag any claim that isn't true in the data.
> 4. Bad records: injection, expired chemical, hazmat with no SDS, overpriced. Confirm they're blocked at compliance and that matching and pricing never run (check the audit trail). Confirm obvious cases are blocked by code with no model call.
> 5. Negotiation variance: run each negotiation pair 3 times. Report outcome consistency, rounds, and final prices, and confirm offers only move one way and never break a limit.
> 6. Leak check: scan every negotiation message for the other side's private floor or ceiling. Include a buyer message trying to extract the seller's floor.
> 7. Caps: rerun with MAX_NEGOTIATION_ROUNDS=2 and MAX_MODEL_REQUESTS=3. It should stop gracefully with a logged reason.
> 8. Permissions: try calling tools outside each agent's role, including approve_deal. Should be refused and logged.
> 9. Failures: simulate a model timeout and malformed output. Should retry once, then return a friendly error.
> 10. Record tokens and cost per test so we can spot expensive outliers.
>
> Give me a PASS/FAIL table with a proposed fix for each FAIL, then stop. Log this prompt in AI_prompts.md.

> do we need the full stress test? can we just do it for a few of each type without messing up the quality

> hows the progress

> fix all 6 - but is there anything we can do to fix that extra finding about the 5 seconds and it being slow on the onedrive? is that something that will get sorted when we publish to github

> The 30s timeout is fine for startup, but I don't want it to be the main fix. Please do the process reuse now, not in Phase 4:
> - Start the MCP server once at backend startup (FastAPI lifespan) with one persistent connection per role. All runs reuse it. Keep the 30s timeout only for that first startup, and show a "Starting up…" state in the UI until it's ready.
> - Per-call timeout of about 15s with one automatic reconnect, then a friendly error. Log every reconnect in the audit trail.
> - Make concurrent calls safe: a lock or small queue on the shared connection, and SQLite in WAL mode.
> - Rerun the concurrency test (2 at once and 6 at once, same as before) and report crash counts before vs. after in output/phase3_stress.md.
> Log this prompt in AI_prompts.md.
>
> before you do it - does this seem like a reasonable fix?

> Yes, do the process reuse with your four adjustments: negotiator processes per negotiation (reused across its turns), a lock only around connection use/reconnect, WAL on the working copy only with -wal/-shm ignored, and the concurrency test run through the backend API. Log my prompt.

> in the meantime - can I give you some instructions on design to include in phase 4 - we wont start phase 4 yet but just want you to get more familiar with my design vision

## Phase 4 — Design Direction (Spare Change)

### Initial prompt

> Phase 4: before building any frontend, set the design direction and write it to output/design.md. Don't code screens until I approve it.
>
> use the design guidelines here as the direction overriding and replacing any design features that were in the agents.md
>
> BRAND
> - Name: Spare Change. Tagline: "Turn spare parts into spare change."
> - Logo: a small orange circle with a white "¢" next to the "Spare Change" wordmark.
> - Update the name everywhere: CLAUDE.md, README, page titles, design.md.
>
> STYLE (Workshop direction)
> - Clean B2B operations tool that feels credible to a plant manager or procurement lead, like Stripe's dashboard or Linear, with the spec density of McMaster-Carr for part details.
> - White background, generous spacing, thin borders (#D5DCE5), 8px corners, no gradients or heavy shadows. Clean sans-serif (Inter or the system font), with monospace only for part numbers.
> - Colors:
>   - Navy #0C2340: top nav and structure
>   - Safety orange #F97316: the ONE accent, for primary buttons, match scores and suggested price
>   - Green #3B6D11 on #EAF3DE: only "compliance passed" / "deal approved"
>   - Red: only "blocked"
>   - Teal #0F766E on #E6F4F1 with a leaf icon: only sustainability/impact numbers, so impact never gets confused with status
>   - Everything else in grays
>
> LAYOUT
> - Top nav: logo and wordmark, tabs Sell | Wanted | Marketplace | Negotiations, and an alerts bell.
> - Main content on the left. A fixed right rail with:
>   1. Live agent activity (each agent step with a check mark, a spinner, or "blocked")
>   2. Cost meter (tokens, $ for this run, % cached, session budget bar)
>   3. Impact this session (teal): $ recovered vs. scrap value, kg kept out of scrap, est. kg CO2e avoided
>
> SUSTAINABILITY LAYER (keep it subtle, not a green theme)
> - On every listing result, show a teal impact strip: "Recovers $X vs. $Y scrap · Z kg kept out of scrap · est. N kg CO2e avoided".
> - For near-expiry chemicals, also show "hazardous waste disposal avoided: est. $X".
> - On the deal card after approval: "This deal recovered $X and avoided est. N kg CO2e."
> - Add a small impact summary at the top of the Marketplace tab: total value recovered, kg diverted, CO2e avoided across all deals.
> - Numbers must come from data, never be made up by the LLM. Calculate them in code from the catalog:
>   - Add weight_kg to part_catalog, and a carbon_factors table: part family, kg CO2e per kg (or per unit), source, notes.
>   - Use clearly labeled placeholder factors for now. I'll replace them with researched, sourced values in Phase 10.
>   - Label every CO2 figure "est." with an info tooltip explaining the method: avoided manufacturing emissions of a new part, minus nothing else for now.
>   - Document the method in design.md and harness.md.
>
> SCREENS (sketch all four in design.md so Phases 5 and 6 fit the same structure)
> 1. Sell: a one-line explanation of the app at the top, a paste box, "Try:" example chips (Siemens PLC, expired solvent, injection test), and a "Find buyers" button. Then:
>    - listing card (part number in monospace, specs, compliance badge)
>    - top 3 buyer matches, each with a score and a one-line reason
>    - price cards (new / suggested ask / scrap)
>    - impact strip
>    - drafted outreach email with a copy button
> 2. Wanted: buyer posts a need, sees matched listings.
> 3. Marketplace: impact summary on top, then two columns (available surplus | wanted) with match badges.
> 4. Negotiations: chat bubbles (seller left, buyer right), price-by-round line chart, round counter, and a deal card with Approve / Reject plus its impact line.
>
> UX RULES
> - A first-time user understands the page in 10 seconds.
> - Loading states name the agent that's working ("Matching agent finding buyers…"), not a generic spinner.
> - Blocked listings show a clear red card explaining why, and skip the downstream steps visually.
> - Friendly empty states and errors, never raw error text.
> - Sentence case and consistent spacing everywhere.
> - Must look good at laptop width (1280–1440px), since screenshots go in the report and slides.
>
> Show me design.md and a first-screen mockup, then stop for my feedback. Log this prompt in AI_prompts.md.
>
> you dont need to do any of the updates to files yet if its better to commit phase 3 first but if there are things you can do now, do them

### What was missing

- It didn't account for contrast: white text on #F97316 is 2.8:1, below the 4.5:1 accessibility minimum, so the button text colour had to be decided.
- It didn't give colours for states other than passed, approved and blocked ("held for review", "needs clarification"), or for the two lines of the price chart.
- It didn't say how the demo knows which company is posting (there are no logins), or whether the rename covers the GitHub repo and code identifiers.

### Follow-up prompt(s)

> commit phase 3 then I'll answer your questions

> okay for the decisions
> 1- sure
> 2- sure
> 3 - makes sense
> 4 - what does this mean?
> 5 - what do you suggest

> dont we eventually need to have logins

> yes build the switcher in nav - i want to have a way for them to see what a real company's experience would look like on the website. and yes for #5 your recommendation sounds good

> i want to try to run the demo - what is the tet that should be here? where did it go?

> no need to rebuild the whole thing - its more that when my professor opens the demo, there should already be text there and they should just be able to click find buyers right? since the professor wont have that text to provide - i liked the text you had thats in the screenshot you took - see image - does that make sense?

> what does this mean - The example chips still swap in the expired-solvent and injection examples.

> okay makes sense. but - why are there demo accounts for all companies? shouldn't one suffice? and if we do have them, shouldnt their prompts and listings be different

> Yes: 5 featured demo accounts at the top of the switcher, each with its own pre-filled post and a one-line 'what to try', chips that switch to the right account, and the other companies behind 'Show all companies'.

> here you go - save these screenshots and commit phase 4
