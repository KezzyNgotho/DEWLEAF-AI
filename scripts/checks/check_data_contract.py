#!/usr/bin/env python3
from __future__ import annotations
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TELEM_REQUIRED = {"timestamp_ms","iso_time","night_id","state","action_id","air_temp_c","rh_pct","dew_point_c","wh_total","flow_l_total","flow_l_window"}

def check_csv(path, required):
    with path.open() as f:
        r = csv.DictReader(f)
        cols = set(r.fieldnames or [])
        missing = required - cols
        if missing:
            print(f"FAIL {path}: missing {sorted(missing)}")
            return False
        for i, row in enumerate(r, 1):
            if i > 200: break
            if not row.get("night_id"):
                print(f"FAIL {path}: empty night_id row {i}"); return False
    print(f"OK {path}")
    return True

def main():
    ok = True
    sim = ROOT/'logs/sim_bench_14night.csv'
    if sim.exists(): ok &= check_csv(sim, TELEM_REQUIRED)
    for p in [ROOT/'ml/artifacts/bench_sim_report.json', ROOT/'ml/artifacts/kenya_v2_full_report.json']:
        if p.exists():
            d=json.loads(p.read_text())
            for k in ["n_rows","n_nights","mean_improvement_pct","target_met_15pct","folds"]:
                if k not in d: print(f"FAIL {p}: missing {k}"); ok=False
            if p.exists() and ok: print(f"OK {p}")
    return 0 if ok else 1

if __name__=='__main__': raise SystemExit(main())
