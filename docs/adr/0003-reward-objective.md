# ADR 0003: Reward Objective for Edge Policy

- Status: Accepted
- Date: 2026-11-24

## Context
Maximizing harvested water alone can waste battery. Actuators have energy cost and safety constraints.

## Decision
Optimize `R = harvested_ml - lambda * Wh`, with `lambda` configurable (default 5.0). Hard safety constraints override reward (frost guard, Peltier fan interlock, soil bounds, nightly energy cap).

## Consequences
- Positive: aligns with field energy budget.
- Negative: lambda requires calibration per hardware/site.
- Verification: report policy vs static baseline; field A/B with INA219 and flow meter.
