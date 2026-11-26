"""Independent action guard - final safety authority before actuation."""
from __future__ import annotations

SAFE = 100
ALLOWED = {100,200,201,300,301,302,310,400,500}

def guard_action(action_id: int, *, peltier_allowed: bool, fan_on: bool, predawn: bool, night: bool, bus_v: float, spine_c: float) -> tuple[int,str]:
    if action_id not in ALLOWED: return SAFE, 'unknown_action'
    if action_id in (200,201,310) and (not peltier_allowed or spine_c <= 1.5 or bus_v < 11.2): return SAFE, 'peltier_blocked'
    if action_id in (200,201,310) and not fan_on: return SAFE, 'fan_required'
    if action_id in (300,301,302,310) and not predawn: return SAFE, 'shedding_only_predawn'
    if action_id in (200,201) and not night: return SAFE, 'nucleation_only_night'
    return action_id, 'ok'
