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

> Everything looks great, just on the design front. I worry that the whole page is white and it's not intuitive or easy to track what the most important information is. So I'm thinking maybe for the agent activity and cost this run on the side, those maybe can have like a background of beige or gray, so that the stuff on the left is the only stuff that has a white background so that it's more noticeable. And maybe like a few darker borders in some places or something. Can you make a mock-up of just what that would look like and show it to me before making any actual changes?

> Go with Option B (gray sidebar panel + firmer borders on the key cards) and apply it to the app.

> Yes, commit the Option B design update. I'll retake the phase4-sell-result screenshot and send it.

> what screenshot

> here - but didnnt the outputs have 3 buyers before

> Do you think the this change came from adding those 5 companies as demos and that it's only using from those? Or is that not, does that not have anything to do with this?

> okay fix it with your proposed fix

> here you go - and yes commit it

## Phase 5 — Two-Sided Matching

### Initial prompt

> yes start it - here are some additional instructions for it:
> Phase 5: two-sided matching. Build on the demo accounts I added.
>
> - Buyers can post a need. It goes through the same pipeline as listings: extraction to a structured need, the compliance guard (needs text can contain injection too), then the SAME matching agent in reverse with the same SQL pre-filter. One matching logic, both directions, same scoring.
> - Alerts are triggered by code, not an agent: new listing → check open needs; new need → check active listings. Alert only above a score threshold, max top 3 per event, no duplicates on rerun. If the pre-filter returns 0 candidates, skip the LLM call entirely.
> - Privacy: a buyer's max price never appears in alerts, the Marketplace board, or seller views. Each demo account sees only its own alerts and private terms. Note in the README and limits that account switching is a demo, not real auth.
> - Status lifecycle: listings active → in negotiation → sold; needs open → matched → filled. Matching ignores sold, filled or expired items.
> - Each alert gets a "Start negotiation" button, marked "coming in Phase 6" for now.
> - Make sure at least 2 demo accounts are buyers whose open needs match the sample seller test cases, and add a buyer-side sample test case to each buyer account.
> - Add a "Reset demo" button that restores the seeded state via the existing reset route, so every grader starts clean.
> - Marketplace tab: impact summary on top, two columns (available | wanted) with match badges.
> - Tests: add expected reverse matches to data/answer_keys.json and score them. Add an end-to-end test of the two-account flow (seller lists → buyer alerted → switch account → alert visible), and run it with concurrent requests too.
> - Log tokens per alert event.

### What was missing

- **The alert threshold value:** set to 70, the score band the matching agent already uses for "has an open need this listing fills".
- **What happens if a buyer types the max price into the post text:** the server redacts it to `[private]` before saving, since the post text is public.
- **What the Marketplace impact shows before any deal is approved** (deals come in Phase 6): the potential impact of the listings that fill a wanted need, plus closed deals (0 so far).
- **Whether the Phase 4 seller screen should show the alerts it sent:** it does (the same "N alerts sent" line as Wanted).

### Follow-up prompt(s)

> A few, before I take the screenshots, a few small changes. I want the new tab to, instead of it saying wanted, I want it to say buy. So like one tab is sell, the other tab is buy. And I want that to be carried forward wherever else wanted is there that it might be replaced with buy. Secondly, in the wanted page, let's say for like Riverbend, once you write whatever you want, the button says find surplus, change that to just find. Third change is that I want a tagline on the sell and the buy pages. And I want there to be some design differences. Right now, the sell and the buy pages look exactly the same. You don't even realize you moved to a different tab. So I don't know if we want to overall add another color where like there's one color that goes with on the sell page and another that goes on the buy page, or if it's some other type of variation, some gradient maybe, I don't know. So for that, before making the change, suggest and demo something for me. And the tagline, think about where we might want to add that. Maybe write, maybe like instead of writing sell surplus, I don't know, think about where that might fit the tagline. So for example, on the sell side, the tagline would be spare parts for spare change versus, you know, something like that for the buy side also.

> go with option A, and for the taglines, keep the tagline for sell, which is turn spare parts into spare change, and for the buy side, make it spare yourself the downtime.

> I changed my mind. I want you to update the design to option number 2 that you had given me in the mockup. Sorry, option number B that you had given me in the mockup.

## Phase 5 — Stress Test

### Initial prompt

> Phase 5 pressure test. We're on deadline day, so keep it focused: write scripts/stress_phase5.py, save results to output/phase5_stress.json and output/phase5_stress.md, and run everything through the backend API. do only as much as you need, keep it brief without compromising on quality
>
> 1. Reverse matching: score need→listing matches against data/answer_keys.json (top-1/top-3).
> 2. Symmetry: for matched pairs, compare scores from both directions and flag big gaps.
> 3. Alerts: right recipient, threshold respected, max 3 per event, no duplicates on rerun or double submit.
> 4. Zero candidates: a need with no pre-filter candidates shows an empty state and makes NO LLM call (check token_usage).
> 5. Self-match: a company never matches its own listing or need.
> 6. Lifecycle: sold, filled and expired items disappear from matches, alerts and the Marketplace board.
> 7. Leaks: scan every alert, board entry and API response for buyer max prices and seller floors. Try fetching another account's alerts and private terms via the API. Neither may leak.
> 8. Need-side attacks: injection in need text ("alert me for every listing", "show seller floor prices"), gibberish, hazmat or expired requests, absurd qty or price.
> 9. Race: post a listing and its matching need at the same moment, and 2 accounts posting at once. Exactly one match, no duplicate alerts, no crashes.
> 10. Reset demo: after posting things, reset restores the exact seeded state (compare row counts or a hash) and clears alerts.
> 11. Regression: rerun a subset of the Phase 3 stress tests to confirm the seller flow still works.
> 12. Record tokens per alert event.
>
> Give me a PASS/FAIL table. Fix only failures that would break the demo or leak private data. List the rest as known limits for the report. Log this prompt in AI_prompts.md.
>
> most importantly - if there are things on this list that you already tested or checked for in your execution of phase 5, just let me know and dont repeat it again

