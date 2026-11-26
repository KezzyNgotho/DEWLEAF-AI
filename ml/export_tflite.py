#!/usr/bin/env python3
"""Export DewLeaf surrogate models to TFLite (optional) + C byte array.

Uses sklearn MLPRegressor for a small TFLite-friendly NN when tensorflow is
available; otherwise emits a metadata+fallback artifact. The on-device golden
vector manifest can be validated in Python and used for C-side tests.
"""

from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from ml.train_dewleaf_policy import add_features, FEATURES, CAT_FEATURES, TARGET_ML, TARGET_WH

ACTION_MAP = {100:"passive_only",200:"nucleation_assist",201:"nucleation_full",300:"shed_dual",301:"shed_single_explore",302:"shed_aggressive",310:"shed_dual_nucleation"}
ACTION_NAMES = list(ACTION_MAP.values())

def build_nn():
    return Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()), ("mlp", MLPRegressor(hidden_layer_sizes=(24,12), activation='relu', max_iter=300, random_state=7))])

def feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURES].copy()
    for a in ACTION_NAMES:
        X[f"act_{a}"] = (df["action_name"] == a).astype(float)
    return X.astype(float)

def c_array(name: str, data: bytes) -> str:
    hexs = ', '.join(f'0x{b:02x}' for b in data)
    return f"static const unsigned char {name}[] = {{ {hexs} }};\nstatic const unsigned int {name}_len = {len(data)};\n"

def try_tflite(model: Pipeline, Xs: np.ndarray, out: Path) -> dict:
    try:
        import tensorflow as tf
    except Exception as e:
        return {"ok": False, "reason": f"tensorflow unavailable: {e}"}
    mlp = model.named_steps['mlp']; sc = model.named_steps['sc']; imp = model.named_steps['imp']
    Xp = sc.transform(imp.transform(Xs[:1].astype(np.float32)))
    # Build equivalent keras model
    inp = tf.keras.Input(shape=(Xp.shape[1],), dtype=tf.float32)
    x = inp
    for i,(W,b) in enumerate(zip(mlp.coefs_, mlp.intercepts_)):
        x = tf.keras.layers.Dense(W.shape[1], activation='relu' if i < len(mlp.coefs_)-1 else None,
                                  weights=[W.astype(np.float32), b.astype(np.float32)])(x)
    km = tf.keras.Model(inp,x)
    conv = tf.lite.TFLiteConverter.from_keras_model(km)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    tfl = conv.convert()
    out.write_bytes(tfl)
    return {"ok": True, "bytes": len(tfl), "sha256": hashlib.sha256(tfl).hexdigest()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--out-dir', default='ml/artifacts/tflite')
    ap.add_argument('--max-rows', type=int, default=20000)
    args = ap.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    df = add_features(pd.read_csv(args.data))
    if args.max_rows and len(df) > args.max_rows:
        df = df.sample(n=args.max_rows, random_state=7).reset_index(drop=True)
    X = feature_matrix(df); y_ml = df[TARGET_ML].astype(float); y_wh = df[TARGET_WH].astype(float)
    ml_m = build_nn().fit(X, y_ml); wh_m = build_nn().fit(X, y_wh)
    joblib.dump({'ml':ml_m,'wh':wh_m,'feature_names':list(X.columns)}, out/'tflite_surrogates.joblib')
    Xn = X.to_numpy().astype(np.float32)
    ml_t = try_tflite(ml_m, Xn, out/'dewleaf_ml.tflite')
    wh_t = try_tflite(wh_m, Xn, out/'dewleaf_wh.tflite')
    # golden vectors
    idx = np.linspace(0, len(X)-1, num=min(8, len(X)), dtype=int)
    vectors=[]
    for i in idx:
        xi=pd.DataFrame(Xn[i:i+1], columns=X.columns)
        vectors.append({
            'i': int(i),
            'x': [float(v) for v in xi.iloc[0].to_numpy()],
            'pred_ml': float(ml_m.predict(xi)[0]),
            'pred_wh': float(wh_m.predict(xi)[0]),
        })
    manifest={'format':'dewleaf-tflite-golden-v1','feature_names':list(X.columns),'tflite_ml':ml_t,'tflite_wh':wh_t,'vectors':vectors}
    (out/'golden_vectors.json').write_text(json.dumps(manifest,indent=2))
    # C header for vectors (always available)
    lines=['#pragma once','#include <stdint.h>',f'static const unsigned int DEWLEAF_GV_N={len(vectors)};',f'static const unsigned int DEWLEAF_GV_F={len(X.columns)};']
    flat=[v for vec in vectors for v in vec['x']]
    ml=[vec['pred_ml'] for vec in vectors]; wh=[vec['pred_wh'] for vec in vectors]
    lines.append('static const float DEWLEAF_GV_X[] = {'+','.join(f'{v:.8f}f' for v in flat)+'};')
    lines.append('static const float DEWLEAF_GV_ML[] = {'+','.join(f'{v:.8f}f' for v in ml)+'};')
    lines.append('static const float DEWLEAF_GV_WH[] = {'+','.join(f'{v:.8f}f' for v in wh)+'};')
    if ml_t.get('ok'): lines.append(c_array('DEWLEAF_ML_TFLITE', (out/'dewleaf_ml.tflite').read_bytes()))
    if wh_t.get('ok'): lines.append(c_array('DEWLEAF_WH_TFLITE', (out/'dewleaf_wh.tflite').read_bytes()))
    (out/'dewleaf_golden_vectors.h').write_text('\n'.join(lines))
    print(json.dumps({'out_dir':str(out),'tflite_ml':ml_t,'tflite_wh':wh_t,'vectors':len(vectors)}))

if __name__=='__main__': main()
