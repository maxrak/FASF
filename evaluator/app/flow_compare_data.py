#!/usr/bin/env python3
"""
flow_compare_data.py
Legge i CSV, calcola le differenze e genera report_data.json (e i CSV di dettaglio).
Esempio: python flow_compare_data.py original.csv simulated.csv -o output_dir
"""

import argparse
import math
import os
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd

try:
    from scipy.optimize import linear_sum_assignment
except Exception:
    linear_sum_assignment = None

KEY_COLS_DEFAULT = ["Src IP", "Src Port", "Dst IP", "Dst Port"]
EXCLUDE_DEFAULT = {"Flow ID", "Timestamp"}
EPS = 1e-12

FEATURE_GROUPS = {
    "identita/topologia": ["Protocol"],
    "durata/timing": ["Duration", "IAT", "Active", "Idle"],
    "conteggi pacchetti": ["Total Fwd Packet", "Total Bwd packets", "Packet", "Subflow"],
    "dimensioni/lunghezze": ["Length", "Header", "Segment", "Bytes/Bulk", "Bulk Rate"],
    "throughput/rate": ["Bytes/s", "Packets/s", "Rate"],
    "TCP/flag/window": ["Flag", "Window", "TCP", "PSH", "URG", "ECE", "CWR", "ACK", "RST", "SYN", "FIN"],
}

def normalize_keys(df: pd.DataFrame, key_cols: Sequence[str]) -> pd.DataFrame:
    out = df.copy()
    for c in key_cols:
        if c not in out.columns:
            raise ValueError(f"Colonna chiave mancante: {c}")
        if "IP" in c:
            out[c] = out[c].astype(str).str.strip()
        else:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64").astype(str)
    return out

def common_numeric_features(original: pd.DataFrame, simulated: pd.DataFrame, exclude: Iterable[str], keys: Sequence[str]) -> List[str]:
    ex_set = set(exclude).union(keys)
    common = [c for c in original.columns if c in simulated.columns and c not in ex_set]
    return [c for c in common if pd.to_numeric(original[c], errors="coerce").notna().any() or pd.to_numeric(simulated[c], errors="coerce").notna().any()]

def infer_group(feature: str) -> str:
    for group, needles in FEATURE_GROUPS.items():
        for n in needles:
            if n.lower() in feature.lower(): return group
    return "altro"

