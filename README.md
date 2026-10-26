# Spare Change

> **From one plant's shelf to another plant's line.**

**An AI-agent marketplace for industrial surplus.** A plant pastes a messy description of a spare part it no longer needs. Agents turn it into a clean listing, check it for safety and compliance, find buyers whose installed equipment is compatible with it, suggest a fair price, and negotiate the deal. A human approves every deal.

MGT 409 (AI Foundations for Managers), Yale SOM, final project by Simrah Palla.

> **All data is synthetic.** Manufacturer and platform names (Siemens, Allen-Bradley, ABB, Grundfos, SKF…) are real so the matching is realistic. Every company, listing, need and price is made up.

---

## Run it (about 5 minutes, most of it installing packages)

You need **Python 3.11+** (tested on 3.14) and the course **`PORTKEY_API_KEY`**. Node is **not** needed: the built dashboard (`frontend/dist`) is committed.

### 1. Get the code

```bash
git clone https://github.com/simrahpalla/final_project---spare_change.git spare-change
cd spare-change
```

The last word of the clone command names the folder `spare-change`, so the commands below work as written.

### 2. Put your key in a `.env` file

The app looks for `.env` in **this repo folder first**, then in **the folder one level above**. Either location works:

```
PORTKEY_API_KEY=your-key-here
```

Only `PORTKEY_API_KEY` is used (all agents call `gpt-6-luna` through Portkey); an `OPENAI_API_KEY` line in the same file is fine and ignored. See `.env.example` for the optional run caps. Never commit `.env`.

### 3. Install

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 4. Check the key and model (optional, about 5 seconds)

```bash
.venv/Scripts/python.exe scripts/check_setup.py     # macOS/Linux: .venv/bin/python scripts/check_setup.py
```

It prints where the key was found (`repo folder` or `parent folder`), a one-line reply from `gpt-6-luna`, and the tokens and cost of that call.

### 5. Start the app (one command)

```bash
.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --port 8000     # macOS/Linux: .venv/bin/python -m ...
```

Open **http://localhost:8000**. For the first few seconds a banner says **"Starting up… loading marketplace tools"**: the backend starts its tool servers once, in the background, and every request reuses them afterwards. When the banner disappears and **Find buyers** is enabled, click **Find buyers**: the box is already filled in with the demo seller's post. Then try the other examples under **Try:** (each one signs in as the company that would post it), for example **Expired solvent** or **Injection test**, to see the safety checks block a listing. The right rail shows each agent working, the cost of the run, and the impact. Use the **account switcher** in the top bar (a demo stand-in for logging in): five featured demo accounts, sellers and buyers, each with a one-line "what to try", plus all 50 companies under "Show all companies". Each account sees its own posts and alerts.

**Two-sided matching (Phase 5).** Buyers post what they need on **Buy**: switch to **Riverbend Foods** or **Tidewater Dairy** (their sample request is pre-filled) and click **Find**. Code then suggests a private budget for the request; click **Confirm budget** (only your agent ever sees it). The same compliance guard, SQL pre-filter and matching agent run in reverse, and code sends alerts (score 70+, top 3, never twice) to both sides. To see an alert arrive, run the **Siemens PLC** example as Hartwell on Sell, then switch to Riverbend and open the bell. **Marketplace** shows everything available and wanted side by side, with match badges; click an item to see what it matches. A buyer's max price never appears in alerts, on the Marketplace, or in any seller view. **Reset demo** in the top bar restores the seeded data, so every grader starts clean.

