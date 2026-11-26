# Bench Data Collection Protocol (D0.3)

## Objective
Collect 14 consecutive nights of real Nairobi bench telemetry for leak-free D0.3 validation.

## Pre-run (day 0)
- Complete `docs/hardware/BRINGUP_CHECKLIST.md` and calibration records.
- Set DS3231 RTC to local time; verify `night_id` rollover at 18:00 boundary.
- Verify SD logging + serial logging simultaneously.
- Calibrate INA219 against meter and YF-S201 against measured volume (±3%).
- Record BOM/config/firmware git commit hash and `models/*` artifact hashes.

## Per-night procedure
1. 17:30 - clean mesh/gutter, confirm vessel empty, photograph rig.
2. 18:00 - start logger: `python logger/dewleaf_logger.py --port /dev/ttyACM0 --out logs/dewleaf.csv --decision-out logs/decisions.jsonl`
3. Overnight - system runs autonomously; no manual actuator overrides except safety emergency.
4. 07:30 - record manual harvested volume (mL), note weather/faults.
5. 08:00 - export SD copy, append to run manifest, checksum files.

## Data integrity
- Store raw CSV immutable; derived files in separate folder.
- Manifest fields: date, night_id, start/end, firmware commit, config hash, manual_ml, anomalies, operator.
- `sha256sum logs/dewleaf.csv > logs/dewleaf.csv.sha256`

## Acceptance
- >=14 nights, no missing night_id, no unexplained timestamp resets.
- Calibration within spec; safety interlocks never violated.
- Run `python ml/train_dewleaf_policy.py --data logs/dewleaf.csv --report-out ml/artifacts/real_validation_report.json`
- Claim D0.3 only if `measured_data=true` and `d0_3_claim_valid=true`.

## Safety abort
Abort and safe rig if: smoke/overheat, Peltier without fan, bus sag/reset loop, water ingress, or wiring fault. Log incident in manifest.
