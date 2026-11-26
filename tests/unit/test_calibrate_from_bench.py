import json, subprocess, sys, os
from pathlib import Path

def test_calibrate_from_bench(tmp_path):
    out_h=tmp_path/'policy.h'; out_r=tmp_path/'r.json'
    env=os.environ.copy(); env['PYTHONPATH']='.'
    subprocess.check_call([sys.executable,'ml/calibrate_from_bench.py','--data','logs/sim_bench_14night.csv','--out-header',str(out_h),'--out-report',str(out_r)], env=env)
    d=json.loads(out_r.read_text())
    assert d['nights']==14
    assert out_h.exists()
    assert 'measured' in d['label_source']
