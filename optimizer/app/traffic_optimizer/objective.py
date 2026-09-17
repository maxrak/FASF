from __future__ import annotations

"""
Objective function for the traffic optimizer.

This version optimizes only the 24 domain-critical features requested for the
flow simulation project. It is designed as a drop-in replacement for
traffic_optimizer/objective.py and keeps the public score_report(...) function
used by the optimizer.

Expected report format:
  - Prefer report["flow_details"]: one row per flow/feature comparison.
  - Fallback to report["summary"]: one row per feature aggregate comparison.

Returned score convention:
  - Lower is better.
  - 0.0 means perfect match on the selected features.
"""

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Target features: exactly the 24 features selected for this domain.
# Keep names as they appear in the comparison JSON.
# ---------------------------------------------------------------------------

TARGET_FEATURES: Tuple[str, ...] = (
    "Flow Duration",
    "Total Length of Fwd Packet",
    "Fwd Packet Length Max",
    "Fwd Packet Length Min",
    "Bwd Packet Length Max",
    "Bwd Packet Length Min",
    "Flow Bytes/s",
    #"Flow IAT Min",
    #"Fwd IAT Min",
    #"Bwd IAT Min",
    "Fwd URG Flags",
    "Bwd URG Flags",
    "Fwd RST Flags",
    "Bwd RST Flags",
    "Packet Length Std",
    "FIN Flag Count",
    "SYN Flag Count",
    "CWR Flag Count",
    "ECE Flag Count",
    "Down/Up Ratio",
    #"Bwd Init Win Bytes",
    "Bwd Seg Size Min",
    "Fwd TCP Retrans. Count",
    "Bwd TCP Retrans. Count",
)

TARGET_FEATURE_SET = set(TARGET_FEATURES)

# Aliases useful when different tools produce slightly different spellings.
FEATURE_ALIASES: Dict[str, str] = {
    "Total Fwd Length": "Total Length of Fwd Packet",
    "Total Length of Fwd Packets": "Total Length of Fwd Packet",
    "FWD Init Win Bytes": "FWD Init Win Bytes",  # intentionally not targeted
    "Bwd Init Win bytes": "Bwd Init Win Bytes",
    "Bwd Init Window Bytes": "Bwd Init Win Bytes",
    "Fwd TCP Retrans Count": "Fwd TCP Retrans. Count",
    "Bwd TCP Retrans Count": "Bwd TCP Retrans. Count",
    "Fwd TCP Retransmission Count": "Fwd TCP Retrans. Count",
    "Bwd TCP Retransmission Count": "Bwd TCP Retrans. Count",
}

# Domain weights. These can be overridden by passing feature_weights to
# score_report(...). The values are deliberately not equal: they prioritize
# features that are usually both important and controllable by the simulator.
DEFAULT_FEATURE_WEIGHTS: Dict[str, float] = {
    "Flow Duration": 5.0,
    "Total Length of Fwd Packet": 5.0,
    "Flow Bytes/s": 4.0,
    #"Flow IAT Min": 1.5,
    #"Fwd IAT Min": 1.5,
    #"Bwd IAT Min": 0.5,
    "Packet Length Std": 3.0,
    "Fwd Packet Length Max": 3.0,
    "Fwd Packet Length Min": 3.0,
    "Bwd Packet Length Max": 3.0,
    "Bwd Packet Length Min": 3.0,
    "Down/Up Ratio": 2.5,
    #"Bwd Init Win Bytes": 1.0,
    "Bwd Seg Size Min": 2.0,
    "FIN Flag Count": 0.5,
    "SYN Flag Count": 2.0,
    "Fwd TCP Retrans. Count": 2.0,
    "Bwd TCP Retrans. Count": 2.0,
    "Fwd URG Flags": 1.5,
    "Bwd URG Flags": 1.5,
    "Fwd RST Flags": 1.5,
    "Bwd RST Flags": 1.5,
    "CWR Flag Count": 1.5,
    "ECE Flag Count": 1.5,
}

