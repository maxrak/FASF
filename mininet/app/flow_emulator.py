import pandas as pd
import time
import random
import numpy as np
import json
import flow_emulator as femul
from scapy.all import *

SERVER_PORT = 9000


# ---------------------------
# LOAD PARAMS (da optimizer)
# ---------------------------
def load_params():
    try:
        with open("params_tmp.json") as f:
            params = json.load(f)
            print("[+] Parametri caricati:", params)
            return params
    except:
        print("[!] Nessun file parametri trovato, uso default")
        return None


# ---------------------------
# DISTRIBUZIONI (controllate)
# ---------------------------
def sample_packet_size(mean, std, params):
    scale = params.get("pkt_size_scale", 1.0) if params else 1.0
    sigma_factor = params.get("pkt_size_sigma", 1.0) if params else 1.0

    mean *= scale
    std *= sigma_factor

    sigma = np.sqrt(np.log(1 + (std / mean) ** 2)) if mean > 0 else 1
    mu = np.log(mean) - sigma**2 / 2 if mean > 0 else 1

    return max(1, int(np.random.lognormal(mu, sigma)))


def sample_iat(rate, params):
    rate = params.get("iat_rate", rate) if params else rate
    return np.random.exponential(1.0 / rate) if rate > 0 else 0.01


def sample_idle(scale, params):
    scale = params.get("idle_scale", scale) if params else scale
    return (np.random.pareto(1.5) + 1) * scale


def sample_burst_size(params):
    p = params.get("burst_size_p", 0.3) if params else 0.3
    return int(np.random.geometric(p=p))


# ---------------------------
# TCP HANDSHAKE
# ---------------------------
def tcp_handshake(src_ip, dst_ip, sport):
    seq = random.randint(0, 100000)

    syn = IP(src=src_ip, dst=dst_ip) / TCP(
        sport=sport, dport=SERVER_PORT, flags="S", seq=seq
    )
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
def generate_burst(row, seq, ack, ip_client, ip_server, sport, params):

    burst_size = sample_burst_size(params)

    pkt_mean = float(row["Fwd Packet Length Mean"])
    pkt_std = float(row["Fwd Packet Length Std"])

    base_rate = float(row.get("Flow Packets/s", 200))

    for _ in range(burst_size):

        size = sample_packet_size(pkt_mean, pkt_std, params)

        pkt = IP(src=ip_client, dst=ip_server) / TCP(
            sport=sport,
            dport=SERVER_PORT,
            flags="PA",
            seq=seq,
            ack=ack
        ) / Raw(load=bytes(size))

        send(pkt, verbose=0)

        seq += size

        # intra-burst IAT
        iat = sample_iat(base_rate * 5, params)
        time.sleep(min(iat, 0.01))

    return seq, burst_size


# ---------------------------
# FLOW GENERATION
# ---------------------------
def generate_flow(row, ip_client, ip_server, params):

    sport = random.randint(1024, 65535)

    seq, ack = tcp_handshake(ip_client, ip_server, sport)

    if seq is None:
        print("[!] Handshake fallito")
        return None

    flow_duration = float(row["Flow Duration"]) / 1e6
    idle_scale = float(row["Idle Mean"]) / 1e6

    start = time.time()

    total_packets = 0
    total_bursts = 0

    while time.time() - start < flow_duration:

        seq, bsize = generate_burst(
            row, seq, ack, ip_client, ip_server, sport, params
        )

        total_packets += bsize
        total_bursts += 1

        idle_time = sample_idle(idle_scale, params)
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
def start_client(csv_file, ip_client, ip_server, params, output="/results/burst_dataset.csv"):

    df = pd.read_csv(csv_file)

    params = load_params(params)

    # Gestisci entrambe le convenzioni di naming
    if "Source IP" in df.columns and "Destination IP" in df.columns:
        src_col, dst_col = "Source IP", "Destination IP"
    elif "Src IP" in df.columns and "Dst IP" in df.columns:
        src_col, dst_col = "Src IP", "Dst IP"
    else:
        print(f"[!] ERRORE: Colonne IP non trovate. Colonne disponibili: {df.columns.tolist()}")
        return
    
    flows = df[
        ((df[src_col] == ip_client) & (df[dst_col] == ip_server)) |
        ((df[src_col] == ip_server) & (df[dst_col] == ip_client))
    ]

    print(f"[+] CSV: {csv_file}")
    print(f"[+] Ricerca flussi tra {ip_client} <-> {ip_server}")
    print(f"[+] Colonne usate: {src_col}, {dst_col}")
    print(f"[+] Righe totali nel CSV: {len(df)}")
    print(f"[+] Flussi selezionati: {len(flows)}")
    
    if len(flows) == 0:
        print(f"[!] ATTENZIONE: Nessun flusso trovato!")
        print(f"[!] IP unici nel CSV: {df[src_col].unique().tolist()}")
        # Crea comunque un file vuoto per evitare errori
        pd.DataFrame([]).to_csv(output, index=False)
        return

    results = []

    for i, (_, row) in enumerate(flows.iterrows()):
        print(f"[FLOW {i}]")

        r = generate_flow(row, ip_client, ip_server, params)

        if r:
            results.append(r)

    pd.DataFrame(results).to_csv(output, index=False)

    print(f"[+] Dataset salvato in {output}")

    ip_client = sys.argv[2]
    ip_server = sys.argv[3]
    
    # Nome file univoco per ogni coppia di IP
    output_file = f"/results/burst_dataset_{ip_client.replace('.', '_')}_{ip_server.replace('.', '_')}.csv"
    
    start_client(sys.argv[1], ip_client, ip_server, output_file, params)
# ---------------------------
# ENTRYPOINT
# ---------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 5:
        print("Uso: python client.py flows.csv IPclient IPserver params.config")
        exit(1)

    start_client(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    