import pandas as pd
import time
import random
import numpy as np
from scapy.all import *

SERVER_PORT = 9000


# ---------------------------
# DISTRIBUZIONI
# ---------------------------

def sample_packet_size(mean, std):
    sigma = np.sqrt(np.log(1 + (std / mean) ** 2)) if mean > 0 else 1
    mu = np.log(mean) - sigma**2 / 2 if mean > 0 else 1
    return max(1, int(np.random.lognormal(mu, sigma)))


def sample_iat_fast(rate):
    return np.random.exponential(1.0 / rate)


def sample_idle(scale):
    return (np.random.pareto(1.5) + 1) * scale


def sample_burst_size():
    # heavy tail: molti piccoli burst, pochi grandi
    return int(np.random.geometric(p=0.3))


# ---------------------------
# HANDSHAKE
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
# BURST GENERATOR
# ---------------------------
def generate_burst(row, seq, ack, ip_client, ip_server, sport):

    burst_size = sample_burst_size()

    pkt_mean = float(row["Fwd Packet Length Mean"])
    pkt_std = float(row["Fwd Packet Length Std"])

    rate = float(row["Flow Packets/s"]) if "Flow Packets/s" in row else 200

    for _ in range(burst_size):

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

        # intra-burst IAT (molto piccolo)
        iat = sample_iat_fast(rate * 5)  # burst più veloce del rate medio
        time.sleep(min(iat, 0.01))

    return seq, burst_size


# ---------------------------
# FLOW COMPLETO
# ---------------------------
def generate_flow(row, ip_client, ip_server):

    sport = random.randint(1024, 65535)
    seq, ack = tcp_handshake(ip_client, ip_server, sport)

    if seq is None:
        return None

    flow_duration = float(row["Flow Duration"]) / 1e6
    idle_scale = float(row["Idle Mean"]) / 1e6

    start = time.time()

    total_packets = 0
    total_bursts = 0

    while time.time() - start < flow_duration:

        # BURST
        seq, bsize = generate_burst(row, seq, ack, ip_client, ip_server, sport)
        total_packets += bsize
        total_bursts += 1

        # GAP tra burst (idle)
        idle_time = sample_idle(idle_scale)
        time.sleep(min(idle_time, 3))

    return {
        "duration": time.time() - start,
        "packets": total_packets,
        "bursts": total_bursts,
        "avg_burst_size": total_packets / max(total_bursts, 1)
    }


# ---------------------------
# MAIN
# ---------------------------
def start_client(csv_file, ip_client, ip_server, output="burst_dataset.csv"):

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
    print(f"[+] Salvato dataset: {output}")


if __name__ == "__main__":
    import sys
    start_client(sys.argv[1], sys.argv[2], sys.argv[3])