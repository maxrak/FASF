import pandas as pd
import os

def compute_loss(target, generated):
    keys = [
        "Flow Duration",
        "Total Fwd Packets",
        "Fwd Packet Length Mean",
        "Flow IAT Mean",
        "Idle Mean"
    ]

    loss = 0
    for k in keys:
        if k in target and k in generated:
            loss += abs(target[k] - generated[k])

    return loss


target = pd.read_csv("/features/target.csv").iloc[0]

for file in os.listdir("/features"):
    if file.endswith(".csv") and file != "target.csv":
        gen = pd.read_csv(f"/features/{file}").iloc[0]

        loss = compute_loss(target, gen)

        with open("/results/loss.txt", "a") as f:
            f.write(f"{file},{loss}\n")