"""Append-only audit trail for every agent-loop step, written to output/audit_trail.json.

The file is one JSON array. Each append happens under a cross-process file lock plus a
thread lock, re-reads the current array, adds the entry, and atomically replaces the file,
so concurrent writers never lose entries and a crash can't leave half-written JSON.
Secrets (the Portkey key, key-shaped strings) are scrubbed and long values truncated.
"""

import atexit
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from filelock import FileLock

from config import AUDIT_PATH
from models import AuditEntry

MAX_TEXT = 300
SENSITIVE_KEYS = re.compile(r"api[_-]?key|secret|password|authorization|(^|_)token$", re.I)  # not "input_tokens" counts
SECRET_PATTERNS = [
    re.compile(r"\b(sk|pk)-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bBearer\s+\S+", re.I),
]

_thread_lock = threading.Lock()
_file_lock = FileLock(str(AUDIT_PATH) + ".lock", timeout=30)


def scrub(text: str, limit: int = MAX_TEXT) -> str:
    key = os.getenv("PORTKEY_API_KEY")
    if key:
        text = text.replace(key, "[REDACTED]")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def sanitize(value, key: str = ""):
    if key and SENSITIVE_KEYS.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: sanitize(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        return scrub(value)
    return value


# Entries that could not be written yet (e.g. Windows/OneDrive briefly locking the file).
# They stay queued in memory and are written, in order, with the next successful append.
_backlog: list[dict] = []
REPLACE_ATTEMPTS = 12  # about 4 seconds of retries in total


def _replace_with_retry(src: Path, dst: Path) -> None:
    """os.replace, retried briefly: on Windows it fails while another process (OneDrive sync,
    an editor, antivirus) has the target open for a moment."""
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


def append(entry: AuditEntry) -> None:
    """Append one entry. Never raises: a failed write must not crash the agent run that logged it."""
    record = entry.model_dump(exclude_none=True)
    with _thread_lock, _file_lock:
        _backlog.append(record)
        try:
            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            entries: list = []
            if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size:
                try:
                    entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
                    if not isinstance(entries, list):
                        raise ValueError("audit trail is not a JSON array")
                except ValueError:
                    # Never silently wipe history: set the unreadable file aside and start a new array.
                    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.corrupt-{stamp}.json"))
                    entries = []
            entries.extend(_backlog)
            tmp = AUDIT_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
            _replace_with_retry(tmp, AUDIT_PATH)
            _backlog.clear()
        except OSError as e:
            print(f"[audit] could not write {AUDIT_PATH.name} yet ({e}); "
                  f"{len(_backlog)} entr{'y' if len(_backlog) == 1 else 'ies'} queued for the next write", file=sys.stderr)


@atexit.register
def _flush_backlog() -> None:
    if _backlog:
        last = _backlog.pop()
        append(AuditEntry(**last))


def read_entries() -> list[dict]:
    """Read the whole audit trail under the same locks writers use (safe while agents are writing)."""
    with _thread_lock, _file_lock:
        if not AUDIT_PATH.exists() or not AUDIT_PATH.stat().st_size:
            return []
        entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    return entries if isinstance(entries, list) else []


def log(run_id: str, agent: str, action: str, *, subject: str | None = None, depth: int = 0,
        step: int | None = None, args: dict | None = None, result=None, error: str | None = None,
        **fields) -> None:
    """Build, sanitize and append one audit entry."""
    append(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        run_id=run_id,
        subject=subject,
        agent=agent,
        depth=depth,
        step=step,
        action=action,
        args=sanitize(args) if args is not None else None,
        result=scrub(result if isinstance(result, str) else json.dumps(result, default=str)) if result is not None else None,
        error=scrub(error) if error else None,
        **fields,
    ))
