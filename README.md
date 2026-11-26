# DewLeaf AI — Node-1

Autonomous off-grid atmospheric water + root-zone intelligence device for dryland farming. Phase 0 bench-rig repo: firmware, telemetry, leak-free ML, edge policy, software twin.

> **Status:** software/sim validation ready; **real D0.3 hardware proof pending**. All high performance claims outside measured bench runs are synthetic/simulated.

## Quick Start

```bash
make setup     # install python deps
make test      # py_compile + data contract + golden baseline + unit/data tests
make demo      # Nairobi night software demo -> ml/artifacts/demo_night.*
make sim       # 14-night sim bench + train + eval
make build-fw  # PlatformIO ESP32-S3 build (needs platformio)
```

## What Works Now (Software)

| Area | Status | Evidence |
|---|---|---|
| ESP32-S3 firmware build | PASS | `make build-fw`, 394KB bin / 7.7% RAM |
| Telemetry contract | PASS | `ml/datasets/schemas/telemetry.schema.json`, `scripts/checks/check_data_contract.py` |
| Golden regression baseline | PASS | `tests/golden/hil_replay_summary.json`, `scripts/checks/check_golden.py` |
| Unit/data/safety tests | PASS | `PYTHONPATH=. pytest -q tests/unit tests/data` |
| Software twin / HIL sim | PASS | `ml/hil_simulator.py` emits same CSV schema as firmware |
| Replay + fault monitor | PASS | `ml/replay.py`, `ml/runtime_monitor.py`, `ml/fault_injector.py` |
| Explainable decision engine | PASS | `ml/intelligence_engine.py` with `why` traces + safety overrides |
| Cloud API scaffold | PASS | `software/cloud/api.py` (`/health`, `/api/telemetry`, `/api/decide`) |

## What Needs Hardware (Not Yet Provable)

- **D0.3 acceptance**: 14-night real Nairobi bench telemetry, GroupKFold by `night_id`, **>=15% net mL/Wh vs static baseline** on measured data.
- Electrical validation: brownout/full-load, INA219/YF-S201 calibration (±3%), Peltier/fan/frost interlocks, ADC noise, SD/RF reliability.
- Real dew yield; current ML gains are **physics-informed synthetic/sim**.

## Repository Map

```text
docs/                    Architecture, ADRs, ops, reports, audit
  adr/                   Dual-rail, leak-free ML, reward objective
  architecture/          System map, intelligent-robot practices
  ops/                   Runbook, deployment, software twin, fundraising
hardware/                BOM, wiring, calibration, bringup checklist
firmware/dewleaf_firmware/ ESP32-S3 PlatformIO app (src/main.cpp)
ml/                      Data ingest/build/train/eval/export/replay/twin
  datasets/schemas/      Telemetry/model contracts
  models/cards/          Model cards and caveats
logger/                  Serial CSV logger (optional decision/API forwarding)
software/cloud/          Minimal telemetry/decision API scaffold
edge/policy/             Exported edge artifacts
tests/                   unit/data tests + golden baseline
scripts/checks/          Data contract + golden regression checks
```

## Key Commands

```bash
# Software validation
make test
PYTHONPATH=. python3 scripts/checks/check_golden.py

# Digital twin
PYTHONPATH=. python3 ml/hil_simulator.py --nights 1 --step-s 600 --seed 7 > logs/hil.csv
PYTHONPATH=. python3 ml/replay.py --data logs/hil.csv --out ml/artifacts/hil_replay.json

# Fault injection
PYTHONPATH=. python3 ml/fault_injector.py --in logs/hil.csv --out logs/hil_faulty.csv --rate 0.1
PYTHONPATH=. python3 ml/replay.py --data logs/hil_faulty.csv --out ml/artifacts/hil_faulty_replay.json

# Logger (when hardware connected)
python logger/dewleaf_logger.py --port /dev/ttyACM0 --out logs/dewleaf.csv --decision-out logs/decisions.jsonl

# Real D0.3 retrain (after 14-night bench capture)
python ml/train_dewleaf_policy.py --data logs/dewleaf.csv --out models/dewleaf_policy.h --report-out ml/artifacts/real_validation_report.json
```

## Safety / ML Invariants

- **Power**: 12V actuator rail isolated from 3.3V logic rail; no actuator current through logic buck.
- **Actuation**: Peltier never on without fan; frost guard; flyback diodes on inductive loads.
- **Sensing**: soil probes on ADC1 only.
- **ML**: GroupKFold by `night_id`; reward `R = harvested_ml - lambda*Wh`; report label source (measured vs synthetic).
- **Claims**: no performance claim accepted without raw measured data + reproducible report.

## Golden Regression Baseline

`tests/golden/hil_replay_summary.json` pins a deterministic HIL replay (seed 7, 1 night, 600s step). CI and `make test` fail on drift. Update intentionally only when behavior changes:

```bash
PYTHONPATH=. python3 ml/hil_simulator.py --nights 1 --step-s 600 --seed 7 > /tmp/golden_hil.csv
PYTHONPATH=. python3 ml/replay.py --data /tmp/golden_hil.csv --out /tmp/golden_replay.json
# regenerate tests/golden/hil_replay_summary.json, review diff, commit with reason
```

