#!/usr/bin/env python3
"""Generate a synthetic but physically plausible 14-night DewLeaf Phase 0 dataset.

Stdlib-only so it runs in minimal environments. Replace with real bench-rig
telemetry before making Phase 1 decisions.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from datetime import datetime, timedelta


ACTIONS = [
    {"action_id": 100, "name": "passive_only", "vib": 0, "peltier": 0, "shed_ms": 0},
    {"action_id": 200, "name": "nucleation_assist", "vib": 0, "peltier": 1, "shed_ms": 0},
    {"action_id": 300, "name": "shed_dual", "vib": 2, "peltier": 0, "shed_ms": 2500},
    {"action_id": 301, "name": "shed_single_explore", "vib": 1, "peltier": 0, "shed_ms": 2500},
    {"action_id": 302, "name": "shed_aggressive", "vib": 2, "peltier": 0, "shed_ms": 4000},
]

FIELDNAMES = [
    "timestamp_ms","iso_time","night_id","state","action_id","action_name","air_temp_c","rh_pct","pressure_hpa",
    "dew_point_c","spine_temp_c","soil_temp_c","soil_a_pct","soil_b_pct","bus_v","current_ma","power_mw","wh_total",
    "flow_l_total","flow_l_window","harvested_ml","wh_window","peltier","fan","vib_a","vib_b","valve_flush","valve_drip"
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def dew_point_c(temp_c: float, rh: float) -> float:
    a, b = 17.62, 243.12
    gamma = (a * temp_c) / (b + temp_c) + math.log(max(rh, 1e-3) / 100.0)
    return (b * gamma) / (a - gamma)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--nights", type=int, default=14)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    start = datetime(2026, 1, 1, 18, 0, 0)
    rows = []
    for n in range(args.nights):
        night_start = start + timedelta(days=n)
        night_id = f"night-{night_start:%Y%m%d}"
        base_temp = rng.gauss(16.0, 1.5)
        base_rh = clamp(rng.gauss(82.0, 6.0), 55, 98)
        canopy_eff = clamp(rng.gauss(1.0, 0.12), 0.7, 1.3)
        wind = clamp(rng.gauss(1.5, 0.8), 0, 5)
        wh_total = 0.0
        flow_l_total = 0.0
        for step in range(72):  # 12 hours, 10-min steps
            ts = night_start + timedelta(minutes=10 * step)
            hour = ts.hour + ts.minute / 60.0
            phase = min(max((hour - 18) % 24, 0), 12) / 12
            nocturnal_drop = 4.5 * math.sin(math.pi * phase)
            air_temp = base_temp - nocturnal_drop + rng.gauss(0, 0.2)
            rh = clamp(base_rh + nocturnal_drop * 1.8 + rng.gauss(0, 1.5), 40, 99)
            dp = dew_point_c(air_temp, rh)
            spine_temp = air_temp - rng.gauss(2.0, 0.4) - 0.2 * wind
            delta_t = air_temp - dp
            soil_a = clamp(58 + rng.gauss(0, 1.5) - step * 0.03, 45, 80)
            soil_b = clamp(soil_a + rng.gauss(0, 1.0), 45, 80)

            action = ACTIONS[rng.randrange(len(ACTIONS))]
            pre_dawn = 4 <= ts.hour < 7
            passive_window = ts.hour >= 20 or ts.hour < 6
            near_dp = delta_t <= 0.8

            condensation_ml = 0.0
            if passive_window:
                potential = max(0.0, (rh - 70) * 0.9 + (2.0 - abs(delta_t)) * 8.0)
                condensation_ml = potential * canopy_eff * (1.0 - 0.08 * wind)
            peltier_wh = 0.0
            if action["peltier"] and near_dp and spine_temp > 1.5:
                condensation_ml += 25.0 * canopy_eff
                peltier_wh = 1.8

            shed_eff = 0.35
            if pre_dawn:
                if action["vib"] == 1:
                    shed_eff = 0.72
                elif action["vib"] == 2:
                    shed_eff = 0.90 if action["shed_ms"] <= 3000 else 0.93
                shed_eff -= 0.03 * wind
            shed_eff = clamp(shed_eff, 0.2, 0.95)
            harvested_ml = max(0.0, condensation_ml * shed_eff + rng.gauss(0, 3.0))
            vib_wh = (0.6 if action["vib"] == 1 else 1.1 if action["vib"] == 2 else 0.0) if pre_dawn else 0.0
            wh_window = peltier_wh + vib_wh
            wh_total += wh_window
            flow_l_window = harvested_ml / 1000.0
            flow_l_total += flow_l_window

            rows.append({
                "timestamp_ms": int(ts.timestamp() * 1000),
                "iso_time": ts.isoformat(),
                "night_id": night_id,
                "state": "PRE_DAWN_SHEDDING" if pre_dawn else "PASSIVE_COOLING",
                "action_id": action["action_id"],
                "action_name": action["name"],
                "air_temp_c": round(air_temp, 2),
                "rh_pct": round(rh, 2),
                "pressure_hpa": round(1012 + rng.gauss(0, 2), 2),
                "dew_point_c": round(dp, 2),
                "spine_temp_c": round(spine_temp, 2),
                "soil_temp_c": round(air_temp - 1.5, 2),
                "soil_a_pct": round(soil_a, 2),
                "soil_b_pct": round(soil_b, 2),
                "bus_v": round(12.4 - rng.gauss(0, 0.05), 3),
                "current_ma": round(wh_window * 1000 / 12.0 / (10/60), 2) if wh_window > 0 else round(rng.gauss(90, 10), 2),
                "power_mw": round(wh_window * 1000 / (10/60), 2),
                "wh_total": round(wh_total, 6),
                "flow_l_total": round(flow_l_total, 4),
                "flow_l_window": round(flow_l_window, 4),
                "harvested_ml": round(harvested_ml, 2),
                "wh_window": round(wh_window, 4),
                "peltier": int(action["peltier"] and near_dp),
                "fan": int(action["peltier"] and near_dp),
                "vib_a": int(pre_dawn and action["vib"] >= 1),
                "vib_b": int(pre_dawn and action["vib"] >= 2),
                "valve_flush": 0,
                "valve_drip": 0,
            })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {args.out} rows={len(rows)} nights={args.nights}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
