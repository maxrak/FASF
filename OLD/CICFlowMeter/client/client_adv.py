import pandas as pd
import time
import random
from scapy.all import *

SERVER_PORT = 9000


# ---------------------------
# HANDSHAKE TCP
# ---------------------------
def tcp_handshake(src_ip, dst_ip, sport):
    seq = random.randint(0, 100000)

    syn = IP(src=src_ip, dst=dst_ip) / TCP(sport=sport, dport=SERVER_PORT, flags="S", seq=seq)
    synack = sr1(syn, timeout=1, verbose=0)

    if synack is None:
        return None, None

    ack = IP(src=src_ip, dst=dst_ip) / TCP(
        sport=sport,
        dport=SERVER_PORT,
        flags="A",
        seq=synack.ack,
        ack=synack.seq + 1
    )
    send(ack, verbose=0)

    return synack.ack, synack.seq + 1


# ---------------------------
# GENERA BURST ACTIVE
# ---------------------------
def generate_active_period(row, seq, ack, ip_client, ip_server, sport):
    active_mean = float(row["Active Mean"]) / 1e6
    active_std = float(row["Active Std"]) / 1e6

    duration = max(0.01, random.gauss(active_mean, active_std))

    pkt_mean = float(row["Fwd Packet Length Mean"])
    pkt_std = float(row["Fwd Packet Length Std"])

    start = time.time()

    while time.time() - start < duration:
        size = max(1, int(random.gauss(pkt_mean, pkt_std)))

        pkt = IP(src=ip_client, dst=ip_server) / TCP(
            sport=sport,
            dport=SERVER_PORT,
            flags="PA",
            seq=seq,
            ack=ack
        ) / Raw(load=bytes(size))

        send(pkt, verbose=0)

        seq += size

        # IAT corto (burst)
        time.sleep(random.uniform(0.001, 0.01))

    return seq


# ---------------------------
# GENERA IDLE
# ---------------------------
def generate_idle_period(row):
    idle_mean = float(row["Idle Mean"]) / 1e6
    idle_std = float(row["Idle Std"]) / 1e6

    duration = max(0.01, random.gauss(idle_mean, idle_std))

    print(f"[IDLE] {duration:.2f}s")
    time.sleep(duration)


# ---------------------------
# GENERA FLOW COMPLETO
# ---------------------------
def generate_flow(row, ip_client, ip_server):
    sport = random.randint(1024, 65535)

    seq, ack = tcp_handshake(ip_client, ip_server, sport)

    if seq is None:
        print("[!] Handshake fallito")
        return None

    flow_start = time.time()

    total_duration = float(row["Flow Duration"]) / 1e6

    packets_sent = 0

    while time.time() - flow_start < total_duration:

        # ACTIVE
        seq = generate_active_period(row, seq, ack, ip_client, ip_server, sport)

        # IDLE
        generate_idle_period(row)

        packets_sent += 1

    flow_end = time.time()

    return {
        "generated_duration": flow_end - flow_start,
        "packets_sent": packets_sent
    }


# ---------------------------
# MAIN CLIENT + DATASET OUTPUT
# ---------------------------
def start_client(csv_file, ip_client, ip_server, output_file="generated_flows.csv"):
    df = pd.read_csv(csv_file)

    flows = df[
        ((df["Source IP"] == ip_client) & (df["Destination IP"] == ip_server)) |
        ((df["Source IP"] == ip_server) & (df["Destination IP"] == ip_client))
    ]

    print(f"[+] Flussi selezionati: {len(flows)}")

    results = []

    for _, row in flows.iterrows():
        result = generate_flow(row, ip_client, ip_server)

        if result:
            results.append(result)

    # salva dataset generato
    out_df = pd.DataFrame(results)
    out_df.to_csv(output_file, index=False)

    print(f"[+] Dataset salvato in {output_file}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Uso: python client.py flows.csv IPclient IPserver")
        exit(1)

    start_client(sys.argv[1], sys.argv[2], sys.argv[3])