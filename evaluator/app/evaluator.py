import time
import pandas as pd
from utils import load_csv_safe, get_generated_files
from loss import compute_loss
from config import TARGET_FILE, GENERATED_DIR, LOSS_FILE


def evaluate():

    print("[+] Carico target")

    target_df = load_csv_safe(TARGET_FILE)

    if target_df is None:
        print("[!] Target non trovato")
        return

    target_row = target_df.iloc[0].to_dict()

    print("[+] Cerco file generati")

    files = get_generated_files(GENERATED_DIR)

    if not files:
        print("[!] Nessun file generato")
        return

    for f in files:
        print(f"[+] Analizzo {f}")

        gen_df = load_csv_safe(f)

        if gen_df is None:
            continue

        gen_row = gen_df.iloc[0].to_dict()

        loss = compute_loss(target_row, gen_row)

        print(f"[LOSS] {f}: {loss:.4f}")

        with open(LOSS_FILE, "a") as out:
            out.write(f"{f},{loss}\n")


if __name__ == "__main__":

    while True:
        evaluate()
        time.sleep(10)