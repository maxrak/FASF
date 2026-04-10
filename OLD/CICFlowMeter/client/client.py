import socket
import pandas as pd
import time
import threading
import random

SERVER_PORT = 9000


def generate_flow(row, ip_client, ip_server):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip_server, SERVER_PORT))

        # === FEATURE PRINCIPALI ===
        total_fwd_packets = int(row["Total Fwd Packets"])
        total_bwd_packets = int(row["Total Backward Packets"])
        flow_duration = float(row["Flow Duration"]) / 1e6  # microsec → sec

        pkt_len_mean = float(row["Fwd Packet Length Mean"])
        pkt_len_std = float(row["Fwd Packet Length Std"])

        if total_fwd_packets <= 0:
            return

        # IAT medio
        iat = flow_duration / total_fwd_packets if total_fwd_packets > 0 else 0.01

        print(f"[FLOW] packets={total_fwd_packets}, duration={flow_duration:.2f}s")

        for _ in range(total_fwd_packets):
            # genera dimensione pacchetto
            size = max(1, int(random.gauss(pkt_len_mean, pkt_len_std)))

            payload = bytes(size)

            s.sendall(payload)

            # ricezione opzionale (per simulare backward)
            try:
                s.recv(64)
            except:
                pass

            time.sleep(iat)

        s.close()

    except Exception as e:
        print(f"[!] Errore flow: {e}")


def start_client(csv_file, ip_client, ip_server):
    df = pd.read_csv(csv_file)

    # Filtra flussi
    flows = df[
        ((df["Source IP"] == ip_client) & (df["Destination IP"] == ip_server)) |
        ((df["Source IP"] == ip_server) & (df["Destination IP"] == ip_client))
    ]

    print(f"[+] Flussi trovati: {len(flows)}")

    threads = []

    for _, row in flows.iterrows():
        t = threading.Thread(target=generate_flow, args=(row, ip_client, ip_server))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Uso: python client.py flows.csv IPclient IPserver")
        exit(1)

    csv_file = sys.argv[1]
    ip_client = sys.argv[2]
    ip_server = sys.argv[3]

    start_client(csv_file, ip_client, ip_server)