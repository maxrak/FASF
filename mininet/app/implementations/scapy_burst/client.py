import pandas as pd
import time
import random
import numpy as np
import json
import sys
import logging
import os
from datetime import datetime
from scapy.all import *

# Logger globale (verrà configurato in start_client)
logger = None


# ---------------------------
# LOAD PARAMS (da optimizer)
# ---------------------------
def load_params(config_file=None):
    """Carica parametri dal file di configurazione specificato o da params_tmp.json"""
    if config_file is None:
        config_file = "params_tmp.json"
    
    try:
        with open(config_file) as f:
            params = json.load(f)
            print(f"[+] Parametri caricati da {config_file}:", params)
            return params
    except FileNotFoundError:
        print(f"[!] File {config_file} non trovato, uso default")
        return None
    except Exception as e:
        print(f"[!] Errore caricamento parametri da {config_file}: {e}")
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
def tcp_handshake(src_ip, dst_ip, sport, dport):
    seq = random.randint(0, 100000)

    syn = IP(src=src_ip, dst=dst_ip) / TCP(
        sport=sport, dport=dport, flags="S", seq=seq
    )
    
    if logger:
        logger.info(f"[HANDSHAKE] Invio SYN: {src_ip}:{sport} -> {dst_ip}:{dport} (seq={seq})")
    
    synack = sr1(syn, timeout=1, verbose=0)

    if synack is None:
        if logger:
            logger.warning(f"[HANDSHAKE] Nessuna risposta SYN-ACK da {dst_ip}:{dport}")
        return None, None
    
    if logger:
        logger.info(f"[HANDSHAKE] Ricevuto SYN-ACK: {dst_ip}:{dport} -> {src_ip}:{sport} (seq={synack[TCP].seq}, ack={synack[TCP].ack})")

    ack = IP(src=src_ip, dst=dst_ip) / TCP(
        sport=sport,
        dport=dport,
        flags="A",
        seq=synack.ack,
        ack=synack.seq + 1
    )
    
    if logger:
        logger.info(f"[HANDSHAKE] Invio ACK: {src_ip}:{sport} -> {dst_ip}:{dport} (seq={synack.ack}, ack={synack.seq + 1})")
    
    send(ack, verbose=0)

    return synack.ack, synack.seq + 1


# ---------------------------
# BURST GENERATOR
# ---------------------------
def generate_burst(row, seq, ack, ip_client, ip_server, sport, dport, params):

    burst_size = sample_burst_size(params)
    
    if logger:
        logger.debug(f"[BURST] Generazione burst di {burst_size} pacchetti")

    pkt_mean = float(row["Fwd Packet Length Mean"])
    pkt_std = float(row["Fwd Packet Length Std"])

    base_rate = float(row.get("Flow Packets/s", 200))

    for i in range(burst_size):

        size = sample_packet_size(pkt_mean, pkt_std, params)

        pkt = IP(src=ip_client, dst=ip_server) / TCP(
            sport=sport,
            dport=dport,
            flags="PA",
            seq=seq,
            ack=ack
        ) / Raw(load=bytes(size))
        
        if logger:
            logger.debug(f"[DATA] Invio pacchetto {i+1}/{burst_size}: {ip_client}:{sport} -> {ip_server}:{dport} (size={size}B, seq={seq}, ack={ack})")

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

    # Leggi le porte dal CSV se disponibili
    # Gestisci sia "Source Port" che "Src Port"
    if "Source Port" in row:
        sport = int(row["Source Port"])
        dport = int(row["Destination Port"])
    elif "Src Port" in row:
        sport = int(row["Src Port"])
        dport = int(row["Dst Port"])
    else:
        # Fallback a porte casuali se non disponibili
        sport = random.randint(1024, 65535)
        dport = 9000
    
    print(f"  Porta sorgente: {sport}, Porta destinazione: {dport}")
    if logger:
        logger.info(f"[FLOW] Avvio flusso {ip_client}:{sport} -> {ip_server}:{dport}")

    seq, ack = tcp_handshake(ip_client, ip_server, sport, dport)

    if seq is None:
        print("[!] Handshake fallito")
        if logger:
            logger.error(f"[FLOW] Handshake fallito per {ip_client}:{sport} -> {ip_server}:{dport}")
        return None

    flow_duration = float(row["Flow Duration"]) / 1e6
    idle_scale = float(row["Idle Mean"]) / 1e6
    
    if logger:
        logger.info(f"[FLOW] Durata prevista: {flow_duration:.2f}s, Idle mean: {idle_scale:.6f}s")

    start = time.time()

    total_packets = 0
    total_bursts = 0

    while time.time() - start < flow_duration:

        seq, bsize = generate_burst(
            row, seq, ack, ip_client, ip_server, sport, dport, params
        )

        total_packets += bsize
        total_bursts += 1
        
        if logger:
            logger.debug(f"[FLOW] Burst {total_bursts} completato: {bsize} pacchetti inviati")

        idle_time = sample_idle(idle_scale, params)
        if logger:
            logger.debug(f"[FLOW] Idle time: {idle_time:.6f}s")
        time.sleep(min(idle_time, 3))
    
    elapsed = time.time() - start
    if logger:
        logger.info(f"[FLOW] Flusso completato in {elapsed:.2f}s: {total_packets} pacchetti, {total_bursts} burst")

    return {
        "duration": elapsed,
        "packets": total_packets,
        "bursts": total_bursts,
        "avg_burst_size": total_packets / max(total_bursts, 1)
    }


