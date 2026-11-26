import json, subprocess, sys, os
from pathlib import Path

def test_fault_scenario_replay(tmp_path):
    src=Path('/tmp/dewleaf_hil.csv')
    if not src.exists():
        subprocess.check_call([sys.executable,'-c',"import subprocess,os,sys; env=os.environ.copy(); env['PYTHONPATH']='.'; open('/tmp/dewleaf_hil.csv','w').write(subprocess.check_output([sys.executable,'ml/hil_simulator.py','--nights','1','--step-s','600','--seed','7'],env=env,text=True))"], env={**os.environ,'PYTHONPATH':'.'})
    faulty=tmp_path/'f.csv'; out=tmp_path/'r.json'
    env={**os.environ,'PYTHONPATH':'.'}
    subprocess.check_call([sys.executable,'ml/fault_injector.py','--in',str(src),'--out',str(faulty),'--rate','0.1','--seed','2'],env=env)
    subprocess.check_call([sys.executable,'ml/replay.py','--data',str(faulty),'--out',str(out)],env=env)
    d=json.loads(out.read_text())
    assert d['rows']>0
