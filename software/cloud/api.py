#!/usr/bin/env python3
"""Minimal DewLeaf cloud API scaffold: ingest telemetry and return policy decision."""
from __future__ import annotations
import csv, json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ml.intelligence_engine import Context, decide
try:
    from software.cloud.auth import check_auth, audit
except Exception:
    from auth import check_auth, audit

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "logs" / "cloud_telemetry.csv"
FIELDS = ["timestamp_ms","iso_time","night_id","state","action_id","air_temp_c","rh_pct","dew_point_c","spine_temp_c","soil_a_pct","soil_b_pct","bus_v","wh_total","flow_l_total","flow_l_window"]

def append_row(row: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    exists = LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists: w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not check_auth(self.headers):
            audit('auth_fail', {'path': self.path})
            return self._send(401, {"error":"unauthorized"})
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode() or "{}")
        except Exception:
            return self._send(400, {"error":"invalid json"})
        if path == "/api/telemetry":
            append_row(data)
            return self._send(200, {"ok": True})
        if path == "/api/decide":
            ctx = Context(
                air_c=float(data.get("air_temp_c", 20)), rh_pct=float(data.get("rh_pct", 70)),
                dew_point_c=float(data.get("dew_point_c", 15)), spine_c=float(data.get("spine_temp_c", 18)),
                soil_a_pct=float(data.get("soil_a_pct", 60)), soil_b_pct=float(data.get("soil_b_pct", 60)),
                wind_kmh=float(data.get("wind_kmh", 0)), cloud_pct=float(data.get("cloud_pct", 50)),
                vpd_kpa=float(data.get("vpd_kpa", 0)), bus_v=float(data.get("bus_v", 12.4)),
                hour=float(data.get("hour", 0)), night_wh_used=float(data.get("night_wh_used", 0)),
                tank_l=float(data.get("tank_l", 0)),
            )
            return self._send(200, decide(ctx, lam=float(data.get("lambda", 5.0))))
        return self._send(404, {"error":"not found"})

    def do_GET(self):
        if urlparse(self.path).path == "/health":
            return self._send(200, {"ok": True})
        return self._send(404, {"error":"not found"})

def main():
    port = int(os.environ.get("PORT", "8080"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

if __name__ == "__main__":
    main()
