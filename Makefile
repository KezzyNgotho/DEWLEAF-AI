.PHONY: help setup test sim demo train build-fw clean

PY=python3
PIO=~/.local/bin/platformio

help:
	@echo "Targets: setup test sim demo train build-fw clean golden"

setup:
	$(PY) -m pip install -r logger/requirements.txt -r ml/requirements.txt

test:
	$(PY) -m py_compile logger/dewleaf_logger.py ml/*.py
	$(PY) scripts/checks/check_data_contract.py
	$(PY) scripts/checks/check_golden.py
	$(PY) -m pytest -q tests/unit tests/data

sim:
	$(PY) ml/simulate_bench_run.py --out logs/sim_bench_14night.csv --nights 14 --seed 11
	$(PY) ml/train_dewleaf_policy.py --data logs/sim_bench_14night.csv --out models/dewleaf_policy_bench_sim.h --report-out ml/artifacts/bench_sim_report.json --model-out ml/artifacts/bench_sim.joblib --splits 5 --model hgb
	$(PY) ml/evaluate_policy.py --data logs/sim_bench_14night.csv --model ml/artifacts/bench_sim.joblib --out ml/artifacts/bench_sim_eval.json

demo:
	$(PY) ml/demo_software.py --weather ml/data/open_meteo/2024/Nairobi.csv --date 2024-02-15 --out ml/artifacts/demo_night

train:
	$(PY) ml/train_dewleaf_policy.py --data ml/data/dewleaf_kenya_2023_2024_v2.csv --out models/dewleaf_policy_kenya_2023_2024_v2.h --report-out ml/artifacts/kenya_2023_2024_v2_report.json --model-out ml/artifacts/dewleaf_models_kenya_2023_2024_v2.joblib --splits 5 --model hgb --max-rows 120000

build-fw:
	$(PIO) run -d firmware/dewleaf_firmware -e esp32s3

clean:
	rm -rf firmware/dewleaf_firmware/.pio ml/__pycache__ logger/__pycache__ tests/__pycache__

golden:
	PYTHONPATH=. $(PY) scripts/checks/check_golden.py

dashboard:
	PYTHONPATH=. $(PY) software/cloud/dashboard.py

export-tflite:
	PYTHONPATH=. $(PY) ml/export_tflite.py --data logs/sim_bench_14night.csv --out-dir ml/artifacts/tflite
