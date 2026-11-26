# Hardware Bringup Checklist

## Power
- [ ] 12V rail fused; no actuator current through LM2596.
- [ ] 3.3V logic rail stable under actuator transients (scope/meter).
- [ ] Common star ground verified.

## Actuators
- [ ] MOSFET gate pull-downs present; logic-level parts only.
- [ ] 1N4007 flyback orientation checked on every inductive load.
- [ ] Peltier never energized without fan.
- [ ] Manual test each channel: Peltier/fan/vibA/vibB/flush/drip.

## Sensors
- [ ] BME280 I2C address/responding.
- [ ] DS18B20 IDs read; 4.7k pull-up installed.
- [ ] Soil probes on ADC1 only; dry/wet calibration recorded.
- [ ] INA219 within ±3% vs meter.
- [ ] YF-S201 pulses/L calibrated with 100-mesh filter installed.

## Logging
- [ ] RTC time set; night_id rolls over correctly.
- [ ] SD logs created; USB unplug test retains SD logging.
- [ ] CSV schema matches `ml/datasets/schemas/telemetry.schema.json`.
