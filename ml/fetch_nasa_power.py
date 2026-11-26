#!/usr/bin/env python3
"""Fetch NASA POWER daily agroclimatology for cross-check/domain adaptation."""
from __future__ import annotations
import argparse, csv, json, urllib.parse, urllib.request
from pathlib import Path

PARAMS=['T2M','T2MDEW','RH2M','PRECTOTCORR','WS2M','ALLSKY_SFC_SW_DWN','PS']
def fetch(lat,lon,start,end):
    base='https://power.larc.nasa.gov/api/temporal/daily/point'
    q=urllib.parse.urlencode({'parameters':','.join(PARAMS),'community':'AG','longitude':lon,'latitude':lat,'start':start,'end':end,'format':'JSON'})
    with urllib.request.urlopen(base+'?'+q,timeout=60) as r: return json.loads(r.read().decode())
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--lat',type=float,required=True); ap.add_argument('--lon',type=float,required=True)
    ap.add_argument('--start',default='20240101'); ap.add_argument('--end',default='20241231'); ap.add_argument('--out',required=True)
    a=ap.parse_args(); d=fetch(a.lat,a.lon,a.start,a.end)['properties']['parameter']
    dates=sorted(next(iter(d.values())).keys())
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    with open(a.out,'w',newline='') as f:
        w=csv.writer(f); w.writerow(['date']+PARAMS)
        for dt in dates: w.writerow([dt]+[d[p].get(dt,'') for p in PARAMS])
    print('wrote',a.out,len(dates))
if __name__=='__main__': main()