# Feature-specific normalizers avoid exploding percentages when the original
# value is 0 and the simulated value is a small non-zero count.
ABSOLUTE_EPSILON: Dict[str, float] = {
    "Flow Duration": 1.0,
    "Total Length of Fwd Packet": 1.0,
    "Flow Bytes/s": 1.0,
    #"Flow IAT Min": 1.0,
    #"Fwd IAT Min": 1.0,
    #"Bwd IAT Min": 1.0,
    "Packet Length Std": 1.0,
    "Down/Up Ratio": 0.1,
    #"Bwd Init Win Bytes": 1.0,
    "Bwd Seg Size Min": 1.0,
}

FLAG_OR_COUNT_FEATURES = {
    "Fwd URG Flags",
    "Bwd URG Flags",
    "Fwd RST Flags",
    "Bwd RST Flags",
    "FIN Flag Count",
    "SYN Flag Count",
    "CWR Flag Count",
    "ECE Flag Count",
    "Fwd TCP Retrans. Count",
    "Bwd TCP Retrans. Count",
}


def _safe_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return x


def _canonical_feature(name: Any) -> str:
    raw = str(name or "").strip()
    return FEATURE_ALIASES.get(raw, raw)


def _relative_error_pct(original: float, simulated: float, feature: str) -> float:
    """Symmetric-ish relative error in percent, robust around zero.

    Uses max(abs(original), abs(simulated), epsilon) as denominator. This avoids
    infinite errors when the original value is zero but the simulation produces a
    small non-zero value. For flag/count features, a 0-vs-nonzero mismatch still
    receives a strong penalty because denominator defaults to at least 1.
    """
    eps = ABSOLUTE_EPSILON.get(feature, 1.0 if feature in FLAG_OR_COUNT_FEATURES else 1e-9)
    denom = max(abs(original), abs(simulated), eps)
    return abs(simulated - original) / denom * 100.0


def _component_error_from_detail(row: Dict[str, Any], feature: str) -> Optional[float]:
    original = _safe_number(row.get("original_value"))
    simulated = _safe_number(row.get("simulated_value"))
    if original is not None and simulated is not None:
        return _relative_error_pct(original, simulated, feature)

    # Fallback to already computed relative error if values are missing.
    rel = _safe_number(row.get("relative_error_pct"))
    if rel is not None:
        return abs(rel)

    abs_err = _safe_number(row.get("absolute_error"))
    if abs_err is not None:
        eps = ABSOLUTE_EPSILON.get(feature, 1.0)
        return abs(abs_err) / eps * 100.0

    return None


def _component_error_from_summary(row: Dict[str, Any], metric: str) -> Optional[float]:
    value = _safe_number(row.get(metric))
    if value is None:
        value = _safe_number(row.get("mean_relative_error_pct"))
    if value is None:
        value = _safe_number(row.get("mae"))
    if value is None:
        return None
    return abs(value)


