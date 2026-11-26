import json, subprocess, sys, os
from pathlib import Path

def test_fault_injection_creates_detectable_faults(tmp_path):
    inp='/tmp/dewleaf_hil.csv'
    faulty=tmp_path/'faulty.csv'
    out=tmp_path/'replay.json'
    env=os.environ.copy(); env['PYTHONPATH']='.'
    subprocess.check_call([sys.executable,'ml/fault_injector.py','--in',inp,'--out',str(faulty),'--rate','0.2','--seed','1'],env=env)
    subprocess.check_call([sys.executable,'ml/replay.py','--data',str(faulty),'--out',str(out)],env=env)
    d=json.loads(out.read_text())
    assert d['fault_count']>0
