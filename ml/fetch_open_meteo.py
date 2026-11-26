#!/usr/bin/env python3
"""Fetch hourly weather data from Open-Meteo archive API for Kenyan counties.

Outputs per-county CSVs under ml/data/open_meteo/<county>.csv.
Free API, no key required. Be polite with request pacing.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Representative coordinates for Kenyan counties (capital/major town).
KENYA_COUNTIES = [
    {"county": "Nairobi", "lat": -1.286389, "lon": 36.817223},
    {"county": "Machakos", "lat": -1.517683, "lon": 37.263414},
    {"county": "Makueni", "lat": -1.8041, "lon": 37.6203},
    {"county": "Kitui", "lat": -1.3669, "lon": 38.0106},
    {"county": "Kajiado", "lat": -1.8524, "lon": 36.7768},
    {"county": "Kiambu", "lat": -1.1714, "lon": 36.8356},
    {"county": "Muranga", "lat": -0.7210, "lon": 37.1526},
    {"county": "Nyeri", "lat": -0.4201, "lon": 36.9476},
    {"county": "Kirinyaga", "lat": -0.4989, "lon": 37.2803},
    {"county": "Embu", "lat": -0.5388, "lon": 37.4596},
    {"county": "Meru", "lat": 0.0469, "lon": 37.6559},
    {"county": "Tharaka_Nithi", "lat": -0.3075, "lon": 37.7235},
    {"county": "Laikipia", "lat": 0.3606, "lon": 36.7820},
    {"county": "Nakuru", "lat": -0.3031, "lon": 36.0800},
    {"county": "Narok", "lat": -1.0875, "lon": 35.8711},
    {"county": "Baringo", "lat": 0.4919, "lon": 35.7412},
    {"county": "Uasin_Gishu", "lat": 0.5143, "lon": 35.2698},
    {"county": "Kericho", "lat": -0.3689, "lon": 35.2863},
    {"county": "Kisumu", "lat": -0.0917, "lon": 34.7680},
    {"county": "Homa_Bay", "lat": -0.5273, "lon": 34.4571},
    {"county": "Migori", "lat": -1.0634, "lon": 34.4731},
    {"county": "Kakamega", "lat": 0.2827, "lon": 34.7519},
    {"county": "Bungoma", "lat": 0.5635, "lon": 34.5606},
    {"county": "Trans_Nzoia", "lat": 1.0567, "lon": 34.9507},
    {"county": "Turkana", "lat": 3.1199, "lon": 35.5966},
    {"county": "West_Pokot", "lat": 1.6210, "lon": 35.3900},
    {"county": "Samburu", "lat": 1.2154, "lon": 36.9541},
    {"county": "Isiolo", "lat": 0.3546, "lon": 37.5822},
    {"county": "Marsabit", "lat": 2.3284, "lon": 37.9899},
    {"county": "Garissa", "lat": -0.4532, "lon": 39.6460},
    {"county": "Wajir", "lat": 1.7471, "lon": 40.0573},
    {"county": "Mandera", "lat": 3.9366, "lon": 41.8670},
    {"county": "Tana_River", "lat": -1.6519, "lon": 39.6510},
    {"county": "Lamu", "lat": -2.2717, "lon": 40.9020},
    {"county": "Kilifi", "lat": -3.6305, "lon": 39.8499},
    {"county": "Mombasa", "lat": -4.0435, "lon": 39.6682},
    {"county": "Kwale", "lat": -4.1816, "lon": 39.4606},
    {"county": "Taita_Taveta", "lat": -3.3161, "lon": 38.4850},
    {"county": "Nyandarua", "lat": -0.1804, "lon": 36.5230},
    {"county": "Bomet", "lat": -0.7813, "lon": 35.3416},
    {"county": "Vihiga", "lat": 0.0768, "lon": 34.7074},
    {"county": "Busia", "lat": 0.4608, "lon": 34.1115},
    {"county": "Siaya", "lat": 0.0612, "lon": 34.2881},
    {"county": "Kisii", "lat": -0.6817, "lon": 34.7667},
    {"county": "Nyamira", "lat": -0.5633, "lon": 34.9358},
    {"county": "Elgeyo_Marakwet", "lat": 0.8047, "lon": 35.5081},
    {"county": "Nandi", "lat": 0.1836, "lon": 35.1269},
]

HOURLY = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m",
    "pressure_msl", "wind_speed_10m", "cloud_cover",
    "shortwave_radiation", "direct_radiation", "diffuse_radiation",
    "precipitation", "et0_fao_evapotranspiration", "vapour_pressure_deficit",
    "soil_temperature_0cm", "soil_moisture_0_to_1cm",
]


def fetch_county(county: dict, start: str, end: str) -> dict:
    params = {
        "latitude": county["lat"],
        "longitude": county["lon"],
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(HOURLY),
        "timezone": "Africa/Nairobi",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "dewleaf-phase0/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_csv(payload: dict, county: dict, out_path: Path) -> int:
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["county", "latitude", "longitude", "time"] + HOURLY
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, t in enumerate(times):
            row = {
                "county": county["county"],
                "latitude": payload.get("latitude", county["lat"]),
                "longitude": payload.get("longitude", county["lon"]),
                "time": t,
            }
            for k in HOURLY:
                vals = hourly.get(k, [])
                row[k] = vals[i] if i < len(vals) else ""
            w.writerow(row)
    return len(times)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="ml/data/open_meteo")
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--sleep", type=float, default=1.0, help="Seconds between API calls")
    ap.add_argument("--counties", default="", help="Comma-separated county names; default all")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    selected = {c.strip().lower() for c in args.counties.split(",") if c.strip()}
    counties = [c for c in KENYA_COUNTIES if not selected or c["county"].lower() in selected]

    manifest = []
    for idx, county in enumerate(counties, 1):
        name = county["county"]
        out_path = out_dir / f"{name}.csv"
        try:
            payload = fetch_county(county, args.start, args.end)
            n = write_csv(payload, county, out_path)
            manifest.append({"county": name, "rows": n, "file": str(out_path), "status": "ok"})
            print(f"[{idx}/{len(counties)}] {name}: {n} rows", flush=True)
        except Exception as e:
            manifest.append({"county": name, "rows": 0, "file": str(out_path), "status": f"error:{e}"})
            print(f"[{idx}/{len(counties)}] {name}: ERROR {e}", flush=True)
        time.sleep(args.sleep)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"start": args.start, "end": args.end, "counties": manifest}, indent=2), encoding="utf-8")
    ok = sum(1 for m in manifest if m["status"] == "ok")
    total_rows = sum(m["rows"] for m in manifest)
    print(f"done: {ok}/{len(counties)} counties, {total_rows} rows, manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
