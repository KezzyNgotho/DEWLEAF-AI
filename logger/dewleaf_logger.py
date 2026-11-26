#!/usr/bin/env python3
"""DewLeaf Phase 0 serial/USB telemetry logger.

Captures CSV lines emitted by dewleaf_firmware.ino, persists them to disk,
and optionally forwards JSON summaries. Designed for 72h+ bench runs.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import serial

try:
    from ml.intelligence_engine import Context, decide
except Exception:
    Context = None
    decide = None


CSV_HEADER = [
    "timestamp_ms","iso_time","night_id","state","action_id","air_temp_c","rh_pct","pressure_hpa",
    "dew_point_c","spine_temp_c","soil_temp_c","soil_a_pct","soil_b_pct","bus_v","current_ma",
    "power_mw","wh_total","flow_l_total","flow_l_window","peltier","fan","vib_a","vib_b","valve_flush","valve_drip"
]


def ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def open_csv(path: str):
    ensure_parent(path)
    exists = os.path.exists(path) and os.path.getsize(path) > 0
    f = open(path, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if not exists:
        w.writerow(CSV_HEADER)
        f.flush()
    return f, w


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Log DewLeaf firmware CSV output")
    p.add_argument("--port", required=True, help="Serial port, e.g. /dev/ttyACM0")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--out", default="logs/dewleaf.csv")
    p.add_argument("--reconnect-s", type=float, default=5.0, help="Reconnect delay after serial failure")
    p.add_argument("--append-host-time", action="store_true", help="Prepend host timestamp column in a sidecar file")
    p.add_argument("--decision-out", default="", help="Optional JSONL file with intelligence engine decisions")
    p.add_argument("--api-url", default="", help="Optional POST endpoint for telemetry")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    f, writer = open_csv(args.out)
    sidecar = None
    if args.append_host_time:
        sidecar_path = args.out + ".hosttime.csv"
        ensure_parent(sidecar_path)
        sidecar = open(sidecar_path, "a", encoding="utf-8")

    print(f"[dewleaf-logger] writing {args.out}", flush=True)
    try:
        while True:
            try:
                with serial.Serial(args.port, args.baud, timeout=2) as ser:
                    print(f"[dewleaf-logger] connected {args.port}@{args.baud}", flush=True)
                    while True:
                        raw = ser.readline()
                        if not raw:
                            continue
                        line = raw.decode("utf-8", errors="ignore").strip()
                        if not line or line.startswith("{"):
                            continue
                        if line.startswith("timestamp_ms,iso_time"):
                            continue
                        parts = next(csv.reader([line]))
                        if len(parts) != len(CSV_HEADER):
                            print(f"[skip] bad column count {len(parts)}: {line}", file=sys.stderr, flush=True)
                            continue
                        writer.writerow(parts)
                        f.flush()
                        os.fsync(f.fileno())
                        row = dict(zip(CSV_HEADER, parts))
                        if args.decision_out and decide and Context:
                            try:
                                ctx = Context(
                                    air_c=float(row.get("air_temp_c", 20) or 20), rh_pct=float(row.get("rh_pct", 70) or 70),
                                    dew_point_c=float(row.get("dew_point_c", 15) or 15), spine_c=float(row.get("spine_temp_c", 18) or 18),
                                    soil_a_pct=float(row.get("soil_a_pct", 60) or 60), soil_b_pct=float(row.get("soil_b_pct", 60) or 60),
                                    bus_v=float(row.get("bus_v", 12.4) or 12.4), hour=dt.datetime.utcnow().hour,
                                    night_wh_used=float(row.get("wh_total", 0) or 0),
                                )
                                decision = decide(ctx)
                                Path(args.decision_out).parent.mkdir(parents=True, exist_ok=True)
                                with open(args.decision_out, "a", encoding="utf-8") as df:
                                    df.write(json.dumps({"row": row, "decision": decision}) + "\n")
                            except Exception as e:
                                print(f"[decision-skip] {e}", file=sys.stderr, flush=True)
                        if args.api_url:
                            try:
                                req = urllib.request.Request(args.api_url, data=json.dumps(row).encode(), headers={"Content-Type":"application/json"})
                                urllib.request.urlopen(req, timeout=2).read()
                            except Exception as e:
                                print(f"[api-skip] {e}", file=sys.stderr, flush=True)
                        if sidecar:
                            sidecar.write(f"{dt.datetime.utcnow().isoformat()}Z,{line}\n")
                            sidecar.flush()
                        print(line, flush=True)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"[dewleaf-logger] serial error: {e}; reconnecting in {args.reconnect_s}s", file=sys.stderr, flush=True)
                time.sleep(args.reconnect_s)
    except KeyboardInterrupt:
        print("\n[dewleaf-logger] stopped", flush=True)
    finally:
        f.close()
        if sidecar:
            sidecar.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
