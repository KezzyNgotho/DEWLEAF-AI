# Alert Rules (Phase 0/1)

| Alert | Condition | Severity | Response |
|---|---|---|---|
| Low bus voltage | `bus_v < 11.2` | warn/critical | disable high-load actuators, check battery/MPPT |
| Peltier no fan | `peltier==1 && fan==0` | critical | force fan on, disable peltier, inspect MOSFET/wiring |
| Frost guard | `spine_temp_c <= 1.5` while nucleation active | critical | disable peltier, log event |
| Telemetry gap | no row for > 5 min during night | warn | check logger/serial/SD/power |
| Fault spike | >5 critical faults/hour | critical | safe mode passive_only, notify operator |
| Flow anomaly | non-monotonic or zero during expected shedding | warn | inspect YF-S201/filter/gutter |
| Model drift | reward/MAE drift beyond threshold vs baseline | warn | retrain/calibrate on measured data |
