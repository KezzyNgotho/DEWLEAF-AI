#!/usr/bin/env python3
"""Fetch Open-Meteo archive weather for global arid/semi-arid/ag-dew regions.

Designed for large-scale pretraining. Respects disk by defaulting to 1 year and
selected representative locations. Use --locations-file for custom lists.
"""

from __future__ import annotations
import argparse, csv, json, time, urllib.parse, urllib.request
from pathlib import Path

# Representative global locations relevant to dew harvesting / dryland ag.
# Mix of arid, semi-arid, coastal-desert, and highland dew-prone regions.
GLOBAL_LOCATIONS = [
    # Africa
    {"name":"Nairobi_KE","lat":-1.286389,"lon":36.817223,"region":"Africa"},
    {"name":"Machakos_KE","lat":-1.517683,"lon":37.263414,"region":"Africa"},
    {"name":"Lodwar_Turkana_KE","lat":3.1199,"lon":35.5966,"region":"Africa"},
    {"name":"Marsa_Matruh_EG","lat":31.3543,"lon":27.2373,"region":"Africa"},
    {"name":"Cairo_EG","lat":30.0444,"lon":31.2357,"region":"Africa"},
    {"name":"Agadir_MA","lat":30.4278,"lon":-9.5981,"region":"Africa"},
    {"name":"Tunis_TN","lat":36.8065,"lon":10.1815,"region":"Africa"},
    {"name":"Dakar_SN","lat":14.7167,"lon":-17.4677,"region":"Africa"},
    {"name":"Niamey_NE","lat":13.5116,"lon":2.1254,"region":"Africa"},
    {"name":"Addis_Ababa_ET","lat":9.0320,"lon":38.7469,"region":"Africa"},
    {"name":"Windhoek_NA","lat":-22.5609,"lon":17.0658,"region":"Africa"},
    {"name":"Upington_ZA","lat":-28.4478,"lon":21.2561,"region":"Africa"},
    # Middle East
    {"name":"Amman_JO","lat":31.9454,"lon":35.9284,"region":"MiddleEast"},
    {"name":"Riyadh_SA","lat":24.7136,"lon":46.6753,"region":"MiddleEast"},
    {"name":"Al_Madinah_SA","lat":24.5247,"lon":39.5692,"region":"MiddleEast"},
    {"name":"Dubai_AE","lat":25.2048,"lon":55.2708,"region":"MiddleEast"},
    {"name":"Muscat_OM","lat":23.5880,"lon":58.3829,"region":"MiddleEast"},
    {"name":"Sanaa_YE","lat":15.3694,"lon":44.1910,"region":"MiddleEast"},
    # South Asia
    {"name":"Jodhpur_IN","lat":26.2389,"lon":73.0243,"region":"SouthAsia"},
    {"name":"Kutch_IN","lat":23.7337,"lon":69.8597,"region":"SouthAsia"},
    {"name":"Ahmedabad_IN","lat":23.0225,"lon":72.5714,"region":"SouthAsia"},
    {"name":"Hyderabad_IN","lat":17.3850,"lon":78.4867,"region":"SouthAsia"},
    {"name":"Karachi_PK","lat":24.8607,"lon":67.0011,"region":"SouthAsia"},
    # East Asia / Central
    {"name":"Lanzhou_CN","lat":36.0611,"lon":103.8343,"region":"EastAsia"},
    {"name":"Hohhot_CN","lat":40.8414,"lon":111.7519,"region":"EastAsia"},
    {"name":"Ulaanbaatar_MN","lat":47.8864,"lon":106.9057,"region":"EastAsia"},
    # Americas
    {"name":"Tucson_US","lat":32.2226,"lon":-110.9747,"region":"Americas"},
    {"name":"Phoenix_US","lat":33.4484,"lon":-112.0740,"region":"Americas"},
    {"name":"El_Paso_US","lat":31.7619,"lon":-106.4850,"region":"Americas"},
    {"name":"Monterrey_MX","lat":25.6866,"lon":-100.3161,"region":"Americas"},
    {"name":"Antofagasta_CL","lat":-23.6509,"lon":-70.3975,"region":"Americas"},
    {"name":"Lima_PE","lat":-12.0464,"lon":-77.0428,"region":"Americas"},
    {"name":"Petrolina_BR","lat":-9.3891,"lon":-40.5031,"region":"Americas"},
    # Europe / Med
    {"name":"Almeria_ES","lat":36.8340,"lon":-2.4637,"region":"Europe"},
    {"name":"Athens_GR","lat":37.9838,"lon":23.7275,"region":"Europe"},
    {"name":"Nicosia_CY","lat":35.1856,"lon":33.3823,"region":"Europe"},
    # Australia
    {"name":"Alice_Springs_AU","lat":-23.6980,"lon":133.8807,"region":"Australia"},
    {"name":"Broken_Hill_AU","lat":-31.9539,"lon":141.4539,"region":"Australia"},
]