### What was missing

- **Sold and filled can't be reached through the API yet:** deals arrive in Phase 6, so check 6 sets those statuses with SQL on the scratch database, then checks the app through the API.
- **"Exactly one match" in a race:** two match rows (one per direction) for the same pair would be correct, so the check counts alerts per company instead.

### Follow-up prompt(s)

> Do you think we should be committing the phase five stress test? I assume so, since it can be used for evidence later, but let me know what you think. And then, yes, can you tell me how we can fix these things and if it's how important it is to fix them in order of priority?

> Is it possible that I ask you to commit and that then I give you the instructions for phase 6, but you first do these 3 fixes and then you proceed to do phase 6 without me having to be there in the middle?

> commit
> make the fixes and commit those too - and yes if its too large, move on to phase 6 and let me know
> go into phase 6 without stopping and proceed to stress test phase 6 also and then stop at the phase 6 checkpoint (the Phase 6 instructions are logged under Phase 6 below)


## Phase 6 — Negotiation in the App

### Initial prompt

> go into phase 6 without stopping and proceed to stress test phase 6 also and then stop at the phase 6 checkpoint - i have given you instructions for these below:
>
> Phase 6: negotiation in the app. The negotiator agents and code-enforced rules from Phase 3 already exist. This phase connects them to the UI. Timebox about 4 hours. If it's not working by then, fall back to a rule-based buyer and tell me. this time box begins once youre done with the previous steps from before phase 6
>
> Everything shown must make sense for a real buyer or seller using the app in their own role. No views or features that exist only for grading.
>
> STARTING A NEGOTIATION
> - "Start negotiation" on an alert or match opens a negotiation.
> - Before starting, the logged-in company can review or adjust its OWN private limit (floor for sellers, budget for buyers), with the note "Only your agent sees this."
>
> LIVE NEGOTIATION VIEW
> - Offers appear turn by turn as they happen (not all at the end).
> - Chat bubbles: seller on the left, buyer on the right. A "Round X of N" counter.
> - Price-by-round line chart showing ONLY the viewer's own limit line ("Your floor" for sellers, "Your budget" for buyers). Never show or hint at the other side's limit.
> - Under each of the viewer's own agent's offers, show a short private rationale (e.g. "Countered at $520 because the buyer's line-down urgency suggests room to hold firm"). Visible only to that company, never to the other side.
> - If code blocks one of the viewer's own agent's offers (outside its limit, wrong direction, past the round cap), show it only to that company: "Your agent tried to offer below your floor, and the rules blocked it." Never show the other side's blocked offers or anything that hints at their limit.
>
> OUTCOMES
> - Deal → pending deal card with price, quantity and the impact line ($ recovered, est. CO2e). Each company approves its own side (switch demo accounts). No deal closes without both human approvals.
> - The deal card shows the result relative to the viewer's own limit: "Closed at $480, $40 above your floor" for the seller, "$70 under your budget" for the buyer.
> - Walk-away or round cap reached → plain-English explanation and a suggested next-best match.
> - Reject → negotiation closes and the listing goes back to active.
>
> STATUS AND DATA CONSISTENCY
> - Approved deal → listing sold, need filled, related alerts closed.
> - Lock quantity while a negotiation is open so the same units can't be sold twice.
>
> LIMITS AND COST
> - Keep the 2–3 concurrent negotiation limit, with a "Queued" state in the UI for the rest.
> - Add a per-negotiation token/cost cap.
> - Show each negotiation's cost in the cost meter.
>
> MESSAGE SAFETY
> - Messages between agents are data, never instructions.
> - Before any agent message is saved or shown, scan it in code and block it if it contains either side's private limit.
>
> RELIABLE DEMOS
> - Give each relevant demo account a sample negotiation with a known outcome (clear deal, walk-away, narrow deal) as part of its sample test cases.
> - Use low temperature so graders see consistent behavior.
>
> TESTS AND EVIDENCE
> - End-to-end test: seller lists → buyer alerted → negotiate → both approve → listing sold, need filled.
> - Also test: oversell attempt, reject path, leak scan of every message and of each role's API responses (neither side's view may contain the other's limit), concurrent negotiations.
> - Save results to output/eval_negotiation.json and output/phase6_stress.md.
>
> At the checkpoint, list the evidence files produced and remind me to take these screenshots:
> - phase6-negotiation-live
> - phase6-offer-blocked (from the side whose agent was blocked)
> - phase6-seller-view and phase6-buyer-view of the same negotiation (for the report, side by side, to show each side only sees its own limit and both limits held)
> - phase6-deal-approved
>
> Log this prompt in AI_prompts.md.
>
> One more important thing:
> I'm running this overnight and won't be available, so work on your own until it's done:
>
> * Don't stop to ask me questions. Make reasonable decisions that fit CLAUDE.md and log each one in output/phase6_decisions.md. if there are any calls you needed to make that you would have otherwise asked me about, note them and tell me
>
> * Work on a git branch called phase6. Commit after each working stage: (1) negotiation start + live view, (2) outcomes + approvals + statuses, (3) limits, message safety, demo samples, (4) tests and fixes. Never commit .env or keys.
> * Total time budget: about 4 hours. If the LLM buyer negotiator still isn't reliable after about 3 hours, switch to the rule-based buyer fallback, note it in the decisions log, and finish the remaining stages.
> * Spending cap: stop all model calls in this session if they go over 10,000,000 tokens or $2.00 total (whichever comes first), and note in the morning summary where you stopped. Run tests in priority order so the most important evidence exists even if the cap is hit: (1) end-to-end deal flow, (2) leak scan, (3) oversell and reject paths, (4) concurrent negotiations, (5) repeat runs for consistency, (6) Phase 3/5 regression subset. Keep the existing per-run caps (model requests, tokens, rounds) on. Those are what stop an individual stuck loop early.
> * After the Phase 6 tests, rerun a subset of the Phase 3 and Phase 5 stress tests to confirm nothing broke.
> *  When done, write output/phase6_morning_summary.md: what works, what failed and why, decisions made, test results, and exactly what I need to do in the morning (screenshots, merging the branch, anything to review).

