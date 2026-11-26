#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests/golden/hil_replay_summary.json"

def main():
    expected = json.loads(GOLDEN.read_text())
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        hil = td/"hil.csv"; rep = td/"rep.json"
        env = dict(**__import__("os").environ)
        env["PYTHONPATH"] = str(ROOT)
        subprocess.check_call([sys.executable, "ml/hil_simulator.py", "--nights","1","--step-s","600","--seed","7"], cwd=ROOT, stdout=hil.open("w"), env=env)
        subprocess.check_call([sys.executable, "ml/replay.py", "--data", str(hil), "--out", str(rep)], cwd=ROOT, env=env)
        actual = {
            "hil_csv_sha256": hashlib.sha256(hil.read_bytes()).hexdigest(),
            **(({k:v for k,v in json.loads(rep.read_text()).items() if k in ("rows","fault_count")})),
            "first_decision": json.loads(rep.read_text())["events"][0]["decision"],
            "last_decision": json.loads(rep.read_text())["events"][-1]["decision"],
        }
    if actual != expected:
        print("GOLDEN MISMATCH")
        print("expected:", json.dumps(expected, indent=2))
        print("actual:", json.dumps(actual, indent=2))
        return 1
    print("OK golden baseline")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
