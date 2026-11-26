# DewLeaf System Map

## Components
- **Hardware rig**: canopy, spine, gutters, bladder/tank, 12V rail, 5V/3.3V logic rail, sensors, actuators.
- **Firmware**: state machine + safety + edge policy + telemetry logger.
- **ML pipeline**: weather ingest, dataset build, leak-free train/eval, edge export.
- **Software ops**: logger, demo, reports, deployment scripts.

## Data Contracts
- Telemetry row: `ml/datasets/schemas/telemetry.schema.json`
- Model report: `ml/datasets/schemas/model_report.schema.json`
- Firmware log header: `firmware/dewleaf_firmware/src/main.cpp` `ensureSdHeader()`

## Control Loop
1. Sense: BME280/DS18B20/soil/INA219/flow/RTC.
2. Decide: safety overrides + reward policy (`R=ml-lambda*Wh`).
3. Actuate: Peltier/fan/vibe/valves via MOSFETs.
4. Log: CSV to SD + serial; nightly summary later GSM.
5. Learn offline: GroupKFold by `night_id`; export edge artifact; deploy after validation.

## Safety Invariants
- Peltier never on without fan.
- Frost guard disables nucleation below threshold.
- ADC1 only for soil analog reads.
- Inductive loads require flyback diodes.
- Actuator rail isolated from logic rail.