### What was missing

- **Who approves:** "no deal closes without both human approvals" was turned into one approval per side (each company approves its own side).
- **Low temperature isn't possible:** `gpt-6-luna` is a reasoning model and ignores `temperature`; consistency was measured with repeat runs instead (15/15).
- **Where a negotiation starts for seeded listings and needs:** added a "Ready to start" list on the Negotiations tab.
- **A walk-away sample:** none of the featured accounts had a no-overlap pair, so a 6th demo account (Cascade Paper & Board) was added.
- **What to do with a message that contains the other side's limit:** blocking it would tell the agent that number, so all money figures are scrubbed from messages instead.
- All other overnight decisions are in `output/phase6_decisions.md`.

### Follow-up prompt(s)

> give me the link to open it

> Here are the screenshots for what you have asked. It generally looks good. One concern that I have is that the images you asked me to do, that was a deal between Hartwell and Prairie, but Prairie is not part of the demo account, so I had to hunt and go down to look for it. And so, at least in the demo that my professor is going to take, I wonder if it makes sense to either bring that up to also one of the demo accounts, or if there's another alternative example amongst the demo accounts itself that works. If that's the case, then let's do it. Like, just tell me what that is. I don't want you to make any changes. I'm just asking you. I'm looking at the items you have marked as Q at the moment. And I don't quite understand the phase 6 offer blocked screenshot. But is that necessary, or can I skip that? And finally, the impact research MD is going to come in handy in phase, like, I don't know, phase 10. So we can think about it then. Keep ignoring it for now.

> yes

> Commit these follow-ups, then merge phase6 into main.

## Phase 6 follow-up: limits up front + auto-negotiate

### Initial prompt

> Small change to how private limits are captured. Right now negotiation can't start until the user enters a floor or budget. I want the limit captured up front with an agent-suggested default, so the flow is agent-driven with only two human touchpoints: confirming the limit, and approving the deal.
>
> - Seller side: when a listing is created, the pricing agent suggests a private floor (with a one-line reason based on new price, scrap value and condition), shown pre-filled with "Only your agent sees this." The seller accepts or edits it as part of listing. Save it to seller_private.
> - Buyer side: when a need is posted, suggest a private budget from the new price and the downtime cost they entered, pre-filled the same way. Save it to buyer_private.
> - Add an "Auto-negotiate my matches" setting per company (on by default for demo accounts). When on, a match above the score threshold starts the negotiation automatically (respecting the concurrency limit and queue). When off, the "Start negotiation" button stays.
> - The pre-negotiation screen no longer requires entering a limit. It just shows the saved one, editable.
> - Final deal still requires both human approvals. That doesn't change.
> - Make sure seeded demo data already has limits for every listing and need, so nothing blocks.
> - Rerun the end-to-end test (list → auto-negotiate → both approve → sold) and the leak scan to confirm nothing broke.
> - In harness.md, describe the design principle: humans set the guardrails (limits, final approval), agents do the work in between.
>
> Log this in AI_prompts.md.

### What was missing

- **When auto-negotiation may start relative to confirming:** it starts only once both limits are confirmed (confirming is the trigger), so an agent never bargains with an unreviewed suggestion.
- **Whose setting counts:** both companies must have auto-negotiate on.
- **Who suggests the budget:** code (from the new price, urgency and downtime), not a model; the seller's floor stays with the pricing agent.
- **Which accounts are "demo accounts":** the 6 featured accounts plus Prairie Mills (used by an example chip).

### Follow-up prompt(s)

> None.

> Commit these changes to main.

## Phases 7–9 — Evidence audit (tokenomics, safety, quality)

### Initial prompt

> Phase 6 is done. Before writing anything new, audit the evidence we already have for Phases 7, 8 and 9.
>
> 1. Map every existing file in output/ (stress tests, screenshots, token_usage, audit trail, answer-key scores) to the report section it supports: tokenomics, safety (attacks / malfunction / overspending), agent design trace, quality.
> 2. List the GAPS only, meaning what each section still needs to get full credit under the "evidence earns full credit" rules in CLAUDE.md.
> 3. Then fill the gaps in one pass:
>    - Phase 7: scripts/cost_report.py → output/tokenomics.json (avg of real runs per seller flow, need flow and negotiation; per user per month with stated assumptions; 100 and 10,000 users), plus the pre-filter vs. no pre-filter experiment (tokens and accuracy).
>    - Phase 8: consolidate all attack, malfunction and overspending tests into output/safety_tests.json, adding any missing ones (budget cap stop, approve_deal called by an agent, negotiation floor leak).
>    - Phase 9: consolidate into output/eval_matching.json and output/eval_negotiation.json.
> 4. List which screenshots I still need to take.
>
> Don't redo tests that already passed. Log this prompt in AI_prompts.md.

