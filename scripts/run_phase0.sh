#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "== DewLeaf Phase 0 =="
echo "[1/5] Python checks"
python3 -m py_compile logger/dewleaf_logger.py ml/*.py
echo "[2/5] Simulate 14-night bench (contract test)"
python3 ml/simulate_bench_run.py --out logs/sim_bench_14night.csv --nights 14 --seed 11
echo "[3/5] Train on sim bench"
python3 ml/train_dewleaf_policy.py --data logs/sim_bench_14night.csv --out models/dewleaf_policy_bench_sim.h --report-out ml/artifacts/bench_sim_report.json --model-out ml/artifacts/bench_sim.joblib --splits 5 --model hgb
echo "[4/5] Eval policy"
python3 ml/evaluate_policy.py --data logs/sim_bench_14night.csv --model ml/artifacts/bench_sim.joblib --out ml/artifacts/bench_sim_eval.json
echo "[5/5] Hardware check"
if command -v pio >/dev/null 2>&1; then
  echo "pio found: $(command -v pio)"
  if ls /dev/ttyACM* /dev/ttyUSB* >/dev/null 2>&1; then
    echo "Serial device detected - run: pio run -t upload -d firmware/dewleaf_firmware"
  else
    echo "No serial device detected. Connect ESP32-S3 then upload."
  fi
else
  echo "pio not found. Install: python3 -m pip install --user platformio"
fi
echo "== done =="
