from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Optional

DEFAULT_GROUP_WEIGHTS = {
    'conteggi pacchetti': 3.0,
    'durata/timing': 2.5,
    'dimensioni/lunghezze': 2.0,
    'throughput/rate': 1.0,
    'TCP/flag/window': 1.0,
    'identita/topologia': 5.0,
    'altro': 0.7,
}

DEFAULT_FEATURE_WEIGHTS = {
    'Total Fwd Packet': 5.0,
    'Total Bwd packets': 5.0,
    'Total Length of Fwd Packet': 4.0,
    'Total Length of Bwd Packet': 4.0,
    'Flow Duration': 4.0,
    'Fwd IAT Total': 3.0,
    'Bwd IAT Total': 3.0,
    'Fwd Packet Length Mean': 2.5,
    'Bwd Packet Length Mean': 2.5,
    'Fwd Packet Length Std': 2.0,
    'Bwd Packet Length Std': 2.0,
    'Flow Packets/s': 2.0,
    'Fwd Packets/s': 2.0,
    'Bwd Packets/s': 2.0,
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


def score_report(
    report: Dict[str, Any],
    group_weights: Optional[Dict[str, float]] = None,
    feature_weights: Optional[Dict[str, float]] = None,
    metric: str = 'mean_relative_error_pct',
    signed_error_penalty: float = 0.0,
) -> Dict[str, Any]:
    group_weights = {**DEFAULT_GROUP_WEIGHTS, **(group_weights or {})}
    feature_weights = {**DEFAULT_FEATURE_WEIGHTS, **(feature_weights or {})}
    rows: Iterable[Dict[str, Any]] = report.get('summary') or []

    weighted_sum = 0.0
    total_weight = 0.0
    feature_scores = []

    for row in rows:
        feature = str(row.get('feature', ''))
        group = str(row.get('group', 'altro'))
        value = _safe_number(row.get(metric))
        if value is None:
            value = _safe_number(row.get('mae'))
        if value is None:
            continue

        w = group_weights.get(group, 1.0) * feature_weights.get(feature, 1.0)
        signed = abs(_safe_number(row.get('mean_signed_error')) or 0.0)
        component = value + signed_error_penalty * signed
        weighted_sum += w * component
        total_weight += w
        feature_scores.append({'feature': feature, 'group': group, 'metric': value, 'weight': w, 'component': component})

    if total_weight <= 0:
        return {'score': float('inf'), 'weighted_sum': weighted_sum, 'total_weight': total_weight, 'top_features': []}

    feature_scores.sort(key=lambda x: x['weight'] * x['component'], reverse=True)
    return {
        'score': weighted_sum / total_weight,
        'weighted_sum': weighted_sum,
        'total_weight': total_weight,
        'top_features': feature_scores[:15],
    }
