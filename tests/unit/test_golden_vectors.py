import json, joblib, numpy as np, pandas as pd
from pathlib import Path

def test_golden_vectors_match_surrogate():
    m=json.loads(Path('ml/artifacts/tflite/golden_vectors.json').read_text())
    b=joblib.load('ml/artifacts/tflite/tflite_surrogates.joblib')
    X=pd.DataFrame([v['x'] for v in m['vectors']], columns=m['feature_names'])
    ml=b['ml'].predict(X); wh=b['wh'].predict(X)
    for i,v in enumerate(m['vectors']):
        assert abs(float(ml[i])-v['pred_ml'])<1e-4
        assert abs(float(wh[i])-v['pred_wh'])<1e-4