# ---------------------------
# LOGGER SETUP
# ---------------------------
def setup_logger(csv_file, ip_client, debug_enabled=True):
    """Configura il logger per il client"""
    global logger
    
    if not debug_enabled:
        logger = None
        return
    
    # Estrae nome base dal CSV
    csv_basename = os.path.splitext(os.path.basename(csv_file))[0]
    ip_safe = ip_client.replace('.', '_').replace(':', '_')
    
    # Nome file log: {csv_name}_{ip}.log
    log_file = f"/results/{csv_basename}_{ip_safe}.log"
    
    # Configura logger
    logger = logging.getLogger(f'client_{ip_client}')
    logger.setLevel(logging.DEBUG)
    
    # File handler
    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)
    
    # Console handler (solo INFO e superiori)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    logger.info("="*60)
    logger.info(f"CLIENT DEBUG LOG - {csv_basename}")
    logger.info(f"IP Client: {ip_client}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("="*60)
    
    print(f"[+] Log debug salvato in: {log_file}")


# ---------------------------
# MAIN
# ---------------------------
def start_client(csv_file, ip_client, ip_server, output="/results/burst_dataset.csv", config_file=None, debug=True):
    
    # Configura logger
    setup_logger(csv_file, ip_client, debug)
    
    if logger:
        logger.info(f"Avvio client: CSV={csv_file}, Client={ip_client}, Server={ip_server}")
        logger.info(f"Output: {output}, Config: {config_file}")

    df = pd.read_csv(csv_file)

    params = load_params(config_file)
    
    if logger:
        logger.info(f"Parametri caricati: {params}")

    # Gestisci entrambe le convenzioni di naming
    if "Source IP" in df.columns and "Destination IP" in df.columns:
        src_col, dst_col = "Source IP", "Destination IP"
    elif "Src IP" in df.columns and "Dst IP" in df.columns:
        src_col, dst_col = "Src IP", "Dst IP"
    else:
        print(f"[!] ERRORE: Colonne IP non trovate. Colonne disponibili: {df.columns.tolist()}")
        return
    
    flows = df[
        (df[src_col] == ip_client) & (df[dst_col] == ip_server)
    ]

    print(f"[+] CSV: {csv_file}")
    print(f"[+] Ricerca flussi diretti {ip_client} -> {ip_server}")
    print(f"[+] Colonne usate: {src_col}, {dst_col}")
    print(f"[+] Righe totali nel CSV: {len(df)}")
    print(f"[+] Flussi selezionati: {len(flows)}")
    
    if logger:
        logger.info(f"CSV: {csv_file}")
        logger.info(f"Ricerca flussi diretti: {ip_client} -> {ip_server}")
        logger.info(f"Colonne: {src_col}, {dst_col}")
        logger.info(f"Righe totali: {len(df)}, Flussi selezionati: {len(flows)}")
    
    if len(flows) == 0:
        print(f"[!] ATTENZIONE: Nessun flusso trovato!")
        print(f"[!] IP unici nel CSV: {df[src_col].unique().tolist()}")
        if logger:
            logger.warning("Nessun flusso trovato!")
            logger.warning(f"IP unici nel CSV: {df[src_col].unique().tolist()}")
        # Crea comunque un file vuoto per evitare errori
        pd.DataFrame([]).to_csv(output, index=False)
        return

    results = []

    for i, (_, row) in enumerate(flows.iterrows()):
        print(f"[FLOW {i}]")
        if logger:
            logger.info(f"{'='*60}")
            logger.info(f"ELABORAZIONE FLUSSO {i+1}/{len(flows)}")
            logger.info(f"{'='*60}")

        r = generate_flow(row, ip_client, ip_server, params)

        if r:
            results.append(r)
            if logger:
                logger.info(f"Risultato flusso {i}: {r}")

    pd.DataFrame(results).to_csv(output, index=False)

    print(f"[+] Dataset salvato in {output}")
    if logger:
        logger.info(f"Dataset salvato in {output}")
        logger.info(f"Totale flussi processati: {len(results)}/{len(flows)}")
        logger.info("="*60)
        logger.info("ESECUZIONE COMPLETATA")
        logger.info("="*60)


# ---------------------------
# ENTRYPOINT
# ---------------------------
if __name__ == "__main__":

    if len(sys.argv) < 4 or len(sys.argv) > 6:
        print("Uso: python client.py flows.csv IPclient IPserver [config_file] [--no-debug]")
        print("")
        print("Parametri:")
        print("  flows.csv    - File CSV con i flussi da replicare")
        print("  IPclient     - Indirizzo IP del client")
        print("  IPserver     - Indirizzo IP del server")
        print("  config_file  - (opzionale) File di configurazione parametri")
        print("  --no-debug   - (opzionale) Disabilita logging debug")
        print("")
        print("Esempio:")
        print("  python client.py flows.csv 10.0.0.1 10.0.0.2")
        print("  python client.py flows.csv 10.0.0.1 10.0.0.2 config.json")
        print("  python client.py flows.csv 10.0.0.1 10.0.0.2 config.json --no-debug")
        exit(1)

    ip_client = sys.argv[2]
    ip_server = sys.argv[3]
    config_file = None
    debug = True  # Debug abilitato di default
    
    # Parsing argomenti opzionali
    for arg in sys.argv[4:]:
        if arg == "--no-debug":
            debug = False
        else:
            config_file = arg
    
    # Nome file univoco per ogni coppia di IP
    output_file = f"/results/burst_dataset_{ip_client.replace('.', '_')}_{ip_server.replace('.', '_')}.csv"
    
    start_client(sys.argv[1], ip_client, ip_server, output_file, config_file, debug)
