import numpy as np
from config import FEATURES_TO_COMPARE, FEATURE_WEIGHTS


def normalized_error(a, b):
    if a == 0 and b == 0:
        return 0
    return abs(a - b) / (abs(a) + 1e-6)


def compute_loss(target_row, generated_row):
    loss = 0

    for feat in FEATURES_TO_COMPARE:
        if feat in target_row and feat in generated_row:

            t = target_row[feat]
            g = generated_row[feat]

            err = normalized_error(t, g)

            weight = FEATURE_WEIGHTS.get(feat, 1.0)

            loss += weight * err

    return loss