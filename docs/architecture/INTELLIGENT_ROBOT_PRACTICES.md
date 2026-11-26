# Intelligent Robot Software Practices -> DewLeaf Mapping

## What high-reliability autonomous systems do

| Practice | Seen in (examples) | DewLeaf status | Next |
|---|---|---|---|
| **RT/control vs runtime separation** | Soma `robot-rt`/`robot-runtime`; rover FSW layering | Partial: ESP32 firmware state machine + Python runtime tools | Formalize message contract; keep control loop deterministic |
| **Explicit contracts/schemas** | Soma Plant/Protocol; rover interfaces | Yes: telemetry/model schemas, CSV contract, API endpoints | Versioned schema registry + compatibility tests |
| **Digital twin / SIL before hardware** | Ag robotics digital twins; Nobleo virtual testing; NASA WSTS | Yes: `ml/hil_simulator.py`, demo, replay | Add fault injection scenarios, golden regressions |
| **Fault protection: monitor->detect->respond** | Mars rover fault protection engine; runtime monitors | Yes: `ml/runtime_monitor.py`, safety overrides in engine/firmware | Fault catalog config, auto-response hooks, PFR-style log |
| **Observability/flight recorder** | Soma metrics/events/traces/MCAP; rover EVRs/telemetry | Partial: CSV logs, decision JSONL, replay reports | Structured event bus, metrics summary, crash/fault timeline |
| **Test ladder** | Unit/sim/SIL/HIL/field; rover V&V campaign | Partial: unit/data/contract/sim, HIL replay; no HIL hardware | Add fault-injection/regression/golden tests, hardware bringup |
| **Deterministic replay/regression** | Rover sim/replay, digital twin testing | Yes: `ml/replay.py`, seeded HIL/sim | Golden output hashes, CI replay gate |
| **Safety as independent invariant** | Soma SA chain; rover safing/fault responses | Yes: fan-before-Peltier, frost, ADC1, WDT, bus/Wh guards | Formal safety case, watchdog fault taxonomy |
| **Off-nominal/fault injection** | Mars 2020 FP validation, DTP testing | Initial: `ml/fault_injector.py` | Expand scenario library, coverage matrix |
| **Measured/simulated honesty** | Good research/ops practice | Yes: reports/docs label synthetic vs real | Enforce in report schema/CLI banners |

## Software-first definition of done (before physical build)
- [x] Firmware builds and safety interlocks present.
- [x] Telemetry contract + schema checks pass.
- [x] Digital twin emits same schema as device.
- [x] Replay produces decisions + fault events deterministically.
- [x] Fault injection tests cover critical safety/sensor faults.
- [ ] Golden regression baselines versioned in CI.
- [ ] Real 14-night bench telemetry validates D0.3 claim.
