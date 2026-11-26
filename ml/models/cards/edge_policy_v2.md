# Model Card: DewLeaf Edge Policy v2

## Intended Use
Select actuator action for DewLeaf Node-1 to maximize `harvested_ml - lambda*Wh` under safety constraints. Phase 0 decision support/pretraining only.

## Training Data
- Open-Meteo ERA5 hourly weather, 47 Kenyan counties, 2023-2024.
- Physics-informed synthetic labels (`label_source=physics_informed_open_meteo_v2`). Not measured dew.

## Validation
- GroupKFold by `night_id`, no leakage assert.
- v2 full report: `ml/artifacts/kenya_v2_full_report.json` - 250k rows, 34385 nights, mean improvement 220.5% vs static baseline on synthetic labels.

## Limitations / Risks
- Synthetic labels encode assumed physics; may overestimate real gain.
- Must retrain/calibrate on real 14-night bench telemetry before D0.3 sign-off.
- Edge export currently heuristic/compact forest; full TFLM quantized path pending.

## Safety
Policy cannot override firmware hard interlocks: fan-before-Peltier, frost guard, ADC1-only soil, WDT, energy caps.
