import numpy as np
import pandas as pd
import subprocess
import random


# ---------------------------
# FUNZIONE LOSS
# ---------------------------
def compute_loss(target, generated):
    weights = {
        "Flow Duration": 1.0,
        "Total Fwd Packets": 1.0,
        "Fwd Packet Length Mean": 0.5,
        "Flow IAT Mean": 0.5,
        "Idle Mean": 0.5
    }

    loss = 0

    for key, w in weights.items():
        if key in target and key in generated:
            loss += w * abs(target[key] - generated[key])

    return loss


# ---------------------------
# SIMULA TRAFFICO + ESTRAI FEATURE
# ---------------------------
def evaluate_params(params, flow_row):

    # salva parametri temporanei
    param_file = "params_tmp.json"

    import json
    with open(param_file, "w") as f:
        json.dump(params, f)

    # genera traffico (usa il tuo client avanzato modificato)
    subprocess.run([
        "python",
        "client_scapy_burst.py",
        "single_flow.csv",
        flow_row["Source IP"],
        flow_row["Destination IP"]
    ])

    # estrai feature con CICFlowMeter (assunto installato)
    subprocess.run([
        "java", "-jar", "CICFlowMeter.jar",
        "generated.pcap",
        "output.csv"
    ])

    df = pd.read_csv("output.csv")

    if len(df) == 0:
        return float("inf")

    generated = df.iloc[0].to_dict()

    return compute_loss(flow_row, generated)


# ---------------------------
# RANDOM SEARCH (baseline)
# ---------------------------
def random_search(flow_row, iterations=30):

    best_params = None
    best_loss = float("inf")

    for i in range(iterations):

        params = {
            "pkt_size_scale": random.uniform(0.5, 2.0),
            "pkt_size_sigma": random.uniform(0.5, 2.0),
            "burst_rate": random.uniform(50, 500),
            "burst_size_p": random.uniform(0.1, 0.9),
            "idle_scale": random.uniform(0.001, 1.0),
            "iat_rate": random.uniform(50, 500)
        }

        loss = evaluate_params(params, flow_row)

        print(f"[{i}] loss={loss:.3f}")

        if loss < best_loss:
            best_loss = loss
            best_params = params

    return best_params, best_loss