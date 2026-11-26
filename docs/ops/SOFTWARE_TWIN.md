# Software Twin (HIL-style)

`ml/hil_simulator.py` emits the **same CSV telemetry contract** as firmware, driven by the same decision engine (`ml/intelligence_engine.py`). This lets you exercise logger, cloud API, dashboards, and ML pipeline without ESP32 hardware.

## Run

```bash
# Generate one simulated night (fast)
PYTHONPATH=. python3 ml/hil_simulator.py --nights 1 --step-s 600 --seed 7 > logs/hil_night.csv

# Real-time-ish stream over TCP (logger can be adapted to socket source; stdout default)
PYTHONPATH=. python3 ml/hil_simulator.py --realtime --speed 600 --tcp-port 9000
```

## What it validates
- Telemetry schema/contract, state transitions, decision traces, ML retrain/eval pipeline.
- Safety logic in decision engine (frost/energy/bus/soil guards).

## What it does NOT validate
- Real electrical behavior: brownouts, EMI, ADC noise, sensor calibration, MOSFET/flyback wiring, Peltier thermals, flow-meter pulses, SD timing, RF/GSM.
- Real dew physics/yield. All yields are simulated.

## Hardware parity path
1. Run software twin through same logger/API/ML path.
2. Flash same policy/config to ESP32.
3. Replace simulator with serial device; keep downstream pipeline unchanged.
