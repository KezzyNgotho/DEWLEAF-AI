#!/usr/bin/env python3
"""Model promotion gate: blocks promotion unless required evidence exists."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / 'ml/models/registry/model_registry.json'

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--model-id', required=True)
    ap.add_argument('--to', default='staging', choices=['dev','staging','prod'])
    ap.add_argument('--require-measured', action='store_true')
    args=ap.parse_args()
    reg=json.loads(REG.read_text())
    m=next((x for x in reg['models'] if x['model_id']==args.model_id), None)
    if not m: raise SystemExit('model not found')
    report=ROOT / m['report']
    artifact=ROOT / m['artifact']
    if not report.exists() or not artifact.exists(): raise SystemExit('missing artifact/report')
    r=json.loads(report.read_text())
    failures=[]
    if args.require_measured and not r.get('measured_data'): failures.append('measured_data_required')
    if args.to=='prod' and not r.get('d0_3_claim_valid', False): failures.append('d0_3_claim_invalid_for_prod')
    if 'mean_improvement_pct' not in r: failures.append('missing_metric')
    if failures:
        print(json.dumps({'ok':False,'failures':failures,'model':m['model_id']})); raise SystemExit(2)
    m['status']=args.to
    m['artifact_sha256']=sha256(artifact)
    m['report_sha256']=sha256(report)
    REG.write_text(json.dumps(reg, indent=2))
    print(json.dumps({'ok':True,'model':m['model_id'],'status':args.to}))

if __name__=='__main__': main()
