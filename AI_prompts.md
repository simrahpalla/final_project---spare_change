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
