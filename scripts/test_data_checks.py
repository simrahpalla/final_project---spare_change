r"""Mutation test for scripts/data_report.py: proves the data checks can actually fail.

    .venv\Scripts\python.exe scripts\test_data_checks.py

Each case plants one problem in a scratch copy of the database (or the answer keys) and confirms
the check that should catch it fails. The real data files are never touched.
"""

import copy
import json
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import data_report as dr  # noqa: E402

KEYS = json.loads((REPO / "data" / "answer_keys.json").read_text(encoding="utf-8"))


def failing(db: Path, keys: dict, sql: str | None = None) -> set[str]:
    shutil.copyfile(REPO / "data" / "exchange.db", db)
    os.chmod(db, stat.S_IWRITE | stat.S_IREAD)
    if sql:
        con = sqlite3.connect(db)
        con.executescript(sql)
        con.commit()
        con.close()
    x = dr.Exchange(db)
    try:
        # check 9 rebuilds the real DB from the seed; it does not depend on the scratch copy
        return {c["name"].split(".")[0] for c in dr.run_checks(x, keys) if not c["passed"]} - {"9"}
    finally:
        x.con.close()


def mutate_keys(fn) -> dict:
    k = copy.deepcopy(KEYS)
    fn(k)
    return k


CASES = [
    ("unchanged data", KEYS, None, set()),
    ("answer key: wrong qty for listing 1", mutate_keys(lambda k: k["listings"][0]["expected"].update(qty=99)), None, {"11"}),
    ("answer key: wrong deal outcome for a pair", mutate_keys(lambda k: k["negotiation_pairs"][0].update(deal_expected=False)), None, {"11"}),
    ("seller floor leaked into listing text", KEYS, "UPDATE listings SET raw_text = raw_text || ' floor is 905' WHERE id=1", {"8"}),
    ("walk-away ceilings raised above floors", KEYS, "UPDATE buyer_private SET ceiling_price=5000 WHERE need_id IN (3,9,11)", {"5", "11"}),
    ("clean listing priced far above new", KEYS, "UPDATE listings SET asking_price=99999 WHERE id=10", {"4", "7", "11"}),
    ("S7-300 installed at 13 more plants", KEYS, "INSERT INTO installed_equipment (company_id,platform,qty,years_in_use) "
     "SELECT id,'Siemens S7-300',1,1 FROM companies WHERE id BETWEEN 38 AND 50", {"1", "11"}),
    ("injection text removed from listing 22", KEYS, "UPDATE listings SET raw_text='50x SKF 6207 bearings, new.' WHERE id=22", {"7"}),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    passed = 0
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "scratch.db"
        for label, keys, sql, expected in CASES:
            got = failing(db, keys, sql)
            ok = expected <= got if expected else not got
            passed += ok
            print(f"[{'PASS' if ok else 'FAIL'}] {label:<42} expected failing {sorted(expected) or 'none'}, got {sorted(got) or 'none'}")
    print(f"\n{passed}/{len(CASES)} mutation cases behave as expected.")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
