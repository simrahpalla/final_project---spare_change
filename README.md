# Surplus Exchange

**An AI-agent marketplace for industrial surplus.** A plant pastes a messy description of a spare part it no longer needs. Agents turn it into a clean listing, check it for safety and compliance, find buyers whose installed equipment is compatible with it, suggest a fair price, and negotiate the deal. A human approves every deal.

MGT 409 (AI Foundations for Managers), Yale SOM, final project by Simrah Palla.

> **All data is synthetic.** Manufacturer and platform names (Siemens, Allen-Bradley, ABB, Grundfos, SKF…) are real so the matching is realistic. Every company, listing, need and price is made up.

---

## Run it (about 5 minutes)

You need **Python 3.11+** and the course **`PORTKEY_API_KEY`**. Node is **not** needed: the built dashboard (`frontend/dist`) is committed.

### 1. Get the code

```bash
git clone https://github.com/simrahpalla/surplus-exchange.git
cd surplus-exchange
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

Open **http://localhost:8000**. The header shows `gpt-6-luna · key from …` when the key is found. Click **Test model connection** to make one live call.

---

## How it's built

| Part | What it does |
|---|---|
| `backend/` | FastAPI app. It runs the PydanticAI agents (all on `gpt-6-luna` via Portkey) and serves the dashboard from `frontend/dist`. |
| `mcp_server/` | The only path to the SQLite database. Tools are restricted by role (seller agent, buyer agent, broker, human approver). *(Phase 2)* |
| `frontend/` | React + Vite + TypeScript dashboard. Rebuild with `npm install && npm run build` only if you change it. |
| `data/` | The original `exchange.db` (never modified) and the working copy `exchange_new.db`. *(Phase 1)* |
| `scripts/` | The setup check, seeding, cost reports, safety tests and evals. |
| `output/` | Evidence: the audit trail, token and cost reports, safety test results and screenshots. |

**Safety by design:** only `gpt-6-luna` is used, there are per-run caps on model requests, tokens and tool calls, the audit trail is append-only, all user text is treated as data and never as instructions, and only a human can approve a deal.

### Developing the frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to the backend on :8000
npm run build      # writes frontend/dist, which the backend serves
```
