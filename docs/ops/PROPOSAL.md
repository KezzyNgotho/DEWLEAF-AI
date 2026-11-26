# DewLeaf Node-1 — Pilot/Prototype Proposal

**Project:** DewLeaf AI (DewLeaf Node-1, Phase 0)  
**Location:** Nairobi, Kenya (bench) → Machakos (pilot, post-D0.3)  
**Date:** 2026-11-26  
**Contact:** Keziah Ngotho — [add email/phone/LinkedIn]  
**Repo:** https://github.com/KezzyNgotho/DEWLEAF-AI

## Executive Summary
DewLeaf Node-1 is an off-grid, edge-AI dew harvesting and root-zone resilience system for water-stressed smallholder/nursery settings. It combines passive radiative capture, pre-dawn shedding, covered storage, and controlled micro-irrigation. The controller optimizes **net water per energy** (`R = harvested_ml - lambda*Wh`) under hard safety constraints.

**Current status:** software/firmware stack is built and tested (ESP32-S3 build PASS, CI/tests, explainable decision engine, HIL/replay/fault injection, model registry/promotion gates). **No real D0.3 claim yet**: performance gains are synthetic/sim/physics-informed until 14-night measured bench telemetry passes the acceptance gate.

**Ask:** cash, in-kind components, lab/makerspace access, or a pilot host to complete D0.1 build and D0.3 measured validation.

## Problem
- Semi-arid growers face unreliable rainfall, expensive irrigation, and crop stress.
- Active water-generation/cooling can be energy-intensive and risky off-grid.
- Dew is available but often lost to re-evaporation without timed capture/shedding.
- Systems need auditable safety and measured proof, not simulated-only claims.

## Proposed Solution
### System
- **Sensing:** BME280, DS18B20, ADC1 soil probes, INA219, YF-S201 flow, RTC, SD.
- **Actuation:** TEC1-12706 Peltier + fan, vibration motors, flush/drip valves via low-side MOSFETs.
- **Power:** 12V bench supply now (D0.1–D0.3), solar/MPPT/LiFePO4 later. 12V actuator rail isolated from 3.3V logic rail.
- **Control:** ESP32-S3 edge policy with confidence/risk/reason codes and local telemetry.

### Safety Invariants (non-negotiable)
- Peltier OFF unless fan ON.
- Frost guard enforced.
- Soil probes on ADC1 only.
- 12V actuator rail isolated from 3.3V logic; flyback diodes on inductive loads.
- No secrets in repo/logs; measured-data-only D0.3 claims.

## What Is Already Built
| Area | Evidence |
|---|---|
| Firmware | `firmware/dewleaf_firmware/` builds for ESP32-S3 (PlatformIO). |
| ML/Decision | Leak-free GroupKFold by `night_id`, explainable engine, action guard, calibration, drift, TFLite/golden-vector export fallback. |
| Validation | `make test` (py_compile, data contract, golden baseline, pytest). Scenario/fault/replay tests. |
| Ops/Safety | FMEA, bench bringup, bench data protocol, release/OTA checklist, model registry/promotion gate. |
| Repro | `make test && make demo && make build-fw`. |

## Pilot Scope & Timeline
| Phase | Duration | Activities | Deliverable |
|---|---:|---|---|
| A. Procure/bench electronics | Week 1 | Buy Phase A/B parts, flash firmware, sensor logging | Working logger, photos |
| B. D0.1 build & calibration | Week 2 | Assemble 1m² 20° rig, wire rails, calibrate INA219/YF-S201/sensors | Bringup checklist, calibration sheet |
| C. 14-night measured run | Weeks 3–4 | 10s telemetry, SD+serial, checksums/manifests | `logs/dewleaf.csv`, raw data package |
| D. D0.3 report | Week 5 | Train/eval GroupKFold by `night_id` vs static baseline | `real_validation_report.json`, mL/Wh chart, 60s video |

## Acceptance / Kill Criteria
Proceed only if all are true on **real measured** data:
- 14 consecutive nights captured with auditable logs/manifests.
- GroupKFold by `night_id`; **>=15% net mL/Wh improvement vs static baseline**.
- No safety/brownout/flyback/interlock failures.
- All claims labeled with `measured_data=true` and valid report.

If criteria fail, publish results, diagnose root cause, and do not scale to Phase 1.

## Budget (rough, buy-slowly)
| Phase | Items | Est. USD |
|---|---|---:|
| A. Electronics/logger | ESP32-S3, BME280, DS18B20x2, soilx2, RTC, SD, INA219, wires/fuses, 5V supply | $60–120 |
| B. Actuator/safety bench | MOSFETs, 1N4007, gate parts, Peltier, 12V fan, vibex2, valvesx2, 12V supply, buck, fuses, meter | $70–160 |
| C. Measured D0.1 rig | 1m² mesh, Al spine/frame, gutter/vessel, scale, YF-S201+filter, IP65 enclosure, consumables | $120–350 |
| D. Off-grid upgrade | 50W solar, MPPT, 12V 20Ah LiFePO4, mounts/weatherproofing, contingency | $180–450 |
| **Total A–D** | | **$430–1080** |

*Prices are rough ranges; fill `hardware/bom/phase0_budget_template.csv` with Nairobi quotes.*

## Funding / Support Requested
We can accept flexible support:
- **Cash:** $250–1100 depending on phase, or staged disbursement.
- **In-kind:** components from BOM, bench power supply, tools, PCB/enclosure materials.
- **Access:** makerspace/lab bench, oscilloscope/meter, soldering station.
- **Pilot host:** site with secure night setup and feedback.

## Risks & Mitigations
| Risk | Mitigation |
|---|---|
| Low/no dew yield | Validate dew-point nights, mesh angle, shedding timing, gutter seal; report honestly. |
| Electrical/brownout | Isolated rails, fused branches, bench supply first, full-load test before deployment. |
| Sensor drift | Calibrate INA219/YF-S201/soil; ADC1-only; calibration sheet. |
| Overclaim | Model registry/promotion gate; D0.3 claim blocked unless measured report passes. |
| Safety | Bringup checklist, FMEA, interlocks, flyback diodes, RCD/GFCI for mains bench setup. |

## Why DewLeaf
- **Measured-first:** explicit D0.3 gate, no synthetic-data claims.
- **Safety-first:** hardware interlocks and FMEA before field scaling.
- **Lean:** bench supply now, solar later; buy-slowly phases.
- **Reproducible:** open repo, tests, CI, data contracts, golden baseline.

## Attachments / Links
- Pitch deck: `docs/ops/DewLeaf_Pitch_Deck.pptx`
- 1-pager: `docs/ops/FUNDRAISING_ONE_PAGER.md`
- BOM: `hardware/bom/phase0_budget_template.csv`
- Bringup: `docs/hardware/BRINGUP_CHECKLIST.md`
- Bench protocol: `docs/ops/BENCH_DATA_COLLECTION_PROTOCOL.md`
- Safety: `docs/safety/FMEA.md`
