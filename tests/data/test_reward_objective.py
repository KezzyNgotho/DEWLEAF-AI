import json
from pathlib import Path

def test_reports_have_reward_fields():
    p = Path('ml/artifacts/bench_sim_report.json')
    d = json.loads(p.read_text())
    assert d['lambda_wh'] > 0
    assert 'mean_improvement_pct' in d
    assert 'folds' in d and len(d['folds']) >= 2
