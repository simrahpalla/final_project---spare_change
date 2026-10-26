"""Setup check: finds the .env, makes one gpt-6-luna call, prints tokens and cost.

Run from the repo folder:
    .venv\\Scripts\\python.exe scripts\\check_setup.py

Writes the result (never the key) to output/setup_check.json.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import config  # noqa: E402  (loads .env from the repo folder, then the parent folder)
from llm import make_model, usage_breakdown  # noqa: E402
from pydantic_ai import Agent  # noqa: E402


async def main() -> int:
    print(f"PORTKEY_API_KEY: {'found' if os.getenv('PORTKEY_API_KEY') else 'MISSING'} ({config.env_source()})")
    if not os.getenv("PORTKEY_API_KEY"):
        print("Put PORTKEY_API_KEY in a .env file in this folder or the folder one level above.")
        return 1
    agent = Agent(make_model(), instructions="You are a connectivity check. Reply in five words or fewer.")
    result = await agent.run("Say hello to Spare Change.")
    out = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": config.MODEL_NAME,
        "key_source": config.env_source(),
        "reply": result.output,
        **usage_breakdown(result.usage),
    }
    print(json.dumps(out, indent=2))
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    (config.OUTPUT_DIR / "setup_check.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("OK: model reachable. Saved output/setup_check.json")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
