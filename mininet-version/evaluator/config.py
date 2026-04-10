FEATURES_TO_COMPARE = [
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Fwd Packet Length Mean",
    "Fwd Packet Length Std",
    "Flow IAT Mean",
    "Flow IAT Std",
    "Idle Mean",
    "Active Mean"
]

FEATURE_WEIGHTS = {
    "Flow Duration": 1.0,
    "Total Fwd Packets": 1.0,
    "Total Backward Packets": 1.0,
    "Fwd Packet Length Mean": 0.5,
    "Fwd Packet Length Std": 0.5,
    "Flow IAT Mean": 0.7,
    "Flow IAT Std": 0.7,
    "Idle Mean": 0.8,
    "Active Mean": 0.8
}

TARGET_FILE = "/features/target.csv"
GENERATED_DIR = "/features"
LOSS_FILE = "/results/loss.txt"