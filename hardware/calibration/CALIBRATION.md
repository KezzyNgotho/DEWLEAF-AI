# Calibration & Validation

## D0.1 Calibration Targets

| Instrument | Reference | Target | Method |
|---|---|---:|---|
| INA219 voltage | Calibrated multimeter | ±3% | Compare at idle, sensor-only, actuator-load states |
| INA219 current | Calibrated meter/shunt | ±3% | Measure each actuator channel independently |
| YF-S201 flow | Digital scale / graduated cylinder | ±3% | Run known volume, compute pulses/L, update `FLOW_PULSES_PER_LITER` |
| Soil probes | Dry air / saturated medium / field points | Repeatable monotonic curve | Record raw ADC at known moisture points; store calibration map |
| DS18B20 | Reference thermometer | ±0.5°C | Ice water and ambient checks |
| BME280 | Reference weather meter | Plausible ±3% RH/temp | Co-locate for 30 min |

## YF-S201 Calibration Procedure

1. Install 100-mesh filter upstream.
2. Prime line; remove air bubbles.
3. Dispense known volume (e.g., 1000 mL) into scale-verified container.
4. Record pulse count.
5. `pulses_per_liter = pulses / liters`.
6. Repeat 3 times; use mean if within ±3%.

## Energy Accounting

- Log INA219 voltage/current every 5 s and integrate Wh.
- Attribute Wh to active `action_id` window.
- Reward metric: `R = net_harvested_ml - lambda_wh_penalty * Wh`.

## D0.3 Acceptance

- GroupKFold by `night_id` only.
- No rows from same night in train and test.
- Report mean reward improvement vs static baseline; target ≥15% net mL/Wh.
- Export selected policy to `models/dewleaf_policy.h`.
