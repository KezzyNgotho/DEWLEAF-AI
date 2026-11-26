#!/usr/bin/env python3
"""Runtime health/fault monitor for DewLeaf telemetry rows.

Emits structured fault events inspired by rover fault-protection patterns:
monitor -> detect -> classify -> recommend safe response.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class FaultEvent:
    code: str
    severity: str  # info|warn|critical
    message: str
    response: str
    value: Any = None

RANGES = {
    "air_temp_c": (-10, 60),
    "rh_pct": (0, 100),
    "dew_point_c": (-20, 40),
    "spine_temp_c": (-20, 80),
    "soil_a_pct": (0, 100),
    "soil_b_pct": (0, 100),
    "bus_v": (0, 20),
    "wh_total": (0, 1e6),
    "flow_l_total": (0, 1e9),
}

def _f(row, k, d=None):
    try:
        v = row.get(k, d)
        return float(v) if v not in ("", None) else d
    except Exception:
        return d

def recommended_safe_action(faults: list[dict]) -> dict:
    codes = {f.get("code") for f in faults}
    crit = {f.get("code") for f in faults if f.get("severity") == "critical"}
    if {"SAFETY_PELTIER_NO_FAN","SAFETY_FROST_GUARD","POWER_LOW_BUS","ENERGY_NIGHT_CAP"} & (codes|crit):
        return {"action_id": 100, "name": "passive_only", "reason": "critical_safety_or_power_fault"}
    if "SENSOR_SOIL_DIVERGENCE" in codes:
        return {"action_id": 100, "name": "passive_only", "reason": "sensor_disagreement"}
    return {"action_id": None, "name": "normal", "reason": "no_forced_fallback"}

def check_row(row: dict, prev: dict | None = None) -> list[dict]:
    faults: list[FaultEvent] = []
    for k,(lo,hi) in RANGES.items():
        v=_f(row,k)
        if v is None: continue
        if v<lo or v>hi:
            faults.append(FaultEvent(f"RANGE_{k.upper()}", "critical", f"{k} out of range", "flag_sensor_invalid", v))
    air=_f(row,'air_temp_c'); rh=_f(row,'rh_pct'); dp=_f(row,'dew_point_c'); spine=_f(row,'spine_temp_c')
    bus=_f(row,'bus_v'); wh=_f(row,'wh_total'); flow=_f(row,'flow_l_window'); pelt=_f(row,'peltier',0); fan=_f(row,'fan',0)
    soil_a=_f(row,'soil_a_pct'); soil_b=_f(row,'soil_b_pct')
    if air is not None and dp is not None and dp > air + 1.0:
        faults.append(FaultEvent("PHYSICS_DEWPOINT_GT_AIR", "warn", "dew point above air temp", "check_bme280_calibration", {"air":air,"dp":dp}))
    if rh is not None and (rh < 0 or rh > 100):
        faults.append(FaultEvent("PHYSICS_RH_INVALID", "critical", "RH invalid", "flag_sensor_invalid", rh))
    if pelt and not fan:
        faults.append(FaultEvent("SAFETY_PELTIER_NO_FAN", "critical", "Peltier on without fan", "force_fan_on_disable_peltier", {"peltier":pelt,"fan":fan}))
    if spine is not None and spine <= 1.5 and pelt:
        faults.append(FaultEvent("SAFETY_FROST_GUARD", "critical", "spine below frost guard while peltier active", "disable_peltier", spine))
    if bus is not None and bus < 11.2:
        faults.append(FaultEvent("POWER_LOW_BUS", "warn", "bus voltage low", "disable_high_load_actuators", bus))
    if wh is not None and wh > 25.0 and pelt:
        faults.append(FaultEvent("ENERGY_NIGHT_CAP", "warn", "night Wh cap exceeded with peltier active", "disable_peltier", wh))
    if soil_a is not None and soil_b is not None and abs(soil_a-soil_b) > 35:
        faults.append(FaultEvent("SENSOR_SOIL_DIVERGENCE", "warn", "soil probes diverge", "inspect_soil_probes", {"a":soil_a,"b":soil_b}))
    if prev:
        prev_flow=_f(prev,'flow_l_total'); cur_flow=_f(prev,'flow_l_total') if False else _f(row,'flow_l_total')
        if prev_flow is not None and cur_flow is not None and cur_flow < prev_flow - 0.001:
            faults.append(FaultEvent("FLOW_NON_MONOTONIC", "warn", "flow total decreased", "check_flow_sensor", {"prev":prev_flow,"cur":cur_flow}))
        prev_ts=_f(prev,'timestamp_ms'); cur_ts=_f(row,'timestamp_ms')
        if prev_ts is not None and cur_ts is not None and cur_ts <= prev_ts:
            faults.append(FaultEvent("TIME_NON_MONOTONIC", "warn", "timestamp not increasing", "check_rtc", {"prev":prev_ts,"cur":cur_ts}))
    return [asdict(f) for f in faults]
