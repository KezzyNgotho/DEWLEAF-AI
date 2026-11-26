# Test Ladder

| Lane | Command/Location | Gate |
|---|---|---|
| Static/compile | `python3 -m py_compile ...`, `pio run` | every change |
| Data contract | `python3 scripts/checks/check_data_contract.py` | every change |
| Unit/data tests | `pytest -q tests/unit tests/data` | every change |
| Sim integration | `make sim` | before merge/release |
| Firmware HIL smoke | flash + serial logger + actuator dry-run | with hardware |
| 14-night bench | real `logs/dewleaf.csv` + GroupKFold report | D0.3 sign-off |
| Field pilot | Machakos telemetry/water/yield audit | Phase 1 gate |
