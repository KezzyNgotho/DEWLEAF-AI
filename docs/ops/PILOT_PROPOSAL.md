# DewLeaf Phase 0 Pilot Proposal

## Objective
Validate DewLeaf Node-1 bench rig (D0.1-D0.3) under real Nairobi nighttime conditions before Machakos Phase 1.

## Scope
- Install 1m² 20° hydrophilic canopy rig, dual-rail power, sensors/actuators, logger.
- Run 14 consecutive nights; log telemetry every 10s to SD+serial.
- Compare smart policy vs static baseline by `night_id` grouped evaluation.

## Deliverables
1. Build + calibration log (`hardware/calibration`, `hardware/bringup`).
2. Raw dataset (`logs/dewleaf.csv`, checksum, manifest).
3. Validation report (`ml/artifacts/real_validation_report.json`) with mL, Wh, mL/Wh, improvement %.
4. 60s pre-dawn shedding demo video.

## Budget
See `hardware/bom/phase0_budget_template.csv`. Add 10-15% contingency and local transport/labor.

## Risks & Mitigations
- **No water yield**: verify dew-point nights, mesh angle, shedding timing, gutter seal.
- **Brownouts**: isolate rails, fuse branches, load test before deployment.
- **Sensor drift/noise**: calibrate INA219/YF-S201/soil probes; ADC1 only.
- **Overclaim risk**: label all synthetic/sim results clearly; D0.3 pass requires real data.

## Call to Action
Fund Phase 0 bench build now; unlock Phase 1 only on measured D0.3 pass criteria.
