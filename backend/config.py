"""Paths, model settings and run limits for Surplus Exchange.

Limits can be overridden with environment variables in .env (see .env.example).
"""

import os
import sys
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent
REPO_DIR = BACKEND_DIR.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"
OUTPUT_DIR = REPO_DIR / "output"
FRONTEND_DIST = REPO_DIR / "frontend" / "dist"
# SURPLUS_AUDIT / SURPLUS_DB are optional overrides for isolated tests.
AUDIT_PATH = Path(os.getenv("SURPLUS_AUDIT") or OUTPUT_DIR / "audit_trail.json")

DATA_DIR = REPO_DIR / "data"
ORIGINAL_DB = DATA_DIR / "exchange.db"
WORKING_DB = Path(os.getenv("SURPLUS_DB") or DATA_DIR / "exchange_new.db")

# The MCP server is the only path to the database. The backend launches it over stdio.
MCP_SERVER = REPO_DIR / "mcp_server" / "server.py"


def _mcp_python() -> Path:
    """Python used to launch the MCP server: an explicit override, else the repo .venv, else this interpreter."""
    if override := os.getenv("SURPLUS_MCP_PYTHON"):
        return Path(override)
    for exe in ("Scripts/python.exe", "bin/python"):
        if (REPO_DIR / ".venv" / exe).exists():
            return REPO_DIR / ".venv" / exe
    return Path(sys.executable)


MCP_PYTHON = _mcp_python()

# .env lookup: the repo folder first, then the folder one level above (where the teaching
# staff put theirs). For each key, the first file that defines it wins, and a .env value
# overrides any variable already set in the system environment.
ENV_CANDIDATES = (("repo folder", REPO_DIR / ".env"), ("parent folder", REPO_DIR.parent / ".env"))
_KEY_SOURCE = "system environment" if os.getenv("PORTKEY_API_KEY") else "not found"
_loaded: set[str] = set()
for _label, _env_file in ENV_CANDIDATES:
    if not _env_file.exists():
        continue
    for _key, _value in dotenv_values(_env_file).items():
        if _value and _key not in _loaded:
            os.environ[_key] = _value
            _loaded.add(_key)
            if _key == "PORTKEY_API_KEY":
                _KEY_SOURCE = _label


def env_source() -> str:
    """Where PORTKEY_API_KEY came from (for the startup check; never the key itself)."""
    return _KEY_SOURCE


# Every agent uses exactly this model through Portkey. No alternatives or fallbacks.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# gpt-6-luna list prices, USD per 1M tokens (course price table). Used to turn token counts into cost.
PRICE_INPUT_PER_M = 0.10
PRICE_CACHED_INPUT_PER_M = 0.01
PRICE_CACHE_WRITE_PER_M = 0.125
PRICE_OUTPUT_PER_M = 0.50


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value and value.strip().isdigit() else default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, ""))
    except ValueError:
        return default


# Limits for one run (a seller flow, a need flow or a negotiation, all agents combined).
MAX_MODEL_REQUESTS = _int_env("MAX_MODEL_REQUESTS", 30)  # model calls per run
MAX_TOKENS_PER_RUN = _int_env("MAX_TOKENS_PER_RUN", 150_000)  # input + output tokens per run
MAX_TOOL_CALLS = _int_env("MAX_TOOL_CALLS", 40)  # MCP tool calls per run
MAX_NEGOTIATION_ROUNDS = _int_env("MAX_NEGOTIATION_ROUNDS", 6)  # offers per negotiation, enforced in code
SESSION_BUDGET_USD = _float_env("SESSION_BUDGET_USD", 2.00)  # total spend before the backend refuses new runs
