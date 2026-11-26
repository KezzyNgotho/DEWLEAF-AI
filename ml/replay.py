#!/usr/bin/env python3
"""Replay telemetry CSV through intelligence engine + runtime monitor.

Produces decision traces and fault events for deterministic software validation.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from ml.intelligence_engine import Context, decide
from ml.runtime_monitor import check_row, recommended_safe_action

def ffloat(v, d=0.0):
    try: return float(v)
    except: return d

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--limit', type=int, default=0)
    args=ap.parse_args()
    rows=[]
    with open(args.data) as f: r=list(csv.DictReader(f))
    if args.limit: r=r[:args.limit]
    prev=None; out=[]
    for row in r:
        faults=check_row(row, prev)
        safe=recommended_safe_action(faults)
        hour=0
        try:
            iso=row.get('iso_time','')
            hour=int(iso[11:13])+int(iso[14:16])/60 if len(iso)>=16 else 0
        except Exception: pass
        ctx=Context(
            air_c=ffloat(row.get('air_temp_c',20)), rh_pct=ffloat(row.get('rh_pct',70)),
            dew_point_c=ffloat(row.get('dew_point_c',15)), spine_c=ffloat(row.get('spine_temp_c',18)),
            soil_a_pct=ffloat(row.get('soil_a_pct',60)), soil_b_pct=ffloat(row.get('soil_b_pct',60)),
            bus_v=ffloat(row.get('bus_v',12.4)), hour=hour, night_wh_used=ffloat(row.get('wh_total',0)),
        )
        decision=decide(ctx, faults=faults, model_source=row.get('model_source','physics_heuristic_synthetic'))
        out.append({'iso_time':row.get('iso_time'),'night_id':row.get('night_id'),'action_id':row.get('action_id'),'faults':faults,'recommended_safe_action':safe,'decision':decision['selected'],'confidence':decision['confidence'],'safe_fallback':decision['safe_fallback'],'why':decision['why']})
        prev=row
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({'rows':len(out),'fault_count':sum(len(x['faults']) for x in out),'events':out}, indent=2))
    print(json.dumps({'rows':len(out),'fault_count':sum(len(x['faults']) for x in out),'out':args.out}))

if __name__=='__main__': main()
