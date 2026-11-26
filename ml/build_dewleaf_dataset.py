#!/usr/bin/env python3
"""Build DewLeaf training dataset from Open-Meteo county weather CSVs.

Expands hourly weather to 10-min night windows, simulates physics-informed
dew formation/shedding/energy, and emits rows compatible with train_dewleaf_policy.py.

Labels are physics-informed estimates (not measured dew). Real bench telemetry
must replace/supplement before Phase 1 sign-off.
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

ACTIONS = [
    {"action_id": 100, "name": "passive_only", "vib": 0, "peltier": 0, "shed_ms": 0, "duty": 0.0},
    {"action_id": 200, "name": "nucleation_assist", "vib": 0, "peltier": 1, "shed_ms": 0, "duty": 0.5},
    {"action_id": 201, "name": "nucleation_full", "vib": 0, "peltier": 1, "shed_ms": 0, "duty": 1.0},
    {"action_id": 300, "name": "shed_dual", "vib": 2, "peltier": 0, "shed_ms": 2500, "duty": 0.0},
    {"action_id": 301, "name": "shed_single_explore", "vib": 1, "peltier": 0, "shed_ms": 2500, "duty": 0.0},
    {"action_id": 302, "name": "shed_aggressive", "vib": 2, "peltier": 0, "shed_ms": 4000, "duty": 0.0},
    {"action_id": 310, "name": "shed_dual_nucleation", "vib": 2, "peltier": 1, "shed_ms": 2500, "duty": 0.5},
]

OUT_FIELDS = [
    "timestamp_ms","iso_time","night_id","county","state","action_id","action_name",
    "air_temp_c","rh_pct","pressure_hpa","dew_point_c","spine_temp_c","soil_temp_c",
    "soil_a_pct","soil_b_pct","bus_v","current_ma","power_mw","wh_total","flow_l_total",
    "flow_l_window","harvested_ml","wh_window","peltier","fan","vib_a","vib_b",
    "valve_flush","valve_drip","wind_speed_kmh","cloud_cover_pct","shortwave_wm2",
    "et0_mm","vpd_kpa","label_source","condensation_ml","pinned_ml","shed_eff","delta_t"
]


def ffloat(v, default=float("nan")):
    try:
        if v is None or v == "": return default
        return float(v)
    except Exception:
        return default


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def parse_time(s: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def night_id_for(ts: datetime, county: str) -> str:
    d = ts.date()
    if ts.hour < 12:
        d = (ts - timedelta(days=1)).date()
    return f"night-{county}-{d:%Y%m%d}"


def is_night_window(ts: datetime) -> bool:
    return ts.hour >= 18 or ts.hour < 7


def lerp(a, b, t):
    return a + (b - a) * t


def interp_hourly(rows: list[dict], key: str, i: int, frac: float, default=float("nan")):
    a = ffloat(rows[i].get(key), default)
    b = ffloat(rows[min(i + 1, len(rows) - 1)].get(key), a)
    if math.isnan(a) and math.isnan(b): return default
    if math.isnan(a): return b
    if math.isnan(b): return a
    return lerp(a, b, frac)


def choose_action(rng: random.Random, ts: datetime, delta_t: float, rh: float, pinned_ml: float) -> dict:
    pre_dawn = 4 <= ts.hour < 7
    passive_window = ts.hour >= 20 or ts.hour < 6
    near_dp = delta_t <= 1.2
    # Epsilon-greedy with physics-biased exploration for causal signal
    if rng.random() < 0.25:
        return ACTIONS[rng.randrange(len(ACTIONS))]
    if pre_dawn and pinned_ml > 5:
        return rng.choice([ACTIONS[3], ACTIONS[5], ACTIONS[6], ACTIONS[4]])
    if passive_window and near_dp:
        return rng.choice([ACTIONS[1], ACTIONS[2], ACTIONS[0], ACTIONS[6]])
    if pre_dawn:
        return rng.choice([ACTIONS[3], ACTIONS[0], ACTIONS[4]])
    return ACTIONS[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-glob", default="ml/data/open_meteo/*/*.csv")
    ap.add_argument("--out", default="ml/data/dewleaf_kenya_weather.csv")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-files", type=int, default=0)
    ap.add_argument("--step-min", type=int, default=10)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    files = sorted(glob.glob(args.input_glob))
    files = [f for f in files if not f.endswith("manifest.json")]
    files = [f for f in files if f.endswith(".csv") or f.endswith(".csv.gz")]
    if args.max_files:
        files = files[:args.max_files]
    if not files:
        raise SystemExit(f"No files matched {args.input_glob}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    total = 0
    nights = set()
    with open(args.out, "w", newline="", encoding="utf-8") as out_f:
        w = csv.DictWriter(out_f, fieldnames=OUT_FIELDS)
        w.writeheader()
        for fp in files:
            import gzip
            op = gzip.open if fp.endswith(".gz") else open
            with op(fp, "rt", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            if not rows:
                continue
            # sort by time
            rows.sort(key=lambda r: r.get("time", ""))
            county = rows[0].get("county") or Path(fp).stem
            pinned_ml = 0.0
            wh_total = 0.0
            flow_l_total = 0.0
            current_night = None
            for i in range(len(rows) - 1):
                t0 = parse_time(rows[i].get("time", ""))
                t1 = parse_time(rows[i + 1].get("time", ""))
                if t0 is None or t1 is None:
                    continue
                # expand hour into step-min intervals
                steps = max(1, int((t1 - t0).total_seconds() / (args.step_min * 60)))
                for s in range(steps):
                    frac = s / steps
                    ts = t0 + timedelta(minutes=s * args.step_min)
                    if not is_night_window(ts):
                        pinned_ml *= 0.7  # daytime evaporation
                        continue
                    nid = night_id_for(ts, county)
                    if nid != current_night:
                        current_night = nid
                        pinned_ml = 0.0
                        wh_total = 0.0
                        flow_l_total = 0.0
                    nights.add(nid)

                    air = interp_hourly(rows, "temperature_2m", i, frac)
                    rh = interp_hourly(rows, "relative_humidity_2m", i, frac)
                    dp = interp_hourly(rows, "dew_point_2m", i, frac)
                    pressure = interp_hourly(rows, "pressure_msl", i, frac)
                    wind = interp_hourly(rows, "wind_speed_10m", i, frac, 0.0)
                    cloud = interp_hourly(rows, "cloud_cover", i, frac, 50.0)
                    sw = interp_hourly(rows, "shortwave_radiation", i, frac, 0.0)
                    et0 = interp_hourly(rows, "et0_fao_evapotranspiration", i, frac, 0.0)
                    vpd = interp_hourly(rows, "vapour_pressure_deficit", i, frac, 0.0)
                    soil_t = interp_hourly(rows, "soil_temperature_0cm", i, frac, air - 1.5)
                    soil_m = interp_hourly(rows, "soil_moisture_0_to_1cm", i, frac, 0.2)
                    if any(math.isnan(x) for x in [air, rh, dp]):
                        continue

                    delta_t = air - dp
                    cloud_factor = clamp(1.0 - cloud / 100.0, 0.05, 1.0)
                    wind_penalty = clamp(1.0 - 0.06 * wind, 0.15, 1.0)
                    sky_cooling = 2.0 + 3.5 * cloud_factor
                    spine_temp = air - sky_cooling + rng.gauss(0, 0.15)
                    pre_dawn = 4 <= ts.hour < 7
                    passive_window = ts.hour >= 20 or ts.hour < 6
                    near_dp = delta_t <= 0.8

                    action = choose_action(rng, ts, delta_t, rh, pinned_ml)

                    # Condensation model: depends on RH, deltaT, sky, wind, spine temp.
                    condensation_ml = 0.0
                    if passive_window:
                        dp_margin = clamp(2.5 - abs(delta_t), 0, 2.5)
                        rh_margin = clamp((rh - 60) / 40.0, 0, 1)
                        base = 18.0 * rh_margin * (0.3 + 0.7 * dp_margin / 2.5)
                        condensation_ml = base * cloud_factor * wind_penalty
                        if spine_temp <= dp:
                            condensation_ml += 4.0 * cloud_factor
                    # Nucleation assist: effective only when near dew point and spine cold enough
                    peltier_wh = 0.0
                    if action["peltier"] and near_dp and spine_temp > 1.5 and passive_window:
                        duty = float(action.get("duty", 0.5))
                        boost = 10.0 * duty * cloud_factor * clamp(1.0 - delta_t / 1.5, 0, 1)
                        condensation_ml += boost
                        peltier_wh = 20.0 * duty * (args.step_min / 60.0) / 5.0  # scaled Wh for 10-min window
                    condensation_ml = max(0.0, condensation_ml + rng.gauss(0, 0.8))
                    pinned_ml += condensation_ml

                    # Shedding: only effective in pre-dawn and when there are pinned droplets
                    shed_eff = 0.25  # natural/minimal shedding
                    vib_wh = 0.0
                    if pre_dawn:
                        if action["vib"] == 1:
                            shed_eff = 0.68
                            vib_wh = 1.2 * (args.step_min / 60.0) / 2.0
                        elif action["vib"] == 2:
                            shed_eff = 0.90 if action["shed_ms"] <= 3000 else 0.94
                            vib_wh = 2.0 * (args.step_min / 60.0) / 2.0
                        shed_eff -= 0.02 * wind
                        shed_eff = clamp(shed_eff, 0.2, 0.96)
                    harvested_ml = pinned_ml * shed_eff if pre_dawn else 0.0
                    if pre_dawn:
                        pinned_ml = max(0.0, pinned_ml - harvested_ml)
                    # small evaporation loss during night if not shed
                    if not pre_dawn:
                        pinned_ml *= 0.995

                    wh_window = peltier_wh + vib_wh
                    wh_total += wh_window
                    flow_l_window = harvested_ml / 1000.0
                    flow_l_total += flow_l_window

                    soil_a = clamp(55 + (soil_m * 100 if not math.isnan(soil_m) else 8) + rng.gauss(0, 1.0), 35, 90)
                    soil_b = clamp(soil_a + rng.gauss(0, 0.8), 35, 90)

                    out = {
                        "timestamp_ms": int(ts.timestamp() * 1000),
                        "iso_time": ts.isoformat(),
                        "night_id": nid,
                        "county": county,
                        "state": "PRE_DAWN_SHEDDING" if pre_dawn else "PASSIVE_COOLING",
                        "action_id": action["action_id"],
                        "action_name": action["name"],
                        "air_temp_c": round(air, 3),
                        "rh_pct": round(rh, 3),
                        "pressure_hpa": round(pressure, 3) if not math.isnan(pressure) else "",
                        "dew_point_c": round(dp, 3),
                        "spine_temp_c": round(spine_temp, 3),
                        "soil_temp_c": round(soil_t, 3) if not math.isnan(soil_t) else "",
                        "soil_a_pct": round(soil_a, 3),
                        "soil_b_pct": round(soil_b, 3),
                        "bus_v": round(12.4 + rng.gauss(0, 0.03), 3),
                        "current_ma": round(wh_window * 1000 / 12.0 / (args.step_min / 60.0), 2) if wh_window > 0 else round(80 + rng.gauss(0, 5), 2),
                        "power_mw": round(wh_window * 1000 / (args.step_min / 60.0), 2),
                        "wh_total": round(wh_total, 6),
                        "flow_l_total": round(flow_l_total, 6),
                        "flow_l_window": round(flow_l_window, 6),
                        "harvested_ml": round(harvested_ml, 3),
                        "wh_window": round(wh_window, 5),
                        "peltier": int(action["peltier"] and near_dp and passive_window),
                        "fan": int(action["peltier"] and near_dp and passive_window),
                        "vib_a": int(pre_dawn and action["vib"] >= 1),
                        "vib_b": int(pre_dawn and action["vib"] >= 2),
                        "valve_flush": 0,
                        "valve_drip": 0,
                        "wind_speed_kmh": round(wind, 3),
                        "cloud_cover_pct": round(cloud, 3) if not math.isnan(cloud) else "",
                        "shortwave_wm2": round(sw, 3) if not math.isnan(sw) else "",
                        "et0_mm": round(et0, 4) if not math.isnan(et0) else "",
                        "vpd_kpa": round(vpd, 4) if not math.isnan(vpd) else "",
                        "label_source": "physics_informed_open_meteo_v2",
                        "condensation_ml": round(condensation_ml, 3),
                        "pinned_ml": round(pinned_ml, 3),
                        "shed_eff": round(shed_eff, 4),
                        "delta_t": round(delta_t, 3),
                    }
                    w.writerow(out)
                    total += 1

    print(f"wrote {args.out} rows={total} nights={len(nights)} files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
