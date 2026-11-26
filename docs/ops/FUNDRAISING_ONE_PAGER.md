# DewLeaf Node-1 — Phase 0 Fundraise (1-Pager)

## Ask
**Raise:** KES ____ / USD ____ (fill from `hardware/bom/phase0_budget_template.csv`)  
**Use:** Build D0.1 Nairobi 1m² bench rig + run 14-night D0.3 validation.  
**Runway:** ____ weeks. **Instrument:** grant / SAFE / convertible note / pilot prepay.

## Problem
Semi-arid smallholders face unreliable rain, expensive irrigation, and crop loss. Water/energy constraints make always-on active cooling uneconomic.

## Solution
DewLeaf Node-1: passive radiative dew capture + pre-dawn vibration shedding + covered storage + root-zone micro-irrigation, controlled by edge AI that optimizes **mL harvested per Wh** under safety constraints.

## What’s Built (de-risked software)
- ESP32-S3 firmware builds (394KB bin), safety interlocks, telemetry contract.
- Leak-free ML pipeline (GroupKFold by `night_id`), edge policy/export, explainable decision traces.
- Reproducible demo: `make test && make demo && make build-fw`.  
**Honest status:** performance numbers currently synthetic/simulated; real D0.3 needs bench telemetry.

## Milestones (funded)
| Milestone | Timeline | Deliverable | Evidence |
|---|---:|---|---|
| M1 Procurement | Week 1 | BOM bought, receipts | invoice log |
| M2 Rig Build | Week 2 | D0.1 bench rig assembled | photos/video, bringup checklist |
| M3 Calibration | Week 2 | INA219/YF-S201/sensors within spec | calibration sheet |
| M4 14-Night Run | Weeks 3-4 | Raw telemetry CSV + SD logs | `logs/dewleaf.csv`, checksums |
| M5 D0.3 Report | Week 4 | Leak-free model vs baseline | report JSON, mL/Wh chart, video |

## Why Now / Why Us
- Keziah: systems/embedded/field ops. Alex: TinyML/edge/cloud.
- Local Nairobi/Machakos validation path; low-cost, modular, off-grid-first design.

## Investor Test / Kill Criteria
Proceed to Phase 1 only if 14-night real data shows **>=15% net mL/Wh improvement vs static baseline** (GroupKFold by night_id), no safety/brownout failures, and auditable logs.
