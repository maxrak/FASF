# Parametri ottimizzazione

ITERATIONS = 30
SLEEP_TIME = 30  # secondi attesa pipeline

PARAM_BOUNDS = {
    "pkt_size_scale": (0.5, 2.0),
    "pkt_size_sigma": (0.5, 2.0),
    "burst_size_p": (0.1, 0.9),
    "idle_scale": (0.01, 1.0),
    "iat_rate": (50, 300)
}

LOSS_FILE = "/results/loss.txt"
PARAM_FILE = "/shared/params_tmp.json"
TARGET_FEATURE_FILE = "/features/target.csv"