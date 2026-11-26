# DewLeaf Logger

`dewleaf_logger.py` captures CSV telemetry from `firmware/dewleaf_firmware`.

## Usage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r logger/requirements.txt
python logger/dewleaf_logger.py --port /dev/ttyACM0 --baud 115200 --out logs/dewleaf.csv
```

## Output Contract

The logger expects the firmware CSV header:

```csv
timestamp_ms,iso_time,night_id,state,action_id,air_temp_c,rh_pct,pressure_hpa,dew_point_c,spine_temp_c,soil_temp_c,soil_a_pct,soil_b_pct,bus_v,current_ma,power_mw,wh_total,flow_l_total,flow_l_window,peltier,fan,vib_a,vib_b,valve_flush,valve_drip
```

It flushes and fsyncs each row for long-run robustness. If serial disconnects, it retries every 5 seconds.
