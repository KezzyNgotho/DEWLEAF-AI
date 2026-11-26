# DewLeaf Phase 0 Deployment

## What I can do now (no hardware attached)
- Build/validate firmware, logger, and ML pipeline.
- Generate simulated bench logs for contract tests.
- Train/export policy artifacts.

## What needs physical bench rig
- Flash ESP32-S3: `pio run -t upload -d firmware/dewleaf_firmware` or Arduino IDE.
- Serial logger: `python logger/dewleaf_logger.py --port /dev/ttyACM0 --out logs/dewleaf.csv`.
- 14-night real capture with RTC set, SD inserted, INA219/YF-S201 calibrated.
- Retrain on real log: `python ml/train_dewleaf_policy.py --data logs/dewleaf.csv --out models/dewleaf_policy.h --report-out ml/artifacts/real_validation_report.json`.

## Current environment check
- `pio`/`arduino-cli`: not installed
- Serial devices: none detected (`/dev/ttyACM*`, `/dev/ttyUSB*` absent)
- `pyserial`: installed

## Acceptance gate
D0.3 passes only when real 14-night bench data, GroupKFold by `night_id`, shows >=15% net mL/Wh vs static baseline.