HOURLY = [
    "temperature_2m","relative_humidity_2m","dew_point_2m","pressure_msl",
    "wind_speed_10m","cloud_cover","shortwave_radiation","direct_radiation",
    "diffuse_radiation","precipitation","et0_fao_evapotranspiration",
    "vapour_pressure_deficit","soil_temperature_0cm","soil_moisture_0_to_1cm",
]

def fetch(loc, start, end):
    params = {"latitude":loc["lat"],"longitude":loc["lon"],"start_date":start,"end_date":end,
              "hourly":",".join(HOURLY),"timezone":"UTC"}
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent":"dewleaf-global/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

def write_csv(payload, loc, out):
    hourly = payload.get("hourly",{}); times=hourly.get("time",[])
    if not times: return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    fields=["location","region","latitude","longitude","time"]+HOURLY
    with out.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for i,t in enumerate(times):
            row={"location":loc["name"],"region":loc.get("region",""),"latitude":payload.get("latitude",loc["lat"]),"longitude":payload.get("longitude",loc["lon"]),"time":t}
            for k in HOURLY:
                vals=hourly.get(k,[]); row[k]=vals[i] if i<len(vals) else ""
            w.writerow(row)
    return len(times)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",default="ml/data/global_open_meteo/2024")
    ap.add_argument("--start",default="2024-01-01")
    ap.add_argument("--end",default="2024-12-31")
    ap.add_argument("--sleep",type=float,default=0.5)
    ap.add_argument("--max-locations",type=int,default=0)
    ap.add_argument("--locations-file",default="",help="JSON list of {name,lat,lon,region}")
    args=ap.parse_args()
    locs=GLOBAL_LOCATIONS
    if args.locations_file:
        locs=json.loads(Path(args.locations_file).read_text())
    if args.max_locations: locs=locs[:args.max_locations]
    out_dir=Path(args.out_dir); manifest=[]
    for idx,loc in enumerate(locs,1):
        out=out_dir/f"{loc['name']}.csv"
        if out.exists() and out.stat().st_size>1000:
            manifest.append({"location":loc["name"],"status":"exists","file":str(out)}); print(f"[{idx}/{len(locs)}] {loc['name']}: exists"); continue
        try:
            n=write_csv(fetch(loc,args.start,args.end),loc,out)
            manifest.append({"location":loc["name"],"rows":n,"status":"ok","file":str(out)})
            print(f"[{idx}/{len(locs)}] {loc['name']}: {n}", flush=True)
        except Exception as e:
            manifest.append({"location":loc["name"],"status":f"error:{e}","file":str(out)})
            print(f"[{idx}/{len(locs)}] {loc['name']}: ERROR {e}", flush=True)
        time.sleep(args.sleep)
    (out_dir/"manifest.json").write_text(json.dumps({"start":args.start,"end":args.end,"locations":manifest},indent=2))
    ok=sum(1 for m in manifest if m['status'] in ('ok','exists'))
    print(f"done {ok}/{len(locs)}")
    return 0

if __name__=='__main__': raise SystemExit(main())
