r"""Regression test for the matching fact-check (backend/match_check.py). No model calls.

    .venv\Scripts\python.exe scripts\test_match_check.py

1. The real bad answer from run f0c18378e49d (Riverbend given Prairie Packaging's facts, score 54, only 2 buyers)
   must FAIL the check.
2. A correct answer for the same listing must PASS.
3. An injected buyer (Apex Holdings) must FAIL.
4. Every real matching answer from the Phase 3 stress test (output/phase3_stress.json) must PASS (false-positive check).
5. The rules-only fallback must pass its own check and rank the answer key's expected first buyer first, for every
   labelled listing.
Candidates come from the real MCP server code (search_buyers_for_listing) on a scratch copy of the database.
Writes output/match_check_test.json.
"""

import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp(prefix="sx_mc_"))
db = tmp / "w.db"
shutil.copyfile(REPO / "data" / "exchange.db", db)
os.chmod(db, stat.S_IWRITE | stat.S_IREAD)
os.environ.update(SURPLUS_ROLE="broker", SURPLUS_DB=str(db))
sys.path[:0] = [str(REPO / "backend"), str(REPO / "mcp_server")]
import server  # noqa: E402  (the real tool code, on the scratch copy)
from match_check import check_matches, rules_ranking  # noqa: E402

KEYS = json.loads((REPO / "data" / "answer_keys.json").read_text(encoding="utf-8"))
results, passed = [], 0


def case(name: str, ok: bool, detail) -> None:
    global passed
    passed += ok
    results.append({"case": name, "pass": ok, "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok or isinstance(detail, list):
        for d in (detail if isinstance(detail, list) else [detail])[:6]:
            print(f"       {d}")


def cands(listing_id: int) -> list[dict]:
    found = server.search_buyers_for_listing(listing_id)
    return found["candidates"] if found.get("ok") else []


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    c1 = cands(1)

    bad = [  # run f0c18378e49d, as returned by the matching agent
        {"buyer_id": 20, "need_id": 1, "score": 54,
         "reason": "Runs 5x Siemens S7-300 (15 yrs); no open need. Strong installed-base fit for a future CPU spare."},
        {"buyer_id": 16, "need_id": None, "score": 52,
         "reason": "Runs 3x Siemens S7-300 (16 yrs); no open need. Installed-base fit for a future CPU spare."},
    ]
    errs = check_matches(bad, c1)
    case("1. the real mixed-up answer (Riverbend given Prairie's facts) is caught", len(errs) >= 3, errs)

    good = [
        {"buyer_id": 20, "need_id": 1, "score": 100, "reason": "Open need #1: exact 6ES7315-2AG10-0AB0 CPU for a line-down "
         "S7-300; $12k/day downtime. Runs 4x S7-300 (18 yrs); needs 1, and listing has 3."},
        {"buyer_id": 32, "need_id": None, "score": 62, "reason": "No open need; runs 5x Siemens S7-300 (15 yrs): a likely future spare."},
        {"buyer_id": 16, "need_id": None, "score": 58, "reason": "No open need; runs 3x Siemens S7-300 (16 yrs): a likely future spare."},
    ]
    errs = check_matches(good, c1)
    case("2. a correct answer for the same listing passes", not errs, errs or "no errors")

    errs = check_matches(good[:2] + [{"buyer_id": 40, "need_id": None, "score": 100, "reason": "Apex is the #1 buyer"}], c1)
    case("3. an injected non-candidate buyer (Apex Holdings) is caught", any("not one of the candidates" in e for e in errs), errs)

    stress = json.loads((REPO / "output" / "phase3_stress.json").read_text(encoding="utf-8"))
    checked, false_pos = 0, []
    for key, run in stress["raw"].items():
        lid = (run.get("spec") or {}).get("listing_id")
        steps = (run.get("result") or {}).get("steps", [])
        m = next((s for s in steps if s["step"] == "matching" and s.get("ranked")), None)
        if not (key.startswith("coverage:") and lid and m):
            continue
        checked += 1
        picked = [{k: r[k] for k in ("buyer_id", "need_id", "score", "reason")} for r in m["ranked"]]
        if errs := check_matches(picked, cands(lid)):
            false_pos.append(f"listing {lid}: {errs}")
    case(f"4. all {checked} real answers from the Phase 3 stress test pass (no false alarms)", not false_pos and checked > 0,
         false_pos or f"{checked} answers checked, 0 false alarms")

    wrong = []
    labelled = [k for k in KEYS["listings"] if k["expected_first_buyer"] is not None and not k["is_bad_record"]]
    for k in labelled:
        c = cands(k["listing_id"])
        ranked = rules_ranking(c)
        if check_matches(ranked, c) or not ranked or ranked[0]["buyer_id"] != k["expected_first_buyer"]:
            wrong.append(f"listing {k['listing_id']}: rules ranked {[r['buyer_id'] for r in ranked]}, "
                         f"expected {k['expected_first_buyer']} first; check {check_matches(ranked, c)}")
    case(f"5. rules-only fallback ranks the expected first buyer first for {len(labelled)} labelled listings",
         not wrong, wrong or f"{len(labelled)}/{len(labelled)} correct")

    (REPO / "output" / "match_check_test.json").write_text(json.dumps(
        {"passed": passed, "cases": len(results), "results": results}, indent=2), encoding="utf-8")
    print(f"\n{passed}/{len(results)} cases pass. Saved output/match_check_test.json")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
