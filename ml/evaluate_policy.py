#!/usr/bin/env python3
"""Evaluate DewLeaf policy on logged/sim CSV with night-grouped metrics."""
from __future__ import annotations
import argparse, json
import numpy as np, pandas as pd, joblib
from pathlib import Path

def add_features(df):
    out=df.copy(); out['iso_time']=pd.to_datetime(out['iso_time'])
    hour=out['iso_time'].dt.hour+out['iso_time'].dt.minute/60.0
    out['hour_sin']=np.sin(2*np.pi*hour/24.0); out['hour_cos']=np.cos(2*np.pi*hour/24.0)
    out['is_predawn']=((out['iso_time'].dt.hour>=4)&(out['iso_time'].dt.hour<7)).astype(int)
    out['delta_t']=out['air_temp_c']-out['dew_point_c']
    for col, default in [("wind_speed_kmh",0.0),("cloud_cover_pct",50.0),("vpd_kpa",0.0),("et0_mm",0.0),("pressure_hpa",1012.0),("spine_temp_c",out['air_temp_c']-2),("soil_a_pct",60.0),("soil_b_pct",60.0),("bus_v",12.4)]:
        if col not in out: out[col]=default
        out[col]=pd.to_numeric(out[col],errors='coerce').fillna(default)
    out['rh_x_cloud']=out['rh_pct']*(1.0-out['cloud_cover_pct']/100.0)
    out['delta_t_x_wind']=out['delta_t']*out['wind_speed_kmh']
    out['soil_mean']=(pd.to_numeric(out['soil_a_pct'],errors='coerce')+pd.to_numeric(out['soil_b_pct'],errors='coerce'))/2.0
    out['dew_margin']=2.5-out['delta_t'].abs()
    if 'harvested_ml' not in out and 'flow_l_window' in out: out['harvested_ml']=pd.to_numeric(out['flow_l_window'],errors='coerce').fillna(0)*1000
    if 'wh_window' not in out and 'power_mw' in out: out['wh_window']=pd.to_numeric(out['power_mw'],errors='coerce').fillna(0)/1000*(10/60)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',required=True); ap.add_argument('--model',required=True)
    ap.add_argument('--lambda-wh',type=float,default=5.0); ap.add_argument('--baseline-action',default='passive_only')
    ap.add_argument('--out',default='')
    args=ap.parse_args()
    m=joblib.load(args.model); df=add_features(pd.read_csv(args.data))
    feats=m['features']+m['cat_features']
    if 'action_name' not in df and 'action_id' in df:
        mapping={100:'passive_only',200:'nucleation_assist',201:'nucleation_full',300:'shed_dual',301:'shed_single_explore',302:'shed_aggressive',310:'shed_dual_nucleation'}
        df['action_name']=df['action_id'].map(mapping).fillna('passive_only')
    actions=sorted(df['action_name'].dropna().unique()) if 'action_name' in df else ['passive_only']
    if 'action_name' not in df: df['action_name']=args.baseline_action
    base=df.copy(); base['action_name']=args.baseline_action
    base_r=m['ml'].predict(base[feats])-args.lambda_wh*m['wh'].predict(base[feats])
    ctx=df.loc[df.index.repeat(len(actions)),feats].copy(); ctx['action_name']=np.tile(actions,len(df))
    pred=m['ml'].predict(ctx[feats])-args.lambda_wh*m['wh'].predict(ctx[feats])
    pred=pred.reshape(len(df),len(actions)); best=pred.max(axis=1)
    report={
        'rows':int(len(df)),'nights':int(df['night_id'].nunique()) if 'night_id' in df else None,
        'baseline_reward_mean':float(np.mean(base_r)),'policy_reward_mean':float(np.mean(best)),
        'improvement_pct':float((np.mean(best)-np.mean(base_r))/abs(np.mean(base_r)+1e-9)*100),
        'actual_reward_mean':float(np.mean(df['harvested_ml']-args.lambda_wh*df['wh_window'])) if 'harvested_ml' in df and 'wh_window' in df else None,
    }
    if 'night_id' in df:
        g=df.assign(base_r=base_r,best_r=best)
        by=g.groupby('night_id').agg(base=('base_r','mean'),best=('best_r','mean'))
        by['imp_pct']=(by['best']-by['base'])/by['base'].abs().replace(0,np.nan)*100
        report['night_improvement_pct_mean']=float(by['imp_pct'].mean())
        report['night_improvement_pct_median']=float(by['imp_pct'].median())
    print(json.dumps(report,indent=2))
    if args.out: Path(args.out).write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__': main()
