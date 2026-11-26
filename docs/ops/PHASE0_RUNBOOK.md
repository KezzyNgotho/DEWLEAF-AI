# Phase 0 Runbook (Nairobi Bench Rig)

## D0.1 — Bench Rig
1. Assemble 1 m², 20° hydrophilic canopy with anodized Al spine and sealed gutter.
2. Wire dual-rail power: fused 12V actuator bus + LM2596 5V/3.3V logic rail.
3. Install 6-channel MOSFET board with 1N4007 flyback diodes and gate pull-downs.
4. Place BME280, DS18B20, ADC1 soil probes, INA219, YF-S201 (after 100-mesh filter).
5. Run calibration per `docs/CALIBRATION.md`; all key measurements within ±3%.

## D0.2 — Firmware & Logger
1. Flash `firmware/dewleaf_firmware`.
2. Start logger: `python logger/dewleaf_logger.py --port /dev/ttyACM0 --out logs/dewleaf.csv`.
3. Verify CSV fields include `night_id`, `action_id`, `wh_total`, `flow_l_window`.
4. Run 72+ hours; confirm watchdog stability and SD fallback on USB disconnect.

## D0.3 — Leak-Free ML Proof
1. Collect 14 nights real data (or generate sample): `python ml/generate_sample_data.py --out ml/data/nairobi_14_night.csv`.
2. Train: `python ml/train_dewleaf_policy.py --data ml/data/nairobi_14_night.csv --out models/dewleaf_policy.h`.
3. Confirm report shows GroupKFold by `night_id` and mean improvement ≥15% vs static baseline.
4. Deploy exported policy/header and capture 60s pre-dawn shedding video.

## Sign-Off Gate

Do **not** commit Phase 1 field capital until D0.1–D0.3 are empirically verified.