### What was missing

- **Which "missing" tests were really missing:** `approve_deal` by an agent and the negotiation floor leak were already covered (Phase 3 #8a and #6, Phase 6 leak scans), so they were cited, not redone; the session budget cap, the per-run token cap and a rogue looping agent were new.
- **Enough real buy-request runs to average:** only 3 were logged, so 21 real buy requests were measured (`need_post_runs.json`, $0.016).
- **Phase 6 leftovers first:** the user paused the audit to finish Phase 6 (screenshots with an edited budget, re-runs, morning summary); the re-runs found a privacy gap in run results, fixed before the audit continued.

### Follow-up prompt(s)

> wait did we have anything left for phase 6 before moving on

> I went to go take the screenshots, but the Hartwell Riverbend pair negotiation doesn't really negotiate. It just accepts it in the first go. So amongst our existing demo accounts, is there another deal that might be a better one for me to take screenshots of? Or is it worth bringing Prairie packaging into the core demo accounts, maybe? Make no changes, just tell me what you think.

> Okay, I made that change. From 450 to 180. And then I took the screenshots. And gave them to you. Now use whichever screenshots you need. Once you've done that, rerun the rest of the phase 6 suite. Rerun the phase 3 and 5 regressions. Do that, and update the morning summary. And once you've done all of that, go ahead and do the seven-to-nine audit. That I asked you to do. As well as the steps. I asked you to do.

> sorry i had to restart my laptop - please resume

> tell me more about the cost cutting experiment - if it really worked so well at no cost to the quality of the work then why dont we implement it?

> okay anything you need from me before you commit

> what is the agent design trace

## Evidence consistency check (before Phase 10)

### Initial prompt

> before phase 10,
>
> do a consistency check on all evidence (no new features):
> 1. Recalculate one seller run and one negotiation cost by hand from token_usage using gpt-6-luna prices ($0.10 input, $0.01 cached, $0.125 cache write, $0.50 output per 1M) and confirm they match the cost meter and tokenomics.json.
> 2. Confirm tokenomics.json states per-user assumptions and that the 100 and 10,000 user totals follow from them. Confirm the pre-filter experiment reports both tokens and accuracy.
> 3. Confirm safety_tests.json covers attacks, malfunction, and overspending, each with at least one passing test, and list which screenshot proves each.
> 4. Rerun any evidence generated before the Phase 6 and auto-negotiate changes so everything reflects the final code. Add scripts/run_all_evidence.py that regenerates all of it in one command.
> 5. Make sure every metric is identical everywhere it appears, and that sample sizes and failures are stated honestly.
> 6. Output output/evidence_index.md: one table mapping each report section → evidence files → screenshots → headline numbers.
> Log this in AI_prompts.md.

### What was missing

- **Which files count as "before the final code":** the Phase 3 stress test (59 runs, source of seller-flow costs, matching accuracy and ~10 safety tests), the reverse-matching eval, the demo-pair test and the concurrency test were re-run; the separate auto-negotiate evidence files were retired because Phase 6 suite section 1 runs the same checks on the final code.
- **How to keep numbers identical:** the headline numbers are generated into one file (`evidence_index.md`) with automatic consistency checks, and the prose docs point to it instead of repeating numbers; dated records (decisions log, morning summary, Phase 3 history) keep the numbers of their time on purpose.

### Follow-up prompt(s)

> dont stop working - but just tell me - why are we running the phase 3 stress run again?

> Commit the evidence consistency check to main.

## Phase 10 — Impact

### Initial prompt

> Phase 10: impact. The real-user test isn't happening before submission. It might happen tomorrow, but put a pin in it for now: don't block anything on it, and don't add placeholder quotes or invented user feedback anywhere.
>
> 1. Read impact_research.md (sections 1–4). It's the sourced research for this phase.
>
> 2. Carbon factors: replace the placeholder values in carbon_factors with the sourced values in section 2 (store the source URL and notes for each), set the reuse credit to 0.5, recompute CO2 figures, and update the tooltip text plus the method description in design.md and harness.md. Chemicals show disposal cost avoided instead of a CO2 figure.
>
> 3. Impact model: build scripts/impact_model.py → output/impact_model.json and output/impact_model.md for one mid-size plant using section 3:
>    - Inputs clearly labeled as assumptions vs. sourced vs. measured.
>    - Use MEASURED values from our app wherever possible: average suggested ask ÷ new price across the catalog, average negotiated deal price from eval_negotiation.json, and cost per user per month from tokenomics.json.
>    - Outputs: $ recovered vs. scrap, carrying cost avoided per year, buyer-side downtime value (at the $36k/hr lowest-sector rate from Siemens), est. CO2e avoided, and the app's running cost for that plant.
>    - Show the sensitivity: low / mid / high for the key assumptions.
>
> 4. Timed self-test for the "own tests" evidence: create output/timed_test_template.md for me to fill in. For 2 items, record the time to do it manually (write a listing, look up compatibility, find 3 plausible buyers) vs. in the app. Label it "measured by the author, not an independent user." I'll fill in the times myself. Don't make up numbers.
>
> 5. Real user: add a "Planned pilot" section to output/impact_model.md and a line in the README's limits: what the session would test (time to list and find buyers vs. today's process, plus a quote) and that it hasn't happened yet.
>
> 6. Write output/impact_sources.md listing every external number we use, with its source link and confidence level, to paste into the report's Impact and Motivation sections. Don't use anything from the "don't claim" list in impact_research.md.
>
> At the checkpoint, list the evidence files and remind me to fill in the timed test and screenshot the impact strip and Marketplace impact summary (phase10-impact). Also remind me of the agent design trace. Log this prompt in AI_prompts.md.