def _score_flow_details(
    rows: Iterable[Dict[str, Any]],
    feature_weights: Dict[str, float],
    missing_feature_penalty: float,
) -> Dict[str, Any]:
    # Group rows by pair_id so every flow contributes one score. This prevents a
    # single problematic feature across all flows from hiding per-flow failures.
    by_flow: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        feature = _canonical_feature(row.get("feature"))
        if feature not in TARGET_FEATURE_SET:
            continue
        pair_id = str(row.get("pair_id", row.get("Endpoint Flusso", "__all__")))
        by_flow[pair_id].append(row)

    if not by_flow:
        return {"score": float("inf"), "reason": "no_target_features_in_flow_details"}

    flow_scores = []
    feature_contrib: Dict[str, Dict[str, float]] = defaultdict(lambda: {"weighted_sum": 0.0, "weight": 0.0, "count": 0.0})

    for pair_id, flow_rows in by_flow.items():
        seen = set()
        weighted_sum = 0.0
        total_weight = 0.0

        for row in flow_rows:
            feature = _canonical_feature(row.get("feature"))
            err = _component_error_from_detail(row, feature)
            if err is None:
                continue
            weight = feature_weights.get(feature, 1.0)
            weighted_sum += weight * err
            total_weight += weight
            seen.add(feature)

            feature_contrib[feature]["weighted_sum"] += weight * err
            feature_contrib[feature]["weight"] += weight
            feature_contrib[feature]["count"] += 1.0

        # Penalize missing target features so incomplete reports do not look good.
        missing = TARGET_FEATURE_SET - seen
        if missing:
            missing_weight = sum(feature_weights.get(f, 1.0) for f in missing)
            weighted_sum += missing_feature_penalty * missing_weight
            total_weight += missing_weight

        score = weighted_sum / total_weight if total_weight > 0 else float("inf")
        flow_scores.append({
            "pair_id": pair_id,
            "score": score,
            "features_seen": len(seen),
            "features_missing": len(TARGET_FEATURE_SET - seen),
        })

    overall = sum(item["score"] for item in flow_scores) / len(flow_scores)
    top_features = []
    for feature, values in feature_contrib.items():
        if values["weight"] <= 0:
            continue
        top_features.append({
            "feature": feature,
            "component": values["weighted_sum"] / values["weight"],
            "weight": feature_weights.get(feature, 1.0),
            "count": int(values["count"]),
        })
    top_features.sort(key=lambda x: x["component"] * x["weight"], reverse=True)
    flow_scores.sort(key=lambda x: x["score"], reverse=True)

    return {
        "score": overall,
        "mode": "flow_details",
        "optimized_features": list(TARGET_FEATURES),
        "num_flows": len(flow_scores),
        "top_features": top_features[:15],
        "worst_flows": flow_scores[:10],
    }


def _score_summary(
    rows: Iterable[Dict[str, Any]],
    feature_weights: Dict[str, float],
    metric: str,
    missing_feature_penalty: float,
) -> Dict[str, Any]:
    weighted_sum = 0.0
    total_weight = 0.0
    seen = set()
    feature_scores = []

    for row in rows:
        feature = _canonical_feature(row.get("feature"))
        if feature not in TARGET_FEATURE_SET:
            continue
        err = _component_error_from_summary(row, metric)
        if err is None:
            continue
        weight = feature_weights.get(feature, 1.0)
        weighted_sum += weight * err
        total_weight += weight
        seen.add(feature)
        feature_scores.append({
            "feature": feature,
            "component": err,
            "weight": weight,
            "group": row.get("group", ""),
        })

    missing = TARGET_FEATURE_SET - seen
    if missing:
        missing_weight = sum(feature_weights.get(f, 1.0) for f in missing)
        weighted_sum += missing_feature_penalty * missing_weight
        total_weight += missing_weight

    if total_weight <= 0:
        return {"score": float("inf"), "reason": "no_target_features_in_summary"}

    feature_scores.sort(key=lambda x: x["component"] * x["weight"], reverse=True)
    return {
        "score": weighted_sum / total_weight,
        "mode": "summary",
        "optimized_features": list(TARGET_FEATURES),
        "features_seen": len(seen),
        "features_missing": len(missing),
        "missing_features": sorted(missing),
        "top_features": feature_scores[:15],
    }


def score_report(
    report: Dict[str, Any],
    group_weights: Optional[Dict[str, float]] = None,
    feature_weights: Optional[Dict[str, float]] = None,
    metric: str = "mean_relative_error_pct",
    signed_error_penalty: float = 0.0,
    missing_feature_penalty: float = 250.0,
) -> Dict[str, Any]:
    """Compute optimization score for a comparison report.

    Parameters kept compatible with the previous objective.py:
      - group_weights is accepted but ignored because this objective is driven by
        a fixed feature list rather than broad groups.
      - signed_error_penalty is accepted but ignored by default because the score
        uses absolute mismatch.
      - metric is used only for summary fallback.

    Returns a dictionary with at least:
      - score: float, lower is better.
      - top_features: largest error contributors.
    """
    weights = {**DEFAULT_FEATURE_WEIGHTS, **(feature_weights or {})}

    flow_rows = report.get("flow_details") or []
    if flow_rows:
        result = _score_flow_details(flow_rows, weights, missing_feature_penalty)
        if math.isfinite(result.get("score", float("inf"))):
            return result

    summary_rows = report.get("summary") or []
    return _score_summary(summary_rows, weights, metric, missing_feature_penalty)
