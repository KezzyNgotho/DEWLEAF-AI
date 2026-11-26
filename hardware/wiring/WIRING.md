# Wiring & Pin Map

## Pin Map (ESP32-S3-DevKitC-1 N16R8)

| Function | GPIO | Notes |
|---|---:|---|
| I2C SDA | 8 | BME280, INA219, DS3231 |
| I2C SCL | 9 | 4.7k pull-ups if module absent |
| DS18B20 data | 4 | 4.7 kΩ pull-up to 3.3V |
| Soil probe A | 1 | ADC1 only |
| Soil probe B | 2 | ADC1 only |
| Flow meter pulse | 5 | YF-S201, interrupt/input |
| MOSFET CH1 Peltier | 10 | 12V rail, fan interlock required |
| MOSFET CH2 Heatsink fan | 11 | 12V rail |
| MOSFET CH3 Vibration motor A | 12 | 12V rail, flyback diode |
| MOSFET CH4 Vibration motor B | 13 | 12V rail, flyback diode |
| MOSFET CH5 Solenoid/valve flush | 14 | 12V rail, flyback diode |
| MOSFET CH6 Solenoid/valve drip | 21 | 12V rail, flyback diode |
| SD CS | 41 | SPI |
| SD MOSI | 40 | SPI |
| SD SCK | 39 | SPI |
| SD MISO | 38 | SPI |
| Status LED | 48 | Optional |

> Adjust pins to match final board layout; keep soil probes on ADC1 and avoid strapping pins.

## MOSFET Low-Side Driver

```text
ESP32 GPIO --100R--+-- MOSFET GATE (AOD4184/IRL540N)
                   |
                 100k
                   |
                  GND

12V+ ---- LOAD ----+---- MOSFET DRAIN
                   |
                 [1N4007]  (stripe/cathode to +12V, anode to drain) for inductive loads
                   |
               MOSFET SOURCE ---- GND (power ground)
```

## Power

```text
50W Solar -> MPPT -> 12V 20Ah LiFePO4 -> fused 12V actuator bus
                                      -> LM2596 buck -> 5V/3.3V logic rail
                                                    -> 100uF + 0.1uF decoupling
Common ground: battery negative star point.
```

## Safety Rules

1. Confirm 1N4007 orientation before powering inductive loads.
2. Never energize Peltier without heatsink fan.
3. Fuse every 12V actuator branch.
4. Keep I2C lines short in IP65 vault; use shielded cable for long sensor runs.
5. Use 100-mesh filter upstream of YF-S201.
