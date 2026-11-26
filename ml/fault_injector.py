#!/usr/bin/env python3
"""Inject faults into telemetry CSV for software resilience testing."""
from __future__ import annotations
import argparse, csv, random
from pathlib import Path

FAULTS = ["spike_temp","rh_invalid","bus_sag","peltier_no_fan","flow_stuck","timestamp_regress","soil_diverge"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--rate', type=float, default=0.02)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--faults', default=','.join(FAULTS))
    args=ap.parse_args()
    rng=random.Random(args.seed)
    allowed=set(args.faults.split(','))
    with open(args.inp) as f: rows=list(csv.DictReader(f))
    for i,row in enumerate(rows):
        if rng.random()>args.rate: continue
        f=rng.choice([x for x in FAULTS if x in allowed])
        if f=='spike_temp': row['air_temp_c']='999'
        elif f=='rh_invalid': row['rh_pct']='150'
        elif f=='bus_sag': row['bus_v']='10.5'; row['peltier']='1'; row['fan']='1'
        elif f=='peltier_no_fan': row['peltier']='1'; row['fan']='0'
        elif f=='flow_stuck' and i>0: row['flow_l_total']=rows[i-1].get('flow_l_total',row['flow_l_total'])
        elif f=='timestamp_regress' and i>0: row['timestamp_ms']=str(int(float(rows[i-1]['timestamp_ms']))-1000)
        elif f=='soil_diverge': row['soil_a_pct']='90'; row['soil_b_pct']='20'
        row['injected_fault']=f
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fields=list(rows[0].keys())
    if 'injected_fault' not in fields: fields.append('injected_fault')
    with open(args.out,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f'wrote {args.out} rows={len(rows)} rate={args.rate}')

if __name__=='__main__': main()