def robust_scale(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if values.size == 0: return 1.0
    q75, q25 = np.percentile(values, [75, 25])
    iqr = q75 - q25
    if abs(iqr) > EPS: return float(iqr)
    std = np.std(values)
    if std > EPS: return float(std)
    mx = np.max(np.abs(values))
    return float(mx) if mx > EPS else 1.0

def build_cost_matrix(o_group: pd.DataFrame, s_group: pd.DataFrame, features: Sequence[str]) -> np.ndarray:
    n, m = len(o_group), len(s_group)
    cost = np.zeros((n, m), dtype=float)
    used = 0
    for f in features:
        ov = pd.to_numeric(o_group[f], errors="coerce").to_numpy(dtype=float)
        sv = pd.to_numeric(s_group[f], errors="coerce").to_numpy(dtype=float)
        scale = robust_scale(np.concatenate([ov, sv]))
        diff = np.abs(ov[:, None] - sv[None, :]) / scale
        both_nan = np.isnan(ov[:, None]) & np.isnan(sv[None, :])
        one_nan = np.isnan(ov[:, None]) ^ np.isnan(sv[None, :])
        diff = np.where(both_nan, 0.0, diff)
        diff = np.where(one_nan, 10.0, diff)
        cost += np.nan_to_num(diff, nan=10.0, posinf=10.0, neginf=10.0)
        used += 1
    return cost / used if used > 0 else cost

def assign_pairs(cost: np.ndarray) -> List[Tuple[int, int]]:
    if cost.size == 0: return []
    if linear_sum_assignment is not None:
        rows, cols = linear_sum_assignment(cost)
        return list(zip(rows.tolist(), cols.tolist()))
    # Fallback greedy
    pairs, used_i, used_j = [], set(), set()
    for _, i, j in sorted((cost[i, j], i, j) for i in range(cost.shape[0]) for j in range(cost.shape[1])):
        if i not in used_i and j not in used_j:
            pairs.append((i, j)); used_i.add(i); used_j.add(j)
    return pairs

def df_to_json_ready(df: pd.DataFrame) -> List[dict]:
    if df.empty: return []
    return df.replace([np.inf, -np.inf, np.nan], None).to_dict(orient="records")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("original_csv")
    ap.add_argument("simulated_csv")
    ap.add_argument("-o", "--output-dir", default="report_output")
    ap.add_argument("--key-cols", nargs=4, default=KEY_COLS_DEFAULT)
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    original = normalize_keys(pd.read_csv(args.original_csv, engine="python"), args.key_cols)
    simulated = normalize_keys(pd.read_csv(args.simulated_csv, engine="python"), args.key_cols)
    features = common_numeric_features(original, simulated, EXCLUDE_DEFAULT, args.key_cols)

    matched_rows, diff_rows = [], []
    missing_indices, extra_indices = set(original.index), set(simulated.index)
    all_keys = pd.concat([original[args.key_cols], simulated[args.key_cols]], ignore_index=True).drop_duplicates()

    for _, k_row in all_keys.iterrows():
        og = original.loc[np.logical_and.reduce([(original[c] == k_row[c]) for c in args.key_cols])]
        sg = simulated.loc[np.logical_and.reduce([(simulated[c] == k_row[c]) for c in args.key_cols])]
        if og.empty or sg.empty: continue

        cost = build_cost_matrix(og, sg, features)
        for oi_local, si_local in assign_pairs(cost):
            oi, si = og.index[oi_local], sg.index[si_local]
            missing_indices.discard(oi); extra_indices.discard(si)
            
            o_row, s_row = original.loc[oi], simulated.loc[si]
            pair_id = len(matched_rows) + 1
            
            row = {"pair_id": pair_id}
            for c in args.key_cols: row[c] = o_row[c]
            matched_rows.append(row)

            # Cell differences
            for f in features:
                ov, sv = pd.to_numeric(o_row[f], errors="coerce"), pd.to_numeric(s_row[f], errors="coerce")
                abs_e = np.nan if pd.isna(ov) or pd.isna(sv) else abs(float(ov) - float(sv))
                sgn_e = np.nan if pd.isna(ov) or pd.isna(sv) else float(sv) - float(ov)
                rel_e = abs_e / abs(float(ov)) if pd.notna(abs_e) and abs(float(ov)) > EPS else np.nan
                
                d = {"pair_id": pair_id, "feature": f, "group": infer_group(f), "original_value": ov, 
                     "simulated_value": sv, "absolute_error": abs_e, "relative_error_pct": rel_e * 100 if pd.notna(rel_e) else np.nan, "signed_error": sgn_e}
                for c in args.key_cols: d[c] = o_row[c]
                
                # Flow Endpoint String formatting
                d["Endpoint Flusso"] = f"{d.get(args.key_cols[0], '')}:{d.get(args.key_cols[1], '')} &rarr; {d.get(args.key_cols[2], '')}:{d.get(args.key_cols[3], '')}" if len(args.key_cols)==4 else " | ".join(str(d.get(k,'')) for k in args.key_cols)
                
                diff_rows.append(d)

    matched = pd.DataFrame(matched_rows)
    missing = original.loc[sorted(missing_indices)].copy()
    extra = simulated.loc[sorted(extra_indices)].copy()
    cell_df = pd.DataFrame(diff_rows)

    summary = pd.DataFrame()
    if not cell_df.empty:
        summary = cell_df.groupby(["feature", "group"]).agg(
            mae=("absolute_error", "mean"), mean_relative_error_pct=("relative_error_pct", "mean"), mean_signed_error=("signed_error", "mean")
        ).reset_index().sort_values(["mean_relative_error_pct", "mae"], ascending=False, na_position="last")

    # Scrittura JSON strutturato per il report
    report_data = {
        "metadata": {"matched_count": len(matched), "missing_count": len(missing), "extra_count": len(extra)},
        "summary": df_to_json_ready(summary),
        "flow_details": df_to_json_ready(cell_df),
        "missing_flows": df_to_json_ready(missing.head(1000)),
        "extra_flows": df_to_json_ready(extra.head(1000))
    }
    
    with open(out_dir / "report_data.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False)
        
    print(f"✅ Dati elaborati. Generato: {out_dir / 'report_data.json'}")

if __name__ == "__main__":
    main()