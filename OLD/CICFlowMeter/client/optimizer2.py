import json
import random
import time

def random_params():
    return {
        "pkt_size_scale": random.uniform(0.5, 2),
        "pkt_size_sigma": random.uniform(0.5, 2),
        "burst_size_p": random.uniform(0.1, 0.9),
        "idle_scale": random.uniform(0.01, 1),
        "iat_rate": random.uniform(50, 300)
    }


for i in range(50):

    params = random_params()

    with open("/shared/params_tmp.json", "w") as f:
        json.dump(params, f)

    print(f"[ITER {i}] params={params}")

    # aspetta pipeline
    time.sleep(20)