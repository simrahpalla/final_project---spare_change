# Spare Change

> **Turn spare parts into spare change.**

**An AI-agent marketplace for industrial surplus.** A plant pastes a messy description of a spare part it no longer needs. Agents turn it into a clean listing, check it for safety and compliance, find buyers whose installed equipment is compatible with it, suggest a fair price, and negotiate the deal. A human approves every deal.

MGT 409 (AI Foundations for Managers), Yale SOM, final project by Simrah Palla.

> **All data is synthetic.** Manufacturer and platform names (Siemens, Allen-Bradley, ABB, Grundfos, SKF…) are real so the matching is realistic. Every company, listing, need and price is made up.

---

## Run it (about 5 minutes)

You need **Python 3.11+** and the course **`PORTKEY_API_KEY`**. Node is **not** needed: the built dashboard (`frontend/dist`) is committed.

### 1. Get the code

```bash
git clone https://github.com/simrahpalla/spare-change.git
cd spare-change
```

### 2. Put your key in a `.env` file

The app looks for `.env` in **this repo folder first**, then in **the folder one level above**. Either location works:

```
PORTKEY_API_KEY=your-key-here
```

See `.env.example` for the optional run caps. Never commit `.env`.

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

Open **http://localhost:8000**. For the first few seconds a banner says **"Starting up… loading marketplace tools"**: the backend starts its tool servers once, in the background, and every request reuses them afterwards. When the banner disappears and **Find buyers** is enabled, click **Find buyers**: the box is already filled in with the demo seller's post. Then try the other examples under **Try:** (each one signs in as the company that would post it), for example **Expired solvent** or **Injection test**, to see the safety checks block a listing. The right rail shows each agent working, the cost of the run, and the impact. Use the **account switcher** in the top bar (a demo stand-in for logging in): five featured demo accounts, sellers and buyers, each with a one-line "what to try", plus all 50 companies under "Show all companies". Each account sees its own posts and alerts. **Reset demo data** in that menu restores the database.

---

## Try the agents from the command line

```bash
.venv/Scripts/python.exe backend/run_flow.py --listing 1          # seller flow: listing -> compliance -> matches -> price -> outreach
.venv/Scripts/python.exe backend/run_flow.py --listing 22         # planted prompt injection: blocked before any model call
.venv/Scripts/python.exe backend/run_flow.py --text "2 grundfos CR15 seal kits HQQE, never installed, 330 ea" --seller 7
.venv/Scripts/python.exe backend/run_flow.py --negotiate 1 1      # seller agent vs buyer agent -> deal pending human approval
```

Each run prints every step with its tokens and cost (a full run costs well under $0.01) and is saved to `output/runs/`. Add `--reset` to start from a clean database.

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
