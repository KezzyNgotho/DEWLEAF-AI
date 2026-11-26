#!/usr/bin/env python3
"""Simulate a 14-night bench run using Nairobi weather + physics model.

Produces a logger-compatible CSV (dewleaf_logger.py contract) for pipeline
validation and pre-deployment checks. NOT a substitute for real bench telemetry.
"""

from __future__ import annotations
import argparse, csv, math, random
from datetime import datetime, timedelta
from pathlib import Path

ACTIONS = [
    (100, "passive_only", 0, 0, 0),
    (200, "nucleation_assist", 0, 1, 0),
    (300, "shed_dual", 2, 0, 2500),
    (301, "shed_single_explore", 1, 0, 2500),
    (302, "shed_aggressive", 2, 0, 4000),
]

HEADER = ["timestamp_ms","iso_time","night_id","state","action_id","air_temp_c","rh_pct","pressure_hpa","dew_point_c","spine_temp_c","soil_temp_c","soil_a_pct","soil_b_pct","bus_v","current_ma","power_mw","wh_total","flow_l_total","flow_l_window","peltier","fan","vib_a","vib_b","valve_flush","valve_drip"]

def clamp(v,lo,hi): return max(lo,min(hi,v))
def dew_point(t,rh):
    a,b=17.62,243.12; g=(a*t)/(b+t)+math.log(max(rh,1e-3)/100)
    return (b*g)/(a-g)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True)
    ap.add_argument('--nights',type=int,default=14)
    ap.add_argument('--seed',type=int,default=11)
    ap.add_argument('--start',default='2026-11-01T18:00:00')
    args=ap.parse_args()
    rng=random.Random(args.seed)
    start=datetime.fromisoformat(args.start)
    rows=[]; flow_total=0.0; wh_total=0.0; pulses_total=0
    for n in range(args.nights):
        night_start=start+timedelta(days=n)
        nid=f"night-{night_start:%Y%m%d}"
        base_t=rng.gauss(17.0,1.2); base_rh=clamp(rng.gauss(82,7),55,98)
        cloud=rng.gauss(35,20); wind=rng.gauss(1.8,0.8)
        pinned=0.0
        for step in range(78): # 13h * 6 per hour
            ts=night_start+timedelta(minutes=10*step)
            hour=ts.hour
            phase=min(max(((hour+ts.minute/60)-18)%24,0),13)/13
            air=base_t-4.2*math.sin(math.pi*phase)+rng.gauss(0,.2)
            rh=clamp(base_rh+8*math.sin(math.pi*phase)+rng.gauss(0,1),40,99)
            dp=dew_point(air,rh); spine=air-(2.0+2.8*(1-cloud/100))+rng.gauss(0,.15)
            delta_t=air-dp
            pre_dawn = 4 <= hour < 7
            passive = hour>=20 or hour<6
            near_dp = delta_t<=0.8
            # action policy: biased but exploratory
            if pre_dawn and pinned>5: action=rng.choice(ACTIONS[2:5])
            elif passive and near_dp: action=rng.choice([ACTIONS[1],ACTIONS[0],ACTIONS[1]])
            elif pre_dawn: action=rng.choice([ACTIONS[2],ACTIONS[0]])
            else: action=ACTIONS[0]
            aid,_,vib,pelt,sm = action
            cond=0.0
            if passive:
                cond=max(0,(rh-65)*0.5+max(0,2.5-abs(delta_t))*5.0)*(1-cloud/120)*clamp(1-0.05*wind,0.2,1)
                if pelt and near_dp and spine>1.5: cond+=12.0; wh_window=0.33
                else: wh_window=0.0
            else: wh_window=0.0
            cond=max(0,cond+rng.gauss(0,.6)); pinned+=cond
            shed_eff=0.25; vib_wh=0.0
            if pre_dawn:
                shed_eff=0.72 if vib==1 else 0.92 if vib==2 else 0.25
                shed_eff=clamp(shed_eff-0.02*wind,0.2,0.96)
                vib_wh = 0.05 if vib==1 else 0.09 if vib==2 else 0.0
                harvested=pinned*shed_eff; pinned=max(0,pinned-harvested)
            else:
                harvested=0.0; pinned*=0.996
            wh_window+=vib_wh; wh_total+=wh_window
            flow_window=harvested/1000.0; flow_total+=flow_window
            soil_a=clamp(62+rng.gauss(0,1.2)-step*0.02,45,80)
            soil_b=clamp(soil_a+rng.gauss(0,0.8),45,80)
            state='PRE_DAWN_SHEDDING' if pre_dawn else 'PASSIVE_COOLING'
            rows.append({
                'timestamp_ms':int(ts.timestamp()*1000),'iso_time':ts.isoformat(),'night_id':nid,'state':state,
                'action_id':aid,'air_temp_c':round(air,2),'rh_pct':round(rh,2),'pressure_hpa':round(1012+rng.gauss(0,1.5),2),
                'dew_point_c':round(dp,2),'spine_temp_c':round(spine,2),'soil_temp_c':round(air-1.2,2),
                'soil_a_pct':round(soil_a,2),'soil_b_pct':round(soil_b,2),'bus_v':round(12.4+rng.gauss(0,.03),3),
                'current_ma':round(wh_window*6000/12.0,2) if wh_window>0 else round(85+rng.gauss(0,5),2),
                'power_mw':round(wh_window*6000,2),'wh_total':round(wh_total,6),'flow_l_total':round(flow_total,5),
                'flow_l_window':round(flow_window,5),'peltier':int(pelt and near_dp and passive),
                'fan':int(pelt and near_dp and passive),'vib_a':int(pre_dawn and vib>=1),'vib_b':int(pre_dawn and vib==2),
                'valve_flush':0,'valve_drip':0,
            })
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=HEADER); w.writeheader(); w.writerows(rows)
    print(f'wrote {args.out} rows={len(rows)} nights={args.nights}')

if __name__=='__main__': main()
