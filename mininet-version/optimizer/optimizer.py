import time
from config import ITERATIONS, SLEEP_TIME, PARAM_FILE, LOSS_FILE
from utils import save_params, load_last_loss
from search import random_search
from evaluator_interface import wait_for_loss


def optimize():

    best_loss = float("inf")
    best_params = None

    last_loss = load_last_loss(LOSS_FILE)

    for i in range(ITERATIONS):

        print(f"\n[ITER {i}] Generazione parametri...")

        params = random_search()

        save_params(params, PARAM_FILE)

        print("[+] Parametri salvati:", params)

        # aspetta pipeline (Mininet + CIC + evaluator)
        time.sleep(SLEEP_TIME)

        loss = wait_for_loss(last_loss)

        if loss is None:
            print("[!] Nessun loss ricevuto")
            continue

        print(f"[+] Loss: {loss}")

        if loss < best_loss:
            best_loss = loss
            best_params = params
            print("[🔥] Nuovo BEST!")

        last_loss = loss

    print("\n=== RISULTATO FINALE ===")
    print("Best loss:", best_loss)
    print("Best params:", best_params)


if __name__ == "__main__":
    optimize()