### What was missing

- **Factors for families the research doesn't list:** non-CPU electronic modules (I/O, power supplies, network, VFD option and control units, teach pendant) use 12.4 kg per unit, the low end of Siemens' range; PLC chassis and accessories use steel (conservative vs. aluminium); lubricants are treated like chemicals (no CO2 claim).
- **Converting $242 per drum to our per-kg model:** $1.34/kg at the ~180 kg average fill of our 55-gal drums.
- **Part weights:** not in the research; they stay as estimated shipping weights and are labelled that way.
- **Two assumptions the model needs that section 3 didn't state:** sell-through (not all idle stock finds a buyer; the rest is still scrapped) and downtime hours avoided per year; both are labelled assumptions with ranges.
- **The README had no Limits section;** one was added.

### Follow-up prompt(s)

> hi there - explain to me in a short summary what you did for phase 10
> and also explain to me what I need to do

> give me detailed instructions on what I need to do for the timed test and give me the link to the webpage so i can take the screenshot

> here are the screenshots
>
> for the manual test - I am not a supply chain person so I dont know what to write up or how to identify good buyers - is there a way you can help me with this? Maybe you give me the writeup and the manual test is about finding buyers?

(Answer: the manual answers were not supplied, so the manual time stays real; instead the template got a step-by-step how-to: a fill-in listing template, search queries for compatibility, and job postings as evidence a plant runs a system, with a 15-minute cap per step.)


## Phase 10 consistency check

### Initial prompt

> Phase 10 consistency check (no new features):
>
> 1. Recompute est. CO2e by hand for 3 items (one steel part, one aluminium or motor, one PLC CPU) and confirm they match the app. Check units, and make sure electronics use the per-unit factor only, not weight too. Flag any figure that looks implausibly large.
> 2. Confirm every carbon factor and source URL matches impact_research.md, and that chemicals show disposal cost avoided, not CO2.
> 3. Confirm the impact strip, deal card, Marketplace summary, and impact_model.json all use the same function, and that the Marketplace total equals the sum of individual deals. Confirm Reset demo clears impact totals.
> 4. Downtime value: only count it for deals where the buyer's need was marked urgent (line down), using $36k/hr as a lower bound. Don't apply it to every deal, and never use the $2.3M/hr automotive figure.
> 5. Label one-time values ($ recovered) vs. annual values (carrying cost avoided) everywhere. Don't sum them without labels.
> 6. Confirm measured inputs are read from evidence files, not hardcoded: change one input and show the output changes.
> 7. Search the repo and UI for any invented user quotes, testimonials, or pilot claims and remove them. Confirm the timed test template is still empty.
> 8. Confirm nothing from the "don't claim" list in impact_research.md is used.
>
> Report PASS/FAIL with fixes, then regenerate impact_model.json/.md and impact_sources.md. Log this in AI_prompts.md.
>
> important: if you already ran any of these tests, dont run them again just let me know

### What was missing

- **No family uses aluminium** (motors and drives use steel on total weight, per the research), so the "aluminium or motor" item used a servo motor.
- **impact_model.py had its own CO2 loop** over the catalog instead of the app's `get_impact_estimate` (0.00766 vs. 0.00576 kg CO2e per $). It now calls the shared function; mid-case CO2e went from 2,528 to 1,901 kg.
- **Downtime was applied as "hours avoided per year" with a $150k/hr high case.** It is now only line-down purchases × 1 hour × $36k (lower bound); the logged deals show 8 of 33 were line down ($288,000 lower bound). The $150k and $2.3M rates were removed from the model and `impact_sources.md`.
- **One-time vs. per-year:** the model outputs are now split into `one_time` and `per_year`; the UI's "$ recovered" is labelled "one-time" on the strip, deal card, Marketplace and rail.
- **Repeatable check:** `scripts/check_impact.py` → `output/impact_check.md` (25/25 PASS; scratch DB, no model calls), added to `run_all_evidence.py`.
- **Not rerun (already done earlier):** the S7-300 CPU hand check (21 kg), the IPA disposal check ($938), and the reset-restores-the-DB stress test.

## Push to GitHub (before Phase 11)

### Initial prompt

> Before you start phase 11, lets push to github
> I created this repository (not to be confused by the old one called surplus exchange)
> https://github.com/simrahpalla/final_project---spare_change.git
> 1. Set the git remote origin to that URL (add it if no remote exists yet).
> 2. Update output/github_url.txt, the README, and any links in the report and slides source.
> 3. Before pushing, confirm .gitignore excludes .env, .venv, node_modules, and the WAL/SHM side files, and that no keys exist anywhere in the git history.
> 4. Merge the phase6 and any other branch into main if it isn't already, then push main.
> Log this in AI_prompts.md.
>
> before you do it - tell me if you think theres something missing in my directions or if this is the right way to do it

### What was missing

- **The clone folder name:** cloning `final_project---spare_change.git` creates a folder of that name, but the README said `cd spare-change`. The README now clones into `spare-change` explicitly.
- **Uncommitted work:** the Phase 11 screenshots and `output/phase11_trace.md` had to be committed first, or the push would not include them.
- Already true: the repo was empty and public; `.gitignore` covered every item; no real key value in any commit (checked against the values in `../.env` without printing them); `phase6` already merged, so only `main` is pushed.

