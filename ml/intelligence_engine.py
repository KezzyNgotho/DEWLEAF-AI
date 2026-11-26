#!/usr/bin/env python3
"""DewLeaf Intelligence Engine - deep contextual reasoning over sensor/weather/policy state.

Not a black-box only: combines physics, safety constraints, learned reward model,
and explainable decision traces for edge/cloud use.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math

@dataclass
class Context:
    air_c: float; rh_pct: float; dew_point_c: float; spine_c: float
    soil_a_pct: float; soil_b_pct: float; wind_kmh: float = 0.0; cloud_pct: float = 50.0
    vpd_kpa: float = 0.0; bus_v: float = 12.4; hour: float = 0.0
    night_wh_used: float = 0.0; tank_l: float = 0.0

ACTIONS = [
    {"id":100,"name":"passive_only","peltier":0,"vib":0},
    {"id":200,"name":"nucleation_assist","peltier":1,"vib":0},
    {"id":201,"name":"nucleation_full","peltier":1,"vib":0},
    {"id":300,"name":"shed_dual","peltier":0,"vib":2},
    {"id":301,"name":"shed_single","peltier":0,"vib":1},
    {"id":302,"name":"shed_aggressive","peltier":0,"vib":2},
    {"id":310,"name":"shed_dual_nuc","peltier":1,"vib":2},
]

SAFETY = {
    "frost_guard_c": 1.5,
    "max_peltier_wh_night": 25.0,
    "min_bus_v": 11.2,
    "soil_target_min": 60.0,
    "soil_target_max": 72.0,
}

def clamp(v,lo,hi): return max(lo,min(hi,v))

def physics_features(c: Context) -> dict:
    delta_t = c.air_c - c.dew_point_c
    cloud_factor = 1.0 - clamp(c.cloud_pct,0,100)/100.0
    wind_pen = clamp(1.0 - 0.05*c.wind_kmh, 0.2, 1.0)
    predawn = 4 <= c.hour < 7
    passive = c.hour >= 20 or c.hour < 6
    near_dp = delta_t <= 0.8
    cond_potential = clamp((c.rh_pct-65)*0.4 + clamp(2.5-abs(delta_t),0,2.5)*4,0,30) * cloud_factor * wind_pen
    return {
        "delta_t":delta_t,"cloud_factor":cloud_factor,"wind_pen":wind_pen,
        "predawn":predawn,"passive":passive,"near_dp":near_dp,
        "cond_potential":cond_potential,"soil_mean":(c.soil_a_pct+c.soil_b_pct)/2,
    }

def safety_overrides(c: Context, action: dict, f: dict) -> tuple[dict,str|None]:
    a = dict(action); reason=None
    if c.spine_c <= SAFETY['frost_guard_c'] or c.bus_v < SAFETY['min_bus_v'] or c.night_wh_used >= SAFETY['max_peltier_wh_night']:
        if a['peltier']:
            a['peltier']=0; reason=reason or 'safety:peltier_blocked'
    if not f['predawn'] and a['vib']>0:
        a['vib']=0; reason=reason or 'safety:vib_only_predawn'
    return a, reason

def estimate_reward(c: Context, action: dict, f: dict, lam=5.0) -> dict:
    a,_ = safety_overrides(c,action,f)
    cond=f['cond_potential']; ml=0.0; wh=0.0
    peltier_ok = not (c.spine_c <= SAFETY['frost_guard_c'] or c.bus_v < SAFETY['min_bus_v'] or c.night_wh_used >= SAFETY['max_peltier_wh_night'])
    if a['id']==200 and f['near_dp'] and peltier_ok: ml=cond+8*f['cloud_factor']; wh=0.33
    elif a['id']==201 and f['near_dp'] and peltier_ok: ml=cond+12*f['cloud_factor']; wh=0.66
    elif a['id']==300 and f['predawn']: ml=cond*0.90; wh=0.09
    elif a['id']==301 and f['predawn']: ml=cond*0.72; wh=0.05
    elif a['id']==302 and f['predawn']: ml=cond*0.93; wh=0.12
    elif a['id']==310 and f['predawn']: ml=cond*0.92+(6*f['cloud_factor'] if peltier_ok else 0); wh=0.42 if peltier_ok else 0.09
    else: ml=cond*0.25; wh=0.0
    if not f['passive'] and not f['predawn']: ml*=0.1
    return {'action':a['name'],'action_id':a['id'],'pred_ml':ml,'pred_wh':wh,'reward':ml-lam*wh}

def assess_confidence(c: Context, f: dict, faults: list[dict] | None = None) -> dict:
    faults = faults or []
    score = 1.0
    reasons = []
    if c.wind_kmh == 0.0 and c.cloud_pct == 50.0:
        score -= 0.15; reasons.append("missing_or_default_weather_inputs")
    if c.spine_c is None or math.isnan(c.spine_c):
        score -= 0.2; reasons.append("missing_spine_temp")
    critical = [x for x in faults if x.get("severity") == "critical"]
    warns = [x for x in faults if x.get("severity") == "warn"]
    score -= min(0.6, 0.35 * len(critical))
    score -= min(0.2, 0.05 * len(warns))
    if critical: reasons.append("critical_faults_present")
    if c.bus_v < 11.5:
        score -= 0.1; reasons.append("low_bus_voltage")
    score = clamp(score, 0.0, 1.0)
    label = "high" if score >= 0.8 else "medium" if score >= 0.55 else "low"
    return {"score": round(score,3), "label": label, "reasons": reasons, "fault_count": len(faults)}

def decide(c: Context, lam=5.0, faults: list[dict] | None = None, model_source: str = "physics_heuristic_synthetic") -> dict:
    f=physics_features(c)
    scored=[estimate_reward(c,a,f,lam) for a in ACTIONS]
    for s in scored:
        # Penalize risky actions when confidence is low
        pass
    scored.sort(key=lambda x:x['reward'], reverse=True)
    best=scored[0]
    conf = assess_confidence(c, f, faults)
    if conf['label'] in ('low','medium') and best['action_id'] in (201,302,310):
        # degrade to safer action
        for s in scored:
            if s['action_id'] in (100,200,301,300):
                best = s; break
    soil=f['soil_mean']
    irrigation='none'
    if not f['passive'] and not f['predawn']:
        if soil < SAFETY['soil_target_min']: irrigation='micro_dose'
        elif soil > SAFETY['soil_target_max']: irrigation='hold'
    risks=[]
    if model_source != "measured_calibrated":
        risks.append("model_not_calibrated_on_real_bench_telemetry")
    if f['cond_potential'] < 2: risks.append("low_condensation_potential")
    if c.bus_v < SAFETY['min_bus_v']: risks.append("low_bus_voltage")
    if c.spine_c <= SAFETY['frost_guard_c'] + 0.5: risks.append("near_frost_guard")
    explanation={
        'inputs':asdict(c),'features':f,'selected':best,'top3':scored[:3],
        'irrigation':irrigation,
        'confidence':conf,
        'model_source':model_source,
        'assumptions':['physics_informed_reward','no_measured_yield_feedback_loop','single_node_local_sensors'],
        'risks':risks,
        'safe_fallback':{'action_id':100,'name':'passive_only','reason':'default_safe_state'},
        'why':[
            f"delta_t={f['delta_t']:.2f}C near_dp={f['near_dp']} predawn={f['predawn']} passive={f['passive']}",
            f"cond_potential={f['cond_potential']:.2f} cloud_factor={f['cloud_factor']:.2f} wind_pen={f['wind_pen']:.2f}",
            f"best={best['action']} reward={best['reward']:.2f} pred_ml={best['pred_ml']:.2f} pred_wh={best['pred_wh']:.3f}",
            f"soil_mean={soil:.1f}% irrigation={irrigation} confidence={conf['label']}",
        ],
    }
    return explanation

if __name__=='__main__':
    ctx=Context(air_c=14.2,rh_pct=92,dew_point_c=13.1,spine_c=11.8,soil_a_pct=61,soil_b_pct=63,wind_kmh=3.2,cloud_pct=20,hour=5.5)
    import json; print(json.dumps(decide(ctx), indent=2))
