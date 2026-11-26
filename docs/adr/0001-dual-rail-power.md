# ADR 0001: Dual-Rail Power Isolation

- Status: Accepted
- Date: 2026-11-24

## Context
Peltier, motors, and valves create high-current transients on 12V rail. ESP32/ADC/I2C sensors are noise/brownout sensitive.

## Decision
Use separate 12V actuator rail and LM2596-derived 5V/3.3V logic rail with common star ground, decoupling, fuses, and flyback diodes. No actuator current through logic buck.

## Consequences
- Positive: brownout resilience, cleaner sensor readings.
- Negative: more wiring/BOM complexity; requires bringup validation.
- Verification: full-load actuator test with no ESP32 reset; INA219 rail measurements.
