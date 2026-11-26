# DewLeaf FMEA / Fault Matrix (Phase 0)

| Failure | Cause | Effect | Detection | Safe response | Test |
|---|---|---|---|---|---|
| Peltier on, fan off | MOSFET/wiring/logic fault | Overheat, damage | runtime monitor `SAFETY_PELTIER_NO_FAN` | disable peltier, force fan check | `tests/unit/test_runtime_monitor.py` |
| Frost on spine | cold night, bad control | ice damage, poor yield | spine temp <= guard | disable peltier | intelligence/fault tests |
| Low bus voltage | battery sag, MPPT fault | brownout/reset | bus_v monitor | passive_only, disable high load | runtime monitor |
| Soil probe divergence | corrosion/noise/wiring | bad irrigation decision | abs(A-B)>35 | block irrigation, inspect sensor | runtime monitor |
| Flow stuck/non-monotonic | clogged filter, bad sensor | false yield accounting | flow checks | flag data invalid | runtime monitor/replay |
| Timestamp regression | RTC fault/reset | bad night grouping | ts check | mark invalid segment | runtime monitor |
| Model overconfidence | synthetic calibration | bad actuator choice | confidence/risk/model_source | degrade to safe action | intelligence engine tests |
