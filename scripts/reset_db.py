"""Reset the working database from the original (the original is never modified).

    .venv\\Scripts\\python.exe scripts\\reset_db.py

Copies data/exchange.db over data/exchange_new.db. Every match, negotiation, deal, notification
and token_usage row written by the app is discarded. The audit trail (output/audit_trail.json)
is kept, because it is append-only.
"""

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ORIGINAL_DB = REPO / "data" / "exchange.db"
WORKING_DB = REPO / "data" / "exchange_new.db"


def reset(original: Path = ORIGINAL_DB, working: Path = WORKING_DB) -> Path:
    """Copy the original over the working copy. Refuses to copy a file onto itself."""
    if not original.exists():
        raise FileNotFoundError(f"{original} not found. Run scripts/seed_data.py first.")
    if working.resolve() == original.resolve():
        raise ValueError("The working copy must be a different file from the original.")
    shutil.copyfile(original, working)  # copies contents only, so the working copy stays writable
    return working


if __name__ == "__main__":
    out = reset()
    print(f"Reset {out.relative_to(REPO)} from {ORIGINAL_DB.relative_to(REPO)}.")
    sys.exit(0)