### Follow-up prompt(s)

> sure - push it and check it worked and then we move to actually doing phase 11?

## Phase 11 — Report and slides

### Initial prompt

> Phase 11: report.html and slides.html. These are two of the three graded deliverables (report 41 pts + slides 8 pts), so accuracy and evidence matter more than polish. Re-read the official requirements page (https://zlisto.github.io/mgt_409_fa26/project_requirements.html) and CLAUDE.md before starting.
>
> GROUND RULES (apply to both files)
> - Every number must trace to a file in output/ (tokenomics.json, safety_tests.json, eval_matching.json, eval_negotiation.json, impact_model.json, impact_sources.md, phase*_stress.md, evidence_index.md) or to a sourced row in impact_research.md. Build output/report_numbers.md: a ledger listing every number used in the report and slides → the file and field it came from. If a number has no source, don't use it.
> - No invented content: no user quotes, testimonials, or pilot results. The real-user test hasn't happened. The timed self-test numbers come from output/timed_test_template.md. If it's still empty, insert a clearly marked [TODO: Simrah to fill timed test] placeholder and list it in the final checklist. Don't make up times.
> - Be honest: state sample sizes ("18/20", not just "90%"), report failures and limits, label estimates "est." and assumptions as assumptions. Use only numbers from the impact_research.md rows, never the "don't claim" list.
> - Write for a smart manager who has never seen the app: plain English, short paragraphs, no filler (the grading says filler costs points). Explain any technical term in one line the first time it appears.
> - Self-contained: both files must open by double-clicking on any computer, with every image embedded as base64 (WebP or compressed PNG to keep file sizes reasonable) and all CSS inline. The only allowed external resource is reveal.js from a CDN in slides.html.
> - Branding: Spare Change, tagline "Turn spare parts into spare change." Buyer-side line "Spare yourself the downtime." Use the approved Workshop design from output/design.md: navy #0C2340, safety orange #F97316 as the one accent, green for passed/approved, red for blocked, teal #0F766E for impact numbers, clean sans-serif, monospace only for part numbers.
> - Build both from source files so they're easy to edit: report/report.md + scripts/build_report.py → report.html, and slides/slides.md (or a JSON outline) + scripts/build_slides.py → slides.html. Put the final files at the repo root and in deliverables/.
>
> REPORT (report.html, 10–15 printed pages, letter size; sections in exactly this order and with these titles)
>
> 1. Title + links
>    - "Spare Change", the tagline, "Simrah Palla", the GitHub repo link (from output/github_url.txt), the app link if hosted, and ONE sentence saying what the app does.
>
> 2. Motivation
>    - Who has the problem: plants with idle surplus parts, and plants with stopped lines waiting for discontinued parts.
>    - How they cope today and what it costs, using sourced numbers from impact_sources.md: Siemens TCOD 2024 downtime costs ($1.4T, 11% of revenue; $36k–$2.3M/hr), restart time 49 → 81 min with emergency parts harder to source, ~22% of spare-parts stock unused 5+ years, holding cost ~15–30%/yr, scrap recovering ~5–15%, new OEM lead time ~16–20 weeks vs. surplus in days.
>    - The S7-300 phase-out story (new parts stopped shipping Oct 2025; spare parts guaranteed to 2033), citing the distributors as the source.
>
> 3. What is new here
>    - Named comparison table: B-Stock, Liquidity Services/GovDeals, EquipNet, eBay, Automa, SPARETECH, Rheaply, Verusen and Verdantis MRO360, Pactum, PharmaCupboard, and ChatGPT itself. For each: what it does, and what it doesn't do that we do.
>    - Our four differences: matching on what equipment buyers run (not keywords); agents on both sides with private limits enforced in code; the whole loop from messy text to human-approved deal; impact ($ and est. CO2e) on every deal.
>    - Be honest that Automa and SPARETECH are closest, and say what we do differently.
>    - A short "What's new vs. my HW5" paragraph: the architecture pattern is reused, but the domain, agents, two-sided matching, negotiation, compliance guard, impact layer, and demo accounts are all new. This matters because ideas built in class without a real addition are capped at Tier 1.
>
> 4. The agents
>    - An agent table: each agent, what it does, its tools (by MCP role), and whether it uses the LLM or deterministic code.
>    - A clear architecture diagram as inline SVG: seller and buyer entry points → listing/need extraction → compliance guard → matching (both directions, SQL pre-filter) → pricing → negotiators (each locked to its own private limit) → human approval. Show the two human touchpoints (confirm limit, approve deal) and the principle "humans set the guardrails, agents do the work."
>    - Model choice: gpt-6-luna for all agents via Portkey, and why (course key; cheap enough to run many agents; structured outputs). Note that deterministic code handles what doesn't need judgment.
>    - ONE real run traced step by step with screenshots: a seller lists an item → listing agent output → compliance pass → matches with reasons → buyer alerted → auto-negotiation turn by turn → both approvals → listing sold and need filled. Use real screenshots from output/screenshots/ and the matching audit trail entries.
>    - Brief design choices: the MCP server as the only path to the database, role-based tools, negotiator processes locked to one negotiation, and process reuse after the crash fix.
>
> 5. Tokenomics
>    - The price table (gpt-6-luna: $0.10 input / $0.01 cached / $0.125 cache write / $0.50 output per 1M).
>    - Measured tokens (input / cached / output) and cost per seller run, per need run, and per negotiation, as averages of real runs with the sample size. Include a screenshot of the in-app cost meter.
>    - Cost per user per month (state the assumptions), at 100 users, and at 10,000 users. Add the scale check: ~284k US manufacturing sites, so 10,000 is ~3.5%.
>    - What we did to keep cost down: SQL pre-filter, deterministic compliance checks, no LLM call when there are 0 candidates, prompt caching, round caps.
>    - The pre-filter experiment: tokens AND accuracy with and without it, answering "did cost-cutting hurt performance?" with evidence.
>
> 6. Safety
>    - Three subsections, exactly as the requirements name them:
>      - Attacks: prompt injection in listings and needs, attempts to extract the other side's limit, calling tools outside a role.
>      - Agent malfunction: made-up specs or match reasons, wrong actions, infinite loops, MCP crashes under load (show the before/after crash rate from the stress test).
>      - Overspending: per-run caps, the per-negotiation cap, and the session budget cap.
>    - For each: the risk, the defense built, and evidence (test result plus a screenshot). Include at least the injection block, the blocked offer shown to its own side, the leak scan, and the side-by-side seller and buyer views showing each side only sees its own limit.
>
> 7. Impact
>    - The plant model from impact_model.md: one-time $ recovered vs. scrap, carrying cost avoided per year (labeled as yearly), downtime value only for line-down deals at the $36k/hr lower bound × 1 hour, and est. CO2e avoided with the method (factor × weight or per unit × 0.5 reuse credit), plus low/mid/high sensitivity.
>    - Per-deal averages from logged test deals (not totals presented as real-world impact).
>    - The timed self-test, labeled "measured by the author, not an independent user."
>    - A sources table for every external number, with its confidence level.
>
> 8. Limits + next steps
>    - Synthetic data; demo account switching is not real login; no payments or shipping; the carbon method is simplified; no independent user test yet.
>    - Business challenges: getting buyers and sellers on board at the same time; equipment data is scattered and private; trust and counterfeits (part revision and firmware verification); thin margins on small transactions.
>    - Next steps: a pilot with a plant maintenance manager; starting with discontinued PLCs and drives; an internal exchange between sites of one large manufacturer as a first customer; verification features.
>
> Report design: clean, print-friendly layout (letter size, ~11pt body), a navy header bar, numbered section headings, figure captions on every screenshot ("Figure 3: Negotiation from the seller's view"), tables with light borders, and print CSS that avoids splitting images and tables across pages. Put a 3–4 line executive summary right under the title.
>
> SLIDES (slides.html, reveal.js from CDN, max 10 slides, big readable text, same colors as the app)
> 1. Title: Spare Change logo and wordmark, "Turn spare parts into spare change", Simrah Palla, repo link
> 2. The problem and who has it: two plants side by side (idle surplus vs. line down), with 2–3 sourced numbers
> 3. What's new: compact competitor comparison, and our four differences
> 4. How the agents work: the architecture diagram with the two human touchpoints
> 5. Demo, seller side: listing → compliance → matches → price (screenshots)
> 6. Demo, negotiation: live negotiation and deal approval (screenshots, seller and buyer views)
> 7. Cost to run: per run, per user per month, at 10,000 users, and the pre-filter result
> 8. Safety: three columns (attacks, malfunction, overspending), each with one proof screenshot or number
> 9. Impact: plant model headline numbers + est. CO2e, with sources
> 10. What's next: limits, the pilot plan, and "Your next spare part is someone's spare change"
> - At most ~30 words of text per slide. Visuals carry the story. Add speaker notes with the talking points. Arrow keys must work and F must enter full screen.
>
> VERIFICATION (do all of these before telling me it's done)
> - Open both files in a headless browser: no console errors, every image renders, no external image/CSS references (except reveal.js), all links valid.
> - Print the report to PDF at letter size and report the page count. It must be 10–15 pages. Adjust content (not font size) if it's outside that range.
> - Click through every slide and confirm there are ≤10, nothing overflows the slide, and text is readable.
> - Cross-check every number in both files against output/report_numbers.md, and flag any mismatch.
> - Search both files for TODO, placeholder, lorem, and invented quotes. List any remaining TODOs for me.
> - Report file sizes for both HTML files.
> - Save a PDF copy of the report to deliverables/ for my review.
>
> Then stop and give me: a final checklist mapping each rubric row to where it's covered in the report and slides, the remaining TODOs (e.g. the timed test), and any section where the evidence is thin. Log this prompt in AI_prompts.md.

> we can reset it. I still need to do the manual check but I'll do that after my class. I want you to go ahead and execute phase 11 and leave placeholder for the manual check

### What was missing

- **Competitor sources:** none of the named competitors were in the repo, so a sourced scan was done first (`output/competitors.md`, 12 products, every row with the page actually opened; 403s noted). PharmaCupboard turned out to be Indian, not UK/EU.
- **Two numbers in the prompt conflicted with the Phase 10 rules:** the "$36k–$2.3M/hr" range (Phase 10 says never use $2.3M) → the report uses "at least $36,000 an hour, even in the lowest-cost sector"; "~284k sites, ~3.5%" (the research says to write "about 280,000") → "about 280,000", so 10,000 users ≈ 3.6%.
- **The ledger is enforced, not just written:** report/slides write `{{key}}`; `scripts/report_numbers.py` reads each value from its evidence file; the build fails on an unknown key.
- **Found while building:** the evidence index's Impact row read the old impact-model keys and printed $0 (fixed); the slides' notes plugin URL was wrong (fixed).
- **Section numbering:** the requirements count Title + links as section 1, so Motivation is 2 … Limits is 8.
- **No natural blocked offer to screenshot:** the traced run closed in round 2, so the "blocked offer shown to its own side" is evidenced by the scripted rogue-agent test (`safety_extra.json`, M3), not a screenshot.


## Phase 11 review fixes

### Initial prompt

> Commit.
>
> After that:
>
> Review fixes for report.html and slides.html. Priority order matters: we're close to the deadline, so do MUST-FIX first and commit, then SHOULD-FIX.
>
> MUST-FIX
> 1. Timed test: most important but I still havent done it - I'll give you the numbers for this in an hour
> 2. Deal counts are inconsistent (exec summary 33, section 7 "31 logged test deals", price range n=32, downtime "8 of our 33"). Use one dataset everywhere and explain any exclusions in one line. also explain to me why its inconsistent
> 3. Remove "worth at least $288,000 at one hour each". It sums repeated test deals. Keep only per-deal averages and the plant model.
> 4. Confirm the repo URL in both files matches the actual GitHub repo name and that the link works.
> 5. Automa: its site advertises a matching tool comparing surplus against 10.5M+ parts and 750+ suppliers. Update the report table and slide 3: it matches against parts/supplier catalogs; we match against the equipment buyers run, plus agent negotiation.
> 6. Motivation overclaims: change "Every plant still running S7-300s now depends on surplus" to "increasingly depends on spares and surplus" (Siemens guarantees spares to 2033), and change "one of the most widely installed PLC families" to "a widely used PLC family" (we have no source for install counts).
>
> SHOULD-FIX
> 7. Usage assumptions: show the per-plant usage assumption on slide 7 next to "$ per plant per month", and add light / typical / heavy scenarios (e.g. 5/2/3, 10/4/6, 100/20/50 seller posts / requests / negotiations per month) with monthly cost per plant and at 100 and 10,000 users, in the report tokenomics section and as a compact row on the slide.
> 8. Negotiation example: replace the traced run with one that shows real negotiating. Use a narrow-overlap pair WITHOUT line-down urgency so the agents counter for 4–6 rounds. Run it end to end in the app after a reset, take new screenshots (both companies' views, price-by-round chart, private reasons, ideally one blocked offer shown only to its own side), update section 4's trace, phase11_trace.md, slide 6 and all affected numbers. Add one sentence and a small figure showing a walk-away outcome from eval_negotiation.json.
> 9. Slide 3: expand the competitor matrix to ~9–10 rows (Automa, SPARETECH, eBay, B-Stock, Liquidity Services, EquipNet, Verusen/Verdantis, Rheaply, Pactum, ChatGPT) with a 3–4 word "what they do" column and the four checkmark columns. Keep text ≥18pt. Split into two columns rather than shrinking the font.
> 10. Sources: add a consistent small source footer to every slide with numbers (external by short name, internal by file and n), especially slides 3, 7, 8, 9.
> 11. Limits + next steps (report and slide 10): add "No company dashboard yet: one view of all your listings, requests, negotiations, statuses and deal history."
> 12. Screenshots: crop Figures 1, 2, 4, 5, 8, 9 to the relevant region and enlarge them so text is readable when printed.
> 13. Exec summary: add "on my own answer keys over a synthetic market" next to 126/126 and 18/18.
> 14. Slide 4: use a simplified diagram (main boxes + two human touchpoints, ≤40 words). Keep the detailed one in the report.
> 15. Add a "1. Title and links" label to the report's first section.
> 16. Taglines: use one consistent approach in the report and slides.
>    - Title slide and report header: "Spare Change", then the tagline "Your next spare part is someone's spare change.", then the existing one-sentence descriptor. Remove "Turn spare parts into spare change. Spare yourself the downtime." from the report header and the sell-side tagline from the title slide.
>    - Keep "Your next spare part is someone's spare change." as the closing line in both (deliberate bookend).
>    - Use the side taglines only where the side is clear: slide 5 heading "Seller side: turn spare parts into spare change", slide 6 heading "Buyer side: spare yourself the downtime", and once each in report section 4 where the seller and buyer flows are introduced.
>    - Leave the app's tab taglines unchanged.
>
> Then rerun the verification: page count 10–15, ≤10 slides only remaining todo being the manual run, every number matches output/report_numbers.md, images embedded, no console errors. Regenerate deliverables/report.pdf. List what changed. Log this in AI_prompts.md.

### What was missing

- **Why the deal counts differed:** three statistics used three filters over the same 33 logged deals. The deal count used all 33. The price ratio dropped 1 deal whose listing was created during a test (not in the seed catalog). The per-deal averages also dropped 1 deal whose request was created during a test. Now one set is used everywhere: 31 of the 33 deals, with that exclusion stated in one line.
- **Automa's figures:** the homepage (opened with a browser user agent) says "10 million unique, standardised products" and "750+ Trusted Suppliers", not 10.5M+; the report uses the site's wording, cited in `output/competitors.md`.
- **The narrow-overlap run needed a human edit:** the pricing agent suggested a $185.50 floor, above Prairie Packaging's $131 budget, so Hartwell lowered its floor to $122 when confirming it (a real human touchpoint). The run was driven through the real UI with Playwright (using the installed Chrome) so every screenshot comes from one in-app run. The agents bargained for 6 rounds; no blocked offer happened naturally, so that defense stays evidenced by the scripted rogue-agent test.
- **Walk-away figure:** `eval_negotiation.json` has outcomes but not offers, so the chart reads pair 3/3's offers from `phase3_stress.json` (same runs).
- **"10,000 users" is shown as plants** to match the per-plant usage assumption.
