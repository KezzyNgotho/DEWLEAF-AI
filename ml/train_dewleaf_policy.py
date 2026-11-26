#!/usr/bin/env python3
"""Leak-free DewLeaf Phase 0 training pipeline.

Trains surrogate models:
- harvested_ml predictor
- wh_window predictor

Policy selects action maximizing: R = predicted_ml - lambda * predicted_wh.
Validation uses GroupKFold by night_id to prevent same-night leakage.
Exports a compact C header for edge inference.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


NUM_FEATURES = [
    "air_temp_c", "rh_pct", "pressure_hpa", "dew_point_c", "spine_temp_c",
    "soil_a_pct", "soil_b_pct", "bus_v", "delta_t", "hour_sin", "hour_cos", "is_predawn",
    "wind_speed_kmh", "cloud_cover_pct", "vpd_kpa", "et0_mm", "rh_x_cloud", "delta_t_x_wind",
    "soil_mean", "dew_margin"
]
CAT_FEATURES = ["action_name"]
FEATURES = NUM_FEATURES  # backward compat name
TARGET_ML = "harvested_ml"
TARGET_WH = "wh_window"


@dataclass
class EvalResult:
    fold: int
    ml_mae: float
    wh_mae: float
    policy_reward: float
    baseline_reward: float
    improvement_pct: float


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["iso_time"] = pd.to_datetime(out["iso_time"])
    hour = out["iso_time"].dt.hour + out["iso_time"].dt.minute / 60.0
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    out["is_predawn"] = ((out["iso_time"].dt.hour >= 4) & (out["iso_time"].dt.hour < 7)).astype(int)
    out["delta_t"] = out["air_temp_c"] - out["dew_point_c"]
    for col, default in [("wind_speed_kmh", 0.0), ("cloud_cover_pct", 50.0), ("vpd_kpa", 0.0), ("et0_mm", 0.0), ("pressure_hpa", 1012.0), ("spine_temp_c", out.get("air_temp_c", 0) - 2), ("soil_a_pct", 60.0), ("soil_b_pct", 60.0), ("bus_v", 12.4)]:
        if col not in out.columns:
            out[col] = default
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(default)
    out["rh_x_cloud"] = out["rh_pct"] * (1.0 - out["cloud_cover_pct"] / 100.0)
    out["delta_t_x_wind"] = out["delta_t"] * out["wind_speed_kmh"]
    out["soil_mean"] = (pd.to_numeric(out["soil_a_pct"], errors="coerce").fillna(60) + pd.to_numeric(out["soil_b_pct"], errors="coerce").fillna(60)) / 2.0
    out["dew_margin"] = 2.5 - out["delta_t"].abs()
    if "action_name" not in out.columns:
        mapping = {100: "passive_only", 200: "nucleation_assist", 201: "nucleation_full", 300: "shed_dual", 301: "shed_single_explore", 302: "shed_aggressive", 310: "shed_dual_nucleation"}
        out["action_name"] = out["action_id"].map(mapping).fillna("unknown")
    # For real logs without explicit targets, derive from flow and power windows.
    if TARGET_ML not in out.columns:
        if "flow_l_window" in out.columns:
            out[TARGET_ML] = out["flow_l_window"].astype(float) * 1000.0
        else:
            raise ValueError("Dataset missing harvested_ml and flow_l_window")
    if TARGET_WH not in out.columns:
        if "power_mw" in out.columns:
            out[TARGET_WH] = pd.to_numeric(out["power_mw"], errors="coerce").fillna(0) / 1000.0 * (10 / 60)
        else:
            raise ValueError("Dataset missing wh_window and power_mw")
    return out


def make_model(model_name: str = "hgb") -> Pipeline:
    pre = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), FEATURES),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("oh", OneHotEncoder(handle_unknown="ignore")),
        ]), CAT_FEATURES),
    ])
    if model_name == "rf":
        reg = RandomForestRegressor(n_estimators=80, random_state=7, min_samples_leaf=2, n_jobs=-1)
    elif model_name == "edge_rf":
        reg = RandomForestRegressor(n_estimators=24, random_state=7, max_depth=6, min_samples_leaf=20, n_jobs=-1)
    else:
        reg = HistGradientBoostingRegressor(random_state=7, max_depth=6, max_iter=120, learning_rate=0.05)
    return Pipeline([("pre", pre), ("model", reg)])


def candidate_actions(df: pd.DataFrame) -> list[str]:
    return sorted(df["action_name"].dropna().unique().tolist())


def evaluate_policy(ml_model: Pipeline, wh_model: Pipeline, df: pd.DataFrame, lam: float, baseline_action: str) -> tuple[float, float, float]:
    actions = candidate_actions(df)
    base = df.copy()
    base["action_name"] = baseline_action
    baseline_reward = float(np.mean(ml_model.predict(base[FEATURES + CAT_FEATURES]) - lam * wh_model.predict(base[FEATURES + CAT_FEATURES])))

    # Vectorized policy evaluation over all contexts x actions.
    ctx = df.loc[df.index.repeat(len(actions)), FEATURES + CAT_FEATURES].copy()
    ctx["action_name"] = np.tile(actions, len(df))
    pred_ml = ml_model.predict(ctx[FEATURES + CAT_FEATURES])
    pred_wh = wh_model.predict(ctx[FEATURES + CAT_FEATURES])
    pred_reward = (pred_ml - lam * pred_wh).reshape(len(df), len(actions))
    best_idx = np.argmax(pred_reward, axis=1)
    best_actions = np.array(actions)[best_idx]
    observed = (df[TARGET_ML] - lam * df[TARGET_WH]).to_numpy()
    rewards = np.where(best_actions == df["action_name"].to_numpy(), observed, pred_reward[np.arange(len(df)), best_idx])
    policy_reward = float(np.mean(rewards))
    improvement = ((policy_reward - baseline_reward) / abs(baseline_reward + 1e-9)) * 100.0
    return policy_reward, baseline_reward, improvement


def export_header(df: pd.DataFrame, actions: list[str], out_path: Path, lam: float) -> None:
    """Export compact edge artifact with empirical action reward biases."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    action_ids = {
        "passive_only": 100, "nucleation_assist": 200, "nucleation_full": 201,
        "shed_dual": 300, "shed_single_explore": 301, "shed_aggressive": 302,
        "shed_dual_nucleation": 310, "unknown": 0,
    }
    means = {}
    for a in actions:
        sub = df[df["action_name"] == a]
        means[a] = float((sub[TARGET_ML] - lam * sub[TARGET_WH]).mean()) if len(sub) else 0.0
    baseline = means.get("passive_only", 0.0)
    lines = [
        "#pragma once",
        "#include <stdint.h>",
        "",
        "// Generated from DewLeaf training data. Biases are empirical mean rewards relative to passive_only.",
        "// For full nonlinear edge inference, use exported TFLM model artifact alongside this fallback.",
        "struct DewLeafActionScore { uint16_t action_id; float reward_bias; };",
        "",
        f"static const float DEWLEAF_LAMBDA_WH = {lam}f;",
        f"static const uint8_t DEWLEAF_ACTION_COUNT = {len(actions)};",
        "static const DewLeafActionScore DEWLEAF_ACTION_SCORES[] = {",
    ]
    for a in actions:
        aid = action_ids.get(a, 0)
        bias = means.get(a, 0.0) - baseline
        lines.append(f"  {{ {aid}, {bias:.4f}f }}, // {a}, mean_reward={means.get(a,0.0):.3f}")
    lines += [
        "};",
        "",
        "static inline uint16_t dewleaf_select_action(uint16_t fallback_action_id) {",
        "  uint16_t best = fallback_action_id; float best_bias = -1e9f;",
        "  for (uint8_t i = 0; i < DEWLEAF_ACTION_COUNT; i++) {",
        "    if (DEWLEAF_ACTION_SCORES[i].reward_bias > best_bias) {",
        "      best_bias = DEWLEAF_ACTION_SCORES[i].reward_bias; best = DEWLEAF_ACTION_SCORES[i].action_id;",
        "    }",
        "  }",
        "  return best;",
        "}",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def export_tflite_or_tree(ml_model: Pipeline, wh_model: Pipeline, out_path: Path) -> None:
    """Export model metadata; TFLM conversion can be added when tflite runtime is available."""
    meta = {
        "format": "sklearn-joblib",
        "note": "Convert to TFLite/TFLM for ESP32 deployment. Joblib is for cloud/offline evaluation.",
        "features": FEATURES,
        "cat_features": CAT_FEATURES,
        "targets": [TARGET_ML, TARGET_WH],
    }
    out_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="models/dewleaf_policy.h")
    ap.add_argument("--model-out", default="ml/artifacts/dewleaf_models.joblib")
    ap.add_argument("--report-out", default="ml/artifacts/validation_report.json")
    ap.add_argument("--lambda-wh", type=float, default=5.0)
    ap.add_argument("--splits", type=int, default=5)
    ap.add_argument("--baseline-action", default="passive_only")
    ap.add_argument("--model", choices=["hgb","rf","edge_rf"], default="hgb")
    ap.add_argument("--max-rows", type=int, default=0, help="Subsample rows for faster iteration; 0=all")
    args = ap.parse_args()

    df = add_features(pd.read_csv(args.data))
    if args.max_rows and len(df) > args.max_rows:
        df = df.sample(n=args.max_rows, random_state=7).sort_values("timestamp_ms").reset_index(drop=True)
    if "night_id" not in df.columns:
        raise ValueError("Dataset must include night_id for GroupKFold")
    groups = df["night_id"]
    n_groups = df["night_id"].nunique()
    splits = max(2, min(args.splits, n_groups))
    gkf = GroupKFold(n_splits=splits)

    results: list[EvalResult] = []
    for fold, (train_idx, test_idx) in enumerate(gkf.split(df, groups=groups), start=1):
        train, test = df.iloc[train_idx], df.iloc[test_idx]
        # Safety: assert no night leakage
        overlap = set(train["night_id"]).intersection(set(test["night_id"]))
        if overlap:
            raise RuntimeError(f"Night leakage detected: {overlap}")

        ml_model = make_model(args.model)
        wh_model = make_model(args.model)
        ml_model.fit(train[FEATURES + CAT_FEATURES], train[TARGET_ML])
        wh_model.fit(train[FEATURES + CAT_FEATURES], train[TARGET_WH])

        pred_ml = ml_model.predict(test[FEATURES + CAT_FEATURES])
        pred_wh = wh_model.predict(test[FEATURES + CAT_FEATURES])
        policy_reward, baseline_reward, improvement = evaluate_policy(
            ml_model, wh_model, test, args.lambda_wh, args.baseline_action
        )
        results.append(EvalResult(
            fold=fold,
            ml_mae=float(mean_absolute_error(test[TARGET_ML], pred_ml)),
            wh_mae=float(mean_absolute_error(test[TARGET_WH], pred_wh)),
            policy_reward=policy_reward,
            baseline_reward=baseline_reward,
            improvement_pct=improvement,
        ))

    # Fit final models on full data for export
    final_ml = make_model(args.model).fit(df[FEATURES + CAT_FEATURES], df[TARGET_ML])
    final_wh = make_model(args.model).fit(df[FEATURES + CAT_FEATURES], df[TARGET_WH])

    model_out = Path(args.model_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"ml": final_ml, "wh": final_wh, "features": FEATURES, "cat_features": CAT_FEATURES, "lambda": args.lambda_wh}, model_out)

    export_header(df, candidate_actions(df), Path(args.out), args.lambda_wh)
    export_tflite_or_tree(final_ml, final_wh, Path(args.model_out).with_suffix(".json"))

    label_source = str(df["label_source"].iloc[0]) if "label_source" in df.columns and len(df) else "unknown"
    measured = bool("measured" in label_source.lower() or "bench" in label_source.lower())
    report = {
        "n_rows": int(len(df)),
        "n_nights": int(df["night_id"].nunique()),
        "splits": splits,
        "lambda_wh": args.lambda_wh,
        "baseline_action": args.baseline_action,
        "label_source": label_source,
        "measured_data": measured,
        "d0_3_claim_valid": bool(measured and np.mean([r.improvement_pct for r in results]) >= 15.0),
        "mean_improvement_pct": float(np.mean([r.improvement_pct for r in results])),
        "mean_policy_reward": float(np.mean([r.policy_reward for r in results])),
        "mean_baseline_reward": float(np.mean([r.baseline_reward for r in results])),
        "target_met_15pct": bool(np.mean([r.improvement_pct for r in results]) >= 15.0),
        "folds": [r.__dict__ for r in results],
    }
    report_out = Path(args.report_out)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"wrote {args.out}")
    print(f"wrote {model_out}")
    print(f"wrote {report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
