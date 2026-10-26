r"""Regenerate ALL the report's evidence on the current code, in one command.

    .venv\Scripts\python.exe scripts\run_all_evidence.py              # everything (~40 min, about $0.30 of model calls)
    .venv\Scripts\python.exe scripts\run_all_evidence.py --no-model   # only the steps that make no model calls
    .venv\Scripts\python.exe scripts\run_all_evidence.py --from cost_report   # resume from a step

Every test runs on its own scratch copy of the database, so the demo data is never touched. Steps run in dependency
order (later steps read earlier outputs). A step that fails is reported and the run continues; the final table and
output/evidence_run.json say what passed. The derived files (tokenomics, safety_tests, eval_*, cost_check,
evidence_index) are rebuilt at the end from whatever the tests produced.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = next((p for p in (REPO / ".venv" / "Scripts" / "python.exe", REPO / ".venv" / "bin" / "python") if p.exists()), Path(sys.executable))

# (name, command, makes model calls, what it produces)
STEPS = [
    ("data_checks", ["scripts/test_data_checks.py"], False, "data checks (mutation cases)"),
    ("data_report", ["scripts/data_report.py", "--brief"], False, "output/data_report.md"),
    ("mcp_smoke", ["scripts/mcp_smoke.py"], False, "output/mcp_smoke.json"),
    ("stress_phase3", ["scripts/stress_phase3.py"], True, "output/phase3_stress.json/.md (59 runs)"),
    ("match_check", ["scripts/test_match_check.py"], False, "output/match_check_test.json"),
    ("eval_reverse", ["scripts/eval_reverse.py"], True, "output/eval_reverse.json"),
    ("two_sided", ["scripts/test_two_sided.py"], True, "output/two_sided_test.json"),
    ("stress_phase5", ["scripts/stress_phase5.py"], True, "output/phase5_stress.json/.md"),
    ("negotiation_suite", ["scripts/test_negotiation.py"], True, "output/negotiation_suite.json, phase6_stress.md"),
    ("demo_pair", ["scripts/test_demo_pair.py"], True, "output/eval_demo_pair.json"),
    ("prefilter_experiment", ["scripts/prefilter_experiment.py"], True, "output/prefilter_experiment.json"),
    ("need_posts", ["scripts/measure_need_posts.py"], True, "output/need_post_runs.json"),
    ("safety_extra", ["scripts/safety_extra.py"], True, "output/safety_extra.json"),
    ("concurrency", ["scripts/concurrency_test.py", "--modes", "backend", "--levels", "6"], True, "output/concurrency_test.json"),
    ("cost_report", ["scripts/cost_report.py"], False, "output/tokenomics.json/.md"),
    ("consolidate", ["scripts/consolidate_evals.py"], False, "output/safety_tests.json, eval_matching.json, eval_negotiation.json"),
    ("cost_check", ["scripts/verify_costs.py"], True, "output/cost_check.json/.md (hand-priced)"),
    ("evidence_index", ["scripts/build_evidence_index.py"], False, "output/evidence_index.md (+ consistency checks)"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-model", action="store_true", help="skip steps that call the model")
    ap.add_argument("--from", dest="start", help="start at this step name")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    names = [s[0] for s in STEPS]
    steps = STEPS[names.index(args.start):] if args.start else STEPS
    log_dir = REPO / "output" / "evidence_logs"
    log_dir.mkdir(exist_ok=True)
    rows, t_all = [], time.time()
    for name, cmd, model, makes in steps:
        if args.no_model and model:
            rows.append({"step": name, "result": "skipped (model)", "seconds": 0, "produces": makes})
            continue
        print(f"--> {name}: {' '.join(cmd)}", flush=True)
        t0 = time.time()
        with open(log_dir / f"{name}.log", "w", encoding="utf-8") as log:
            code = subprocess.run([str(PY), *cmd], cwd=str(REPO), stdout=log, stderr=subprocess.STDOUT).returncode
        tail = (log_dir / f"{name}.log").read_text(encoding="utf-8", errors="replace").strip().splitlines()[-1:] or [""]
        rows.append({"step": name, "result": "PASS" if code == 0 else f"FAIL (exit {code})", "seconds": round(time.time() - t0),
                     "produces": makes, "last_line": tail[0][:200]})
        print(f"    {rows[-1]['result']} in {rows[-1]['seconds']} s · {tail[0][:140]}", flush=True)
    (REPO / "output" / "evidence_run.json").write_text(json.dumps({
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "minutes": round((time.time() - t_all) / 60, 1),
        "steps": rows, "logs": "output/evidence_logs/<step>.log"}, indent=2), encoding="utf-8")
    print("\n| Step | Result | Seconds | Produces |\n|---|---|---|---|")
    for r in rows:
        print(f"| {r['step']} | {r['result']} | {r['seconds']} | {r['produces']} |")
    return 0 if all(r["result"] in ("PASS", "skipped (model)") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
