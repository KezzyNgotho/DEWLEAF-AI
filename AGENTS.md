# AGENTS.md - DewLeaf Working Rules

## Purpose
Phase 0 DewLeaf Node-1: build/test bench-rig firmware, data pipeline, and edge policy with safety-first, leak-free validation.

## Commands
- `make test` - py_compile, data contract checks, pytest unit/data.
- `make sim` - simulated 14-night run + train + eval.
- `make demo` - software night demo from Nairobi weather.
- `make build-fw` - PlatformIO ESP32-S3 build.

## Repo Rules
- Keep generated large datasets in `ml/data/` ignored paths; commit manifests/schemas/reports, not raw bulk where avoidable.
- Single source for firmware runtime files: `firmware/dewleaf_firmware/src/`.
- Any ML metric claim must state dataset source and whether labels are measured or synthetic.
- Validation uses GroupKFold by `night_id`; never random-split time-correlated night rows.

## Safety Invariants (do not regress)
- Peltier OFF unless fan ON; frost guard enforced.
- Soil ADC reads on ADC1 pins only.
- 12V actuator rail isolated from 3.3V logic rail; flyback diodes on inductive loads.
- No secrets in repo/logs.

## Definition of Done
- Code compiles/lints/tests pass.
- Docs/contracts updated for behavior changes.
- Real hardware claims marked "requires bench telemetry" unless measured.
