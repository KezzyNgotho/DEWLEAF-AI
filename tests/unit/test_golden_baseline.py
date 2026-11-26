import subprocess, sys, os
from pathlib import Path

def test_golden_baseline():
    env=os.environ.copy(); env['PYTHONPATH']='.'
    r=subprocess.run([sys.executable,'scripts/checks/check_golden.py'], env=env, capture_output=True, text=True)
    assert r.returncode==0, r.stdout+r.stderr
