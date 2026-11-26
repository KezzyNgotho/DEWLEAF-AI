#!/usr/bin/env python3
"""Calibrate edge policy from real bench telemetry.

Uses measured logs to compute per-action empirical rewards and writes a calibrated
header + report metadata. This is the real-data bridge before field deployment.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--out-header', default='models/dewleaf_policy_calibrated.h')
    ap.add_argument('--out-report', default='ml/artifacts/calibration_report.json')
    ap.add_argument('--lambda-wh', type=float, default=5.0)
    args=ap.parse_args()
    df=pd.read_csv(args.data)
    if 'harvested_ml' not in df.columns and 'flow_l_window' in df.columns:
        df['harvested_ml']=df['flow_l_window'].astype(float)*1000.0
    if 'wh_window' not in df.columns and 'power_mw' in df.columns:
        df['wh_window']=df['power_mw'].astype(float)/1000.0*(10/60)
    if 'action_name' not in df.columns and 'action_id' in df.columns:
        mapping={100:'passive_only',200:'nucleation_assist',201:'nucleation_full',300:'shed_dual',301:'shed_single_explore',302:'shed_aggressive',310:'shed_dual_nucleation'}
        df['action_name']=df['action_id'].map(mapping).fillna('unknown')
    required={'night_id','action_name','harvested_ml','wh_window'}
    miss=required-set(df.columns)
    if miss: raise SystemExit(f'missing columns: {sorted(miss)}')
    df['reward']=df['harvested_ml']-args.lambda_wh*df['wh_window']
    by=df.groupby('action_name')['reward'].agg(['mean','count']).reset_index()
    baseline=float(by.loc[by['action_name']=='passive_only','mean'].iloc[0]) if (by['action_name']=='passive_only').any() else 0.0
    action_ids={"passive_only":100,"nucleation_assist":200,"nucleation_full":201,"shed_dual":300,"shed_single_explore":301,"shed_aggressive":302,"shed_dual_nucleation":310}
    lines=['#pragma once','#include <stdint.h>','',f'// Calibrated from measured bench data: {args.data}','struct DewLeafActionScore { uint16_t action_id; float reward_bias; };',f'static const float DEWLEAF_LAMBDA_WH = {args.lambda_wh}f;',f'static const uint8_t DEWLEAF_ACTION_COUNT = {len(by)};','static const DewLeafActionScore DEWLEAF_ACTION_SCORES[] = {']
    for _,r in by.iterrows():
        a=r['action_name']; aid=action_ids.get(a,0); bias=float(r['mean']-baseline)
        lines.append(f'  {{ {aid}, {bias:.4f}f }}, // {a} n={int(r["count"])} mean={r["mean"]:.3f}')
    lines+=['};','','static inline uint16_t dewleaf_select_action(uint16_t fallback_action_id){','  uint16_t best=fallback_action_id; float best_bias=-1e9f;','  for(uint8_t i=0;i<DEWLEAF_ACTION_COUNT;i++){ if(DEWLEAF_ACTION_SCORES[i].reward_bias>best_bias){best_bias=DEWLEAF_ACTION_SCORES[i].reward_bias; best=DEWLEAF_ACTION_SCORES[i].action_id;} }','  return best;','}','']
    Path(args.out_header).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_header).write_text('\n'.join(lines))
    report={'data':args.data,'rows':int(len(df)),'nights':int(df['night_id'].nunique()),'lambda_wh':args.lambda_wh,'label_source':'measured_bench_calibration','actions':by.to_dict(orient='records')}
    Path(args.out_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_report).write_text(json.dumps(report,indent=2))
    print(json.dumps({'rows':len(df),'nights':df['night_id'].nunique(),'out_header':args.out_header,'out_report':args.out_report}))

if __name__=='__main__': main()
