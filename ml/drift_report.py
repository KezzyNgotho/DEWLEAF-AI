#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
import pandas as pd
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--baseline',required=True); ap.add_argument('--current',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args()
    b=pd.read_csv(a.baseline); c=pd.read_csv(a.current)
    cols=[x for x in ['air_temp_c','rh_pct','dew_point_c','spine_temp_c','soil_a_pct','bus_v','flow_l_window'] if x in b.columns and x in c.columns]
    drift={}
    for col in cols:
        bm, cm=b[col].astype(float).mean(), c[col].astype(float).mean()
        bs, cs=b[col].astype(float).std(ddof=0)+1e-9, c[col].astype(float).std(ddof=0)+1e-9
        drift[col]={'baseline_mean':float(bm),'current_mean':float(cm),'mean_delta':float(cm-bm),'std_delta':float(cs-bs)}
    report={'baseline':a.baseline,'current':a.current,'rows_baseline':len(b),'rows_current':len(c),'drift':drift}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(json.dumps(report,indent=2))
    print(json.dumps({'cols':len(cols),'out':a.out}))

if __name__=='__main__': main()
