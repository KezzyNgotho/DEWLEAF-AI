#!/usr/bin/env python3
"""Export a sklearn RandomForestRegressor as a compact C header for ESP32.

Generates flat arrays for tree traversal: children_left/right, feature, threshold, value.
Supports multiple trees; inference sums/averages. Designed for small forests (<=50 trees, depth<=8).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np


def export_forest(model, feature_names: list[str], name: str) -> str:
    estimators = model.estimators_
    all_left, all_right, all_feat, all_thr, all_val, tree_offsets = [], [], [], [], [], []
    for est in estimators:
        t = est.tree_
        off = len(all_left)
        tree_offsets.append(off)
        all_left.extend((t.children_left + (off if t.children_left[0] != -1 else 0)).tolist())  # placeholder
    # do properly
    all_left, all_right, all_feat, all_thr, all_val, tree_offsets = [], [], [], [], [], []
    for est in estimators:
        t = est.tree_
        off = len(all_feat)
        tree_offsets.append(off)
        n = t.node_count
        for i in range(n):
            cl = int(t.children_left[i])
            cr = int(t.children_right[i])
            all_left.append(cl + off if cl != -1 else -1)
            all_right.append(cr + off if cr != -1 else -1)
            all_feat.append(int(t.feature[i]))
            all_thr.append(float(t.threshold[i]))
            # regression value shape (n,1,1) or (n,1)
            v = t.value[i]
            all_val.append(float(v.reshape(-1)[0]))
    lines = [f"// Auto-exported {name} forest: trees={len(estimators)} nodes={len(all_feat)}", "#pragma once", "#include <stdint.h>", ""]
    lines.append(f"static const uint16_t {name.upper()}_TREE_COUNT = {len(estimators)};")
    lines.append(f"static const uint32_t {name.upper()}_NODE_COUNT = {len(all_feat)};")
    lines.append(f"static const uint8_t {name.upper()}_N_FEATURES = {len(feature_names)};")
    lines.append(f"static const uint32_t {name.upper()}_TREE_OFFSETS[{len(tree_offsets)}] = {{{', '.join(map(str, tree_offsets))}}};")
    lines.append(f"static const int16_t {name.upper()}_CHILD_LEFT[{len(all_left)}] = {{{', '.join(map(str, all_left))}}};")
    lines.append(f"static const int16_t {name.upper()}_CHILD_RIGHT[{len(all_right)}] = {{{', '.join(map(str, all_right))}}};")
    lines.append(f"static const int8_t {name.upper()}_FEATURE[{len(all_feat)}] = {{{', '.join(map(str, all_feat))}}};")
    lines.append(f"static const float {name.upper()}_THRESHOLD[{len(all_feat)}] = {{{', '.join(f'{x:.6f}f' for x in all_thr)}}};")
    lines.append(f"static const float {name.upper()}_VALUE[{len(all_val)}] = {{{', '.join(f'{x:.6f}f' for x in all_val)}}};")
    lines.append("")
    lines.append(f"static inline float {name}_predict(const float* x) {{")
    lines.append("  float sum = 0.0f;")
    lines.append(f"  for (uint16_t t = 0; t < {name.upper()}_TREE_COUNT; t++) {{")
    lines.append(f"    uint32_t n = {name.upper()}_TREE_OFFSETS[t];")
    lines.append("    while (1) {")
    lines.append(f"      int16_t cl = {name.upper()}_CHILD_LEFT[n];")
    lines.append("      if (cl == -1) { sum += " + f"{name.upper()}_VALUE[n]; break; }}" )
    lines.append(f"      uint8_t f = (uint8_t){name.upper()}_FEATURE[n];")
    lines.append(f"      float thr = {name.upper()}_THRESHOLD[n];")
    lines.append(f"      n = (x[f] <= thr) ? (uint32_t)cl : (uint32_t){name.upper()}_CHILD_RIGHT[n];")
    lines.append("    }")
    lines.append("  }")
    lines.append(f"  return sum / (float){name.upper()}_TREE_COUNT;")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="joblib with {'ml':Pipeline,'wh':Pipeline,...}")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    bundle = joblib.load(args.model)
    # Support pipeline with preprocessor+regressor
    ml = bundle["ml"]
    wh = bundle["wh"]
    feat_names = bundle.get("features", [])
    # Expect RandomForestRegressor at final step
    ml_reg = ml.named_steps.get("model", ml)
    wh_reg = wh.named_steps.get("model", wh)
    if not hasattr(ml_reg, "estimators_"):
        raise SystemExit("ML model is not a tree ensemble; use --model rf in training")
    header = '#pragma once\n#include <stdint.h>\n\n// DewLeaf edge forest export. Features must be numeric and in training order.\n'
    header += '// Feature order:\n'
    for i, f in enumerate(feat_names):
        header += f'// {i}: {f}\n'
    header += "\n"
    header += export_forest(ml_reg, feat_names, "dewleaf_ml")
    header += export_forest(wh_reg, feat_names, "dewleaf_wh")
    Path(args.out).write_text(header, encoding="utf-8")
    print(f"wrote {args.out}")

if __name__ == "__main__":
    main()
