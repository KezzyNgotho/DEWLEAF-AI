import json, subprocess, os, sys
from pathlib import Path

def test_replay_generates_report(tmp_path):
    data = Path('/tmp/dewleaf_hil.csv')
    out = tmp_path/'replay.json'
    env = os.environ.copy(); env['PYTHONPATH']='.'
    subprocess.check_call([sys.executable,'ml/replay.py','--data',str(data),'--out',str(out)], env=env)
    d=json.loads(out.read_text())
    assert d['rows']>0
    assert 'fault_count' in d
    assert 'decision' in d['events'][0]
