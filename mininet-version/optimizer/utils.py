import json
import random


def sample_params(bounds):
    return {
        k: random.uniform(v[0], v[1])
        for k, v in bounds.items()
    }


def save_params(params, path):
    with open(path, "w") as f:
        json.dump(params, f)


def load_last_loss(path):
    try:
        with open(path) as f:
            lines = f.readlines()
            if not lines:
                return None
            return float(lines[-1].strip().split(",")[1])
    except:
        return None