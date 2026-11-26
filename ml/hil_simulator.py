#!/usr/bin/env python3
"""Hardware-in-the-loop style software simulator.

Runs the same decision logic/timings as firmware intent and emits identical CSV
schema over stdout or TCP, so logger/dashboard/ML pipeline can consume it as if
it were serial telemetry from ESP32.

This is a software twin, not electrical validation.
"""
from __future__ import annotations
import argparse, csv, json, math, random, socket, sys, time
from datetime import datetime, timedelta
from ml.intelligence_engine import Context, decide

HEADER = ["timestamp_ms","iso_time","night_id","state","action_id","air_temp_c","rh_pct","pressure_hpa","dew_point_c","spine_temp_c","soil_temp_c","soil_a_pct","soil_b_pct","bus_v","current_ma","power_mw","wh_total","flow_l_total","flow_l_window","peltier","fan","vib_a","vib_b","valve_flush","valve_drip"]

def clamp(v,lo,hi): return max(lo,min(hi,v))
def dew_point(t,rh):
    a,b=17.62,243.12; g=(a*t)/(b+t)+math.log(max(rh,1e-3)/100)
    return (b*g)/(a-g)

class Emitter:
    def __init__(self, tcp_host='', tcp_port=0):
        self.conn=None; self.sock=None
        if tcp_port:
            self.sock=socket.socket(); self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            self.sock.bind((tcp_host,tcp_port)); self.sock.listen(1)
            print(f"[hil] listening tcp {tcp_host}:{tcp_port}", file=sys.stderr)
            self.conn,_=self.sock.accept(); print("[hil] client connected", file=sys.stderr)
    def send(self,line):
        if self.conn: self.conn.sendall((line+'\n').encode())
        else: print(line, flush=True)
    def close(self):
        try: 
            if self.conn: self.conn.close()
            if self.sock: self.sock.close()
        except: pass

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--realtime',action='store_true',help='sleep by simulated step interval')
    ap.add_argument('--speed',type=float,default=600.0,help='sim seconds per real second when realtime')
    ap.add_argument('--step-s',type=int,default=10,help='telemetry step seconds')
    ap.add_argument('--nights',type=int,default=1)
    ap.add_argument('--start',default='2026-11-01T18:00:00')
    ap.add_argument('--seed',type=int,default=7)
    ap.add_argument('--tcp-port',type=int,default=0)
    args=ap.parse_args()
    rng=random.Random(args.seed)
    start=datetime.fromisoformat(args.start)
    emit=Emitter(tcp_port=args.tcp_port)
    emit.send(','.join(HEADER))
    wh_total=0.0; flow_total=0.0
    try:
        for n in range(args.nights):
            night_start=start+timedelta(days=n)
            nid=f"night-{night_start:%Y%m%d}"
            base_t=rng.gauss(17,1.2); base_rh=clamp(rng.gauss(82,7),55,98)
            cloud=rng.gauss(35,20); wind=rng.gauss(1.8,0.8); pinned=0.0
            steps=int((13*3600)/args.step_s)
            for s in range(steps):
                ts=night_start+timedelta(seconds=s*args.step_s)
                hour=ts.hour + ts.minute/60
                phase=min(max((hour-18)%24,0),13)/13
                air=base_t-4.2*math.sin(math.pi*phase)+rng.gauss(0,.15)
                rh=clamp(base_rh+8*math.sin(math.pi*phase)+rng.gauss(0,.8),40,99)
                dp=dew_point(air,rh); spine=air-(2.0+2.8*(1-cloud/100))+rng.gauss(0,.1)
                soil_a=clamp(62+rng.gauss(0,1)-s*0.003,45,80); soil_b=clamp(soil_a+rng.gauss(0,.6),45,80)
                ctx=Context(air_c=air,rh_pct=rh,dew_point_c=dp,spine_c=spine,soil_a_pct=soil_a,soil_b_pct=soil_b,wind_kmh=wind,cloud_pct=cloud,hour=ts.hour+ts.minute/60,night_wh_used=wh_total)
                d=decide(ctx)
                aid=int(d['selected']['action_id'])
                predawn=4<=ts.hour<7; passive=ts.hour>=20 or ts.hour<6; near_dp=(air-dp)<=0.8
                cond=0.0
                if passive:
                    cond=max(0,(rh-65)*0.5+max(0,2.5-abs(air-dp))*5.0)*(1-cloud/120)*clamp(1-0.05*wind,0.2,1)
                    if aid in (200,201,310) and near_dp and spine>1.5: cond += 12.0 if aid!=200 else 8.0
                cond=max(0,cond+rng.gauss(0,.3)); pinned+=cond
                wh_window=0.0
                if aid in (200,201,310) and passive and near_dp and spine>1.5: wh_window += 0.33 if aid==200 else 0.66 if aid==201 else 0.33
                harvested=0.0
                if predawn:
                    eff=0.25
                    if aid in (300,310): eff=0.90; wh_window+=0.09
                    elif aid==301: eff=0.72; wh_window+=0.05
                    elif aid==302: eff=0.93; wh_window+=0.12
                    eff=clamp(eff-0.02*wind,0.2,0.96)
                    harvested=pinned*eff; pinned=max(0,pinned-harvested)
                else:
                    pinned*=0.996
                wh_total+=wh_window; flow_total+=harvested/1000.0
                state='PRE_DAWN_SHEDDING' if predawn else ('PASSIVE_COOLING' if passive else 'IDLE_DAY')
                row={
                    'timestamp_ms':int(ts.timestamp()*1000),'iso_time':ts.isoformat(),'night_id':nid,'state':state,'action_id':aid,
                    'air_temp_c':round(air,2),'rh_pct':round(rh,2),'pressure_hpa':round(1012+rng.gauss(0,1),2),'dew_point_c':round(dp,2),
                    'spine_temp_c':round(spine,2),'soil_temp_c':round(air-1.2,2),'soil_a_pct':round(soil_a,2),'soil_b_pct':round(soil_b,2),
                    'bus_v':round(12.4+rng.gauss(0,.02),3),'current_ma':round(wh_window*1000/12/(args.step_s/3600),2) if wh_window>0 else round(85+rng.gauss(0,4),2),
                    'power_mw':round(wh_window*1000/(args.step_s/3600),2),'wh_total':round(wh_total,6),'flow_l_total':round(flow_total,6),
                    'flow_l_window':round(harvested/1000.0,6),
                    'peltier':int(aid in (200,201,310) and passive and near_dp),'fan':int(aid in (200,201,310) and passive and near_dp),
                    'vib_a':int(predawn and aid in (300,301,302,310) and harvested>0),'vib_b':int(predawn and aid in (300,302,310) and harvested>0),
                    'valve_flush':0,'valve_drip':0,
                }
                emit.send(','.join(str(row[h]) for h in HEADER))
                if args.realtime: time.sleep(max(args.step_s/args.speed,0))
    finally:
        emit.close()

if __name__=='__main__': main()
