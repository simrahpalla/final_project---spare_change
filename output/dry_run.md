# Phase 12 dry run: fresh clone, as the teaching staff will run it

Run on 26 Oct 2026 from `C:\grader_test\submissions\` (outside OneDrive and the project), using nothing from the working folder: a new virtual environment, the public GitHub clone, and a `.env` one level **above** the repo with only `PORTKEY_API_KEY` and `OPENAI_API_KEY` (the latter a dummy value; the app doesn't use it).

**Machine:** Windows 11 (10.0.26200), Python 3.14.7, git 2.55. Node was not used (the built dashboard is committed; Node 24.21 is installed but not needed).

## Time to a running app

| Run | Clone (README step 1) | Install (step 3, `pip install -r requirements.txt`) | Key check (step 4) | App ready (step 5) | **Total** |
|---|---|---|---|---|---|
| 1 (commit `4ffee04`) | < 10 s | 4:02 | ~5 s | ~3 s after start | **4:50** |
| 2 (commit `ab40b21`, after fixes) | < 10 s | 4:09 | ~5 s | ~3 s after start | **4:43** |

Both runs: `/api/health` and `check_setup.py` reported `key_source: parent folder`; `gpt-6-luna` replied. Nothing unusual was needed (no special software, versions or paths beyond Python 3.11+ and git).

## Smoke test in the fresh clone (run 2, through the real UI)

| Check | Result |
|---|---|
| Seller listing end to end (Hartwell, pre-filled post): listing, compliance passed, Riverbend Foods ranked first (100), price and private floor; cost meter $0.00114 | PASS |
| Buyer request with alert (Riverbend, pre-filled SM 321 request): matched to Hartwell's listing (96); Hartwell and Riverbend both alerted | PASS |
| Confirm budget → negotiation starts by itself (auto-negotiate) → agreed ($200 × 4) → both companies approve → Marketplace shows 1 closed deal | PASS |
| Injection sample: blocked before any model call; cost meter shows $0.00 / 0 tokens for the run; session total unchanged ($0.00283) | PASS |
| Reset demo: 0 closed deals, 0 negotiations, 0 alerts, no session impact | PASS |
| `report.html` from the clone: 9/9 images, repo link correct, no console errors | PASS |
| `slides.html` from the clone: 10 slides, Arrow Right advances, F enters full screen, images load, repo link correct, no console errors | PASS |

## Issues found and fixed (run 1 → fixed → run 2 clean)

1. **README missed the budget step.** After a buy request, code suggests a private budget that must be confirmed before auto-negotiation starts; the README didn't say so, so following it left the SM 321 sample negotiation in "Ready to start". → README now says to click **Confirm budget** (or start from Negotiations → Ready to start).
2. **Stale README claims:** "with a private max price" (the Buy page no longer has that field) and "a deal after about 5 rounds" (with the code-suggested budget it closed in 2). → Removed; the in-app hint for that sample was updated too (frontend rebuilt).
3. **Demo test cases were scattered in prose.** → Added a "Demo accounts and test cases" table (Hartwell, Riverbend, Summit, Redwood, Tidewater, injection test) with what to click and what to expect.
4. **`.env.example`** listed only `PORTKEY_API_KEY`, with a placeholder value. → Now `PORTKEY_API_KEY=` and `OPENAI_API_KEY=` with no values, noting OpenAI isn't used.
5. **README tagline** was the old one. → "From one plant's shelf to another plant's line."

## Final PASS checklist

| Item | Result |
|---|---|
| Fresh clone of the public repo runs by the README alone in under 10 minutes | **PASS** (4:43) |
| `.env` found one level up; works with only `PORTKEY_API_KEY` / `OPENAI_API_KEY` | **PASS** |
| Seller flow, buyer request + alert, negotiation + both approvals, Reset demo | **PASS** |
| Injection blocked; cost meter updates | **PASS** |
| report.html / slides.html open from the clone, images embedded, arrows and F work | **PASS** |
| No `.env`, keys or secrets in the repo or its history (27 commits scanned for the real key values and key-shaped strings: 0) | **PASS** |
| `.env.example` lists the keys with no values; `.gitignore` covers `.env`, `.venv`, `node_modules`, `data/*.db-wal`, `data/*.db-shm` | **PASS** |
| Repo is public; README has run steps, reset / dataset switching, demo accounts and test cases | **PASS** |
| `output/github_url.txt`, README, report and slides all use `https://github.com/simrahpalla/final_project---spare_change`; GitHub's report.html / slides.html are byte-identical to the final local files | **PASS** |
