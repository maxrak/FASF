import pandas as pd
import time
import random
import numpy as np
from scapy.all import *

SERVER_PORT = 9000


# ---------------------------
# DISTRIBUZIONI REALISTICHE
# ---------------------------

def sample_packet_size(mean, std):
    # log-normal approximation
    sigma = np.sqrt(np.log(1 + (std / mean) ** 2)) if mean > 0 else 1
    mu = np.log(mean) - (sigma**2) / 2 if mean > 0 else 1
    return max(1, int(np.random.lognormal(mu, sigma)))


def sample_iat(rate):
    # exponential (Poisson process)
    return np.random.exponential(1.0 / rate) if rate > 0 else 0.01


def sample_pareto(scale, shape=1.5):
    return (np.random.pareto(shape) + 1) * scale


# ---------------------------
# TCP HANDSHAKE
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
# ACTIVE PERIOD (burst)
# ---------------------------
def generate_active(row, seq, ack, ip_client, ip_server, sport):

    scale = float(row["Active Mean"]) / 1e6
    duration = sample_pareto(scale)

    pkt_mean = float(row["Fwd Packet Length Mean"])
    pkt_std = float(row["Fwd Packet Length Std"])

    rate = float(row["Flow Packets/s"]) if "Flow Packets/s" in row else 100

    start = time.time()

    while time.time() - start < duration:

        size = sample_packet_size(pkt_mean, pkt_std)

        pkt = IP(src=ip_client, dst=ip_server) / TCP(
            sport=sport,
            dport=SERVER_PORT,
            flags="PA",
            seq=seq,
            ack=ack
        ) / Raw(load=bytes(size))

        send(pkt, verbose=0)

        seq += size

        iat = sample_iat(rate)
        time.sleep(min(iat, 0.1))  # evita sleep troppo lunghi

    return seq


# ---------------------------
# IDLE PERIOD
# ---------------------------
def generate_idle(row):
    scale = float(row["Idle Mean"]) / 1e6
    duration = sample_pareto(scale)

    print(f"[IDLE realistico] {duration:.2f}s")
    time.sleep(min(duration, 5))  # clamp per sicurezza


# ---------------------------
# FLOW COMPLETO
# ---------------------------
def generate_flow(row, ip_client, ip_server):
    sport = random.randint(1024, 65535)

    seq, ack = tcp_handshake(ip_client, ip_server, sport)

    if seq is None:
        print("[!] Handshake fallito")
        return None

    flow_duration = float(row["Flow Duration"]) / 1e6

    start = time.time()
    packets = 0

    while time.time() - start < flow_duration:

        seq = generate_active(row, seq, ack, ip_client, ip_server, sport)
        generate_idle(row)

        packets += 1

    return {
        "duration_generated": time.time() - start,
        "packets_estimated": packets
    }


# ---------------------------
# MAIN
# ---------------------------
def start_client(csv_file, ip_client, ip_server, output="generated_realistic.csv"):
    df = pd.read_csv(csv_file)

    flows = df[
        ((df["Source IP"] == ip_client) & (df["Destination IP"] == ip_server)) |
        ((df["Source IP"] == ip_server) & (df["Destination IP"] == ip_client))
    ]

    print(f"[+] Flussi: {len(flows)}")

    results = []

    for _, row in flows.iterrows():
        r = generate_flow(row, ip_client, ip_server)
        if r:
            results.append(r)

    pd.DataFrame(results).to_csv(output, index=False)
    print(f"[+] Salvato: {output}")


if __name__ == "__main__":
    import sys

    start_client(sys.argv[1], sys.argv[2], sys.argv[3])