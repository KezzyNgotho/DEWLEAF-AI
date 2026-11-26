#!/usr/bin/env python3
"""Software demo: simulate one Nairobi night with DewLeaf smart policy vs baseline."""
from __future__ import annotations
import argparse, csv, math, random, json
from datetime import datetime, timedelta
from pathlib import Path

ACTIONS = [
    {"id":100,"name":"passive_only","peltier":0,"vib":0},
    {"id":200,"name":"nucleation_assist","peltier":1,"vib":0},
    {"id":201,"name":"nucleation_full","peltier":1,"vib":0},
    {"id":300,"name":"shed_dual","peltier":0,"vib":2},
    {"id":301,"name":"shed_single","peltier":0,"vib":1},
    {"id":302,"name":"shed_aggressive","peltier":0,"vib":2},
    {"id":310,"name":"shed_dual_nuc","peltier":1,"vib":2},
]

def clamp(v,lo,hi): return max(lo,min(hi,v))
def ffloat(v,d=math.nan):
    try: return float(v)
    except: return d

def parse_time(s):
    for fmt in ("%Y-%m-%dT%H:%M","%Y-%m-%d %H:%M:%S"):
        try: return datetime.strptime(s,fmt)
        except: pass
    return None

def heuristic_action(ctx, fallback=100):
    delta_t=ctx['air']-ctx['dp']; near_dp=delta_t<=0.8; predawn=4<=ctx['hour']<7
    cloud_factor=1-clamp(ctx['cloud'],0,100)/100; wind_pen=clamp(1-0.05*ctx['wind'],0.2,1)
    cond=clamp((ctx['rh']-65)*0.4+clamp(2.5-abs(delta_t),0,2.5)*4,0,30)*cloud_factor*wind_pen
    best=fallback; best_r=-1e9
    for a in ACTIONS:
        ml=0; wh=0
        if a['id']==200 and near_dp: ml=cond+8*cloud_factor; wh=0.33
        elif a['id']==201 and near_dp: ml=cond+12*cloud_factor; wh=0.66
        elif a['id']==300 and predawn: ml=cond*0.90; wh=0.09
        elif a['id']==301 and predawn: ml=cond*0.72; wh=0.05
        elif a['id']==302 and predawn: ml=cond*0.93; wh=0.12
        elif a['id']==310 and predawn: ml=cond*0.92+6*cloud_factor; wh=0.42
        else: ml=cond*0.25; wh=0
        r=ml-5*wh
        if r>best_r: best_r=r; best=a['id']
    return best

def sim_night(rows, policy='smart', seed=7):
    rng=random.Random(seed)
    pinned=0.0; wh_total=0.0; ml_total=0.0; timeline=[]
    for r in rows:
        ts=parse_time(r['time']);
        if not ts: continue
        hour=ts.hour+ts.minute/60
        air=ffloat(r['temperature_2m']); rh=ffloat(r['relative_humidity_2m']); dp=ffloat(r['dew_point_2m'])
        wind=ffloat(r.get('wind_speed_10m','0'),0); cloud=ffloat(r.get('cloud_cover','50'),50)
        if any(math.isnan(x) for x in [air,rh,dp]): continue
        ctx={'air':air,'rh':rh,'dp':dp,'wind':wind,'cloud':cloud,'hour':ts.hour}
        predawn=4<=ts.hour<7; passive=ts.hour>=20 or ts.hour<6; near_dp=(air-dp)<=0.8
        if policy=='smart':
            aid=heuristic_action(ctx)
            if rng.random()<0.1: aid=rng.choice([100,200,301]) # small exploration
        else:
            aid=300 if predawn else (200 if passive and near_dp else 100)
        action=next(a for a in ACTIONS if a['id']==aid)
        cloud_factor=1-clamp(cloud,0,100)/100; wind_pen=clamp(1-0.05*wind,0.2,1)
        delta_t=air-dp
        cond=0.0
        if passive:
            cond=clamp((rh-65)*0.4+clamp(2.5-abs(delta_t),0,2.5)*4,0,30)*cloud_factor*wind_pen
            if action['peltier'] and near_dp: cond+=10*cloud_factor
        cond=max(0,cond+rng.gauss(0,0.5)); pinned+=cond
        wh=0.0
        if action['peltier'] and passive and near_dp: wh+=0.33
        harvested=0.0
        if predawn:
            eff=0.25
            if action['vib']==1: eff=0.72; wh+=0.05
            elif action['vib']==2: eff=0.92; wh+=0.09
            eff=clamp(eff-0.02*wind,0.2,0.96)
            harvested=pinned*eff; pinned=max(0,pinned-harvested)
        else:
            pinned*=0.996
        wh_total+=wh; ml_total+=harvested
        timeline.append({
            'time':ts.isoformat(),'state':'PRE_DAWN_SHEDDING' if predawn else ('PASSIVE_COOLING' if passive else 'IDLE'),
            'action':action['name'],'air_c':round(air,2),'rh_pct':round(rh,1),'dew_point_c':round(dp,2),
            'delta_t':round(delta_t,2),'wind_kmh':round(wind,1),'cloud_pct':round(cloud,0),
            'cond_ml':round(cond,2),'pinned_ml':round(pinned,2),'harvest_ml':round(harvested,2),'wh':round(wh,4),
            'cum_ml':round(ml_total,2),'cum_wh':round(wh_total,4)
        })
    reward=ml_total-5*wh_total
    return {'policy':policy,'harvest_ml':ml_total,'wh_total':wh_total,'reward':reward,'ml_per_wh':(ml_total/wh_total if wh_total else float('inf')),'timeline':timeline}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--weather',default='ml/data/open_meteo/2024/Nairobi.csv')
    ap.add_argument('--date',default='2024-02-15')
    ap.add_argument('--out',default='ml/artifacts/demo_night')
    args=ap.parse_args()
    out=Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    rows=[]
    with open(args.weather) as f:
        for r in csv.DictReader(f):
            t=parse_time(r['time'])
            if not t: continue
            # pick night: 18:00 date to 07:00 next day
            d0=datetime.fromisoformat(args.date+'T18:00:00')
            d1=d0+timedelta(hours=13)
            if d0<=t<=d1: rows.append(r)
    if not rows: raise SystemExit('No rows found for night; check --date/--weather')
    smart=sim_night(rows,'smart',seed=7)
    base=sim_night(rows,'baseline',seed=7)
    summary={
        'date':args.date,'rows':len(rows),
        'smart':{k:smart[k] for k in ['harvest_ml','wh_total','reward','ml_per_wh']},
        'baseline':{k:base[k] for k in ['harvest_ml','wh_total','reward','ml_per_wh']},
        'improvement_pct': (smart['reward']-base['reward'])/abs(base['reward']+1e-9)*100
    }
    Path(str(out)+'.json').write_text(json.dumps(summary,indent=2))
    # timeline csv
    with open(str(out)+'_smart.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(smart['timeline'][0].keys())); w.writeheader(); w.writerows(smart['timeline'])
    with open(str(out)+'_baseline.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(base['timeline'][0].keys())); w.writeheader(); w.writerows(base['timeline'])
    # simple HTML
    html=['<html><body><h2>DewLeaf Software Demo</h2>','<pre>'+json.dumps(summary,indent=2)+'</pre>','<table border=1 cellpadding=4><tr><th>time</th><th>state</th><th>smart action</th><th>base action</th><th>smart cum_ml</th><th>base cum_ml</th><th>smart cum_wh</th></tr>']
    for s,b in zip(smart['timeline'],base['timeline']):
        html.append(f"<tr><td>{s['time'][11:16]}</td><td>{s['state']}</td><td>{s['action']}</td><td>{b['action']}</td><td>{s['cum_ml']}</td><td>{b['cum_ml']}</td><td>{s['cum_wh']}</td></tr>")
    html.append('</table></body></html>')
    Path(str(out)+'.html').write_text('\n'.join(html))
    print(json.dumps(summary,indent=2))
    print(f"wrote {out}.json/.html/_smart.csv/_baseline.csv")

if __name__=='__main__': main()