**Negotiation (Phase 6).** You confirm your private limit once (the pricing agent suggests a floor when you list; a budget is suggested when you post a request; only your agent sees it). With **Auto-negotiate my matches** on (default for the demo accounts), a strong match then starts a negotiation by itself; otherwise start one from **Ready to start**, a match alert in the bell, or a match on Sell/Buy. Two agents then negotiate turn by turn within code-enforced limits; you see your own limit, your own agent's private reasons and any move the rules blocked, never the other side's. A deal closes only when **both** companies approve it (switch accounts to approve the other side). Sample negotiations: Hartwell ↔ Riverbend on the SM 321 input cards (both demo accounts: post Riverbend's sample request on Buy and confirm its budget, and the negotiation starts by itself; or start it as Riverbend from **Negotiations → Ready to start**), Hartwell → Riverbend on the S7-300 CPU (quick deal), Hartwell → Prairie Packaging (narrow), Summit → Ironclad (clear), Redwood → Coastal Electronics (narrow), **Cascade Paper & Board** → Northwoods Pulp (walk-away). Three negotiations run at once; more wait as **Queued**.

### Demo accounts and test cases

| Account (switcher) | Role | Try this | You should see |
|---|---|---|---|
| **Hartwell Precision Components** | Seller | **Sell → Find buyers** (post pre-filled) | Listing, compliance passed, Riverbend Foods ranked first (line down), suggested price and private floor |
| **Riverbend Foods** | Buyer, line down | **Buy → Find**, then **Confirm budget**; open the bell after Hartwell's run | A ranked match to Hartwell's SM 321 cards; alerts for Hartwell's listings; then a negotiation to approve on **Negotiations** (approve as Hartwell too) |
| **Summit Automation Surplus** | Seller, distributor | **Sell → Find buyers** | Ironclad Castings matched: the EN2T replaces its discontinued ENBT |
| **Redwood Coatings** | Seller | **Sell → Find buyers** | Blocked by code: the solvent is expired (no model call) |
| **Tidewater Dairy** | Buyer | **Buy → Find** | No surplus yet: the matching agent is skipped (no model call) |
| any account | Safety | **Sell → Try: Injection test → Find buyers** | Blocked before any AI reads it: $0.00 and 0 tokens on the cost meter |

**Reset demo** (top bar) restores the seeded data at any time.

> **Account switching is a demo, not real authentication.** There are no passwords: anyone can pick any company. It shows what each company would see, and the server only ever returns an account's own alerts and private terms, but a real deployment would need sign-in (see Limits in the report).

---

## Try the agents from the command line

```bash
.venv/Scripts/python.exe backend/run_flow.py --listing 1          # seller flow: listing -> compliance -> matches -> price -> outreach
.venv/Scripts/python.exe backend/run_flow.py --listing 22         # planted prompt injection: blocked before any model call
.venv/Scripts/python.exe backend/run_flow.py --text "2 grundfos CR15 seal kits HQQE, never installed, 330 ea" --seller 7
.venv/Scripts/python.exe backend/run_flow.py --negotiate 1 1      # seller agent vs buyer agent -> deal pending human approval
```

Buyer side (a buy request, matched in reverse):

```bash
.venv/Scripts/python.exe backend/run_flow.py --need "Need 4x S7-300 32-point digital input cards (SM 321), quick please" --buyer 20 --max 180
```

Each run prints every step with its tokens and cost (a full run costs well under $0.01) and is saved to `output/runs/`. Add `--reset` to start from a clean database.

## Evidence (tests, costs, safety)

Every number in the report comes from files in `output/`; **`output/evidence_index.md`** maps each report section to its evidence files, screenshots and headline numbers, with consistency checks. To regenerate all of it on the current code (scratch databases only; about 40 minutes and about $0.30 of model calls):

```bash
.venv/Scripts/python.exe scripts/run_all_evidence.py
```

Add `--no-model` to rebuild only the derived files (tokenomics, safety and eval summaries, the index) without calling the model.

## Report and slides

`report.html` and `slides.html` (repo root, copies in `deliverables/`) open by double-clicking; every image is embedded (slides load reveal.js from a CDN). They are built from `report/report.md` and `slides/slides.md`; every number in them is a key filled from the evidence files, listed with its source in `output/report_numbers.md`. To rebuild (needs Pillow for image compression: `pip install pillow`):

```bash
.venv/Scripts/python.exe scripts/build_report.py
```

```bash
.venv/Scripts/python.exe scripts/build_slides.py
```

## Limits

- **No real user has tried it yet.** A pilot with a plant maintenance manager is planned but hasn't happened: it would time listing a part and finding buyers against their current process and collect a short quote.
- **Synthetic data:** real part numbers, platforms and list prices; made-up companies, listings, requests and limits.
- **Impact numbers are estimates:** sourced carbon factors × a conservative 0.5 reuse credit on estimated shipping weights (no CO2 claim for chemicals); the plant-level impact model is illustrative, with every assumption labelled (`output/impact_model.md`).
- **Account switching is a demo, not authentication** (see above).

## How it's built

| Part | What it does |
|---|---|
| `backend/` | FastAPI app. It runs the PydanticAI agents (all on `gpt-6-luna` via Portkey) and serves the dashboard from `frontend/dist`. |
| `mcp_server/` | The only path to the SQLite database. Tools are restricted by role (broker, seller agent, buyer agent, human approver, system); see `mcp_server/README.md`. Smoke test: `scripts/mcp_smoke.py`. |
| `frontend/` | React + Vite + TypeScript dashboard. Rebuild with `npm install && npm run build` only if you change it. |
| `data/` | The original `exchange.db` (never modified), the working copy `exchange_new.db`, and `answer_keys.json`. Both databases are committed, so no setup step is needed. |
| `scripts/` | The setup check, seeding, cost reports, safety tests and evals. |
| `output/` | Evidence: the audit trail, token and cost reports, safety test results and screenshots. |

**Safety by design:** only `gpt-6-luna` is used, there are per-run caps on model requests, tokens and tool calls, the audit trail is append-only, all user text is treated as data and never as instructions, and only a human can approve a deal.

### The data

**The data is synthetic.** Part numbers, manufacturers and machine platforms are real. Every company, listing, buyer need and price is made up. There is one small test dataset (128 KB): 50 companies, 62 catalog parts, 27 listings (6 of them deliberately bad, for the safety tests) and 21 buyer needs. It is already built and committed in `data/`, so you don't need to run anything to use it.

- `data/exchange.db` is the original. It is read-only and the app never changes it.
- `data/exchange_new.db` is the working copy the app writes to.

**Reset** the working copy to a clean state at any time. This discards matches, negotiations and deals made while using the app:

```bash
.venv/Scripts/python.exe scripts/reset_db.py
```

Other data commands (optional):

```bash
.venv/Scripts/python.exe scripts/seed_data.py      # rebuild everything from scratch (identical result: fixed random seed)
.venv/Scripts/python.exe scripts/data_report.py    # 11 data-quality checks -> output/data_report.md
```

To run against a different database, set `SURPLUS_DB=path/to/working_copy.db` in `.env`. The tables, the answer keys (`data/answer_keys.json`) and the designed test cases are described in `output/harness.md`.

### Developing the frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to the backend on :8000
npm run build      # writes frontend/dist, which the backend serves
```
