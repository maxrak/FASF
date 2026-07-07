import pandas as pd
import time
import random
import numpy as np
import json
import sys
import logging
import os
import socket
import struct
from datetime import datetime

logger = None


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


def _set_linger_rst(sock):
    """DISABILITATO: Causava chiusura con RST invece di FIN, impedendo a cicflowmeter di rilevare i flussi.
    Per una corretta chiusura TCP con FIN, non impostiamo SO_LINGER con timeout 0."""
    # Commentato per permettere chiusura corretta con FIN
    # try:
    #     sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    # except Exception:
    #     pass
    pass


def tcp_handshake(src_ip, dst_ip, sport, dport):
    """
    Stessa interfaccia della versione Scapy.
    Ritorna (sock, None) invece di (seq, ack), perche' lo stato TCP e' gestito dal kernel.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
    _set_linger_rst(s)
    s.settimeout(500.0)

    try:
        s.bind((src_ip, int(sport)))
        if logger:
            logger.info(f"[HANDSHAKE] connect TCP reale: {src_ip}:{sport} -> {dst_ip}:{dport}")
        s.connect((dst_ip, int(dport)))
        if logger:
            logger.info(f"[HANDSHAKE] Connessione stabilita: {src_ip}:{sport} -> {dst_ip}:{dport}")
        return s, None
    except Exception as e:
        if logger:
            logger.error(f"[HANDSHAKE] Fallito {src_ip}:{sport} -> {dst_ip}:{dport}: {e}")
        try:
            s.close()
        except Exception:
            pass
        return None, None


def generate_burst(row, seq, ack, ip_client, ip_server, sport, dport, params):
    """
    Stessa firma della versione Scapy.
    In questa versione seq e' il socket TCP ritornato da tcp_handshake; ack e' ignorato.
    """
    sock = seq
    burst_size = sample_burst_size(params)
    if logger:
        logger.debug(f"[BURST] Generazione burst di {burst_size} segmenti applicativi")

    pkt_mean = float(row["Fwd Packet Length Mean"])
    pkt_std = float(row["Fwd Packet Length Std"])
    base_rate = float(row.get("Flow Packets/s", 200))

    sent_segments = 0
    for i in range(burst_size):
        size = sample_packet_size(pkt_mean, pkt_std, params)
        payload = bytes(size)
        try:
            sock.sendall(payload)
            sent_segments += 1
            if logger:
                logger.debug(f"[DATA] sendall {i+1}/{burst_size}: {ip_client}:{sport} -> {ip_server}:{dport} size={size}B")
        except Exception as e:
            if logger:
                logger.error(f"[DATA] Errore invio: {e}")
            break

        iat = sample_iat(base_rate * 5, params)
        time.sleep(min(iat, 0.01))

    return sock, sent_segments


def generate_flow(row, ip_client, ip_server, params):
    if "Source Port" in row:
        sport = int(row["Source Port"])
        dport = int(row["Destination Port"])
    elif "Src Port" in row:
        sport = int(row["Src Port"])
        dport = int(row["Dst Port"])
    else:
        sport = random.randint(1024, 65535)
        dport = 9000

    print(f"  Porta sorgente: {sport}, Porta destinazione: {dport}")
    if logger:
        logger.info(f"[FLOW] Avvio flusso TCP reale {ip_client}:{sport} -> {ip_server}:{dport}")

    sock, ack = tcp_handshake(ip_client, ip_server, sport, dport)
    if sock is None:
        print("[!] Connessione TCP fallita")
        return None

    flow_duration = float(row["Flow Duration"]) / 1e6
    idle_scale = float(row["Idle Mean"]) / 1e6
    start = time.time()
    total_packets = 0
    total_bursts = 0

    try:
        while time.time() - start < flow_duration:
            sock, bsize = generate_burst(row, sock, ack, ip_client, ip_server, sport, dport, params)
            total_packets += bsize
            total_bursts += 1
            idle_time = sample_idle(idle_scale, params)
            time.sleep(min(idle_time, 3))
            if bsize == 0:
                break
    finally:
        # Chiusura corretta TCP con FIN (four-way handshake)
        try:
            # 1. Invia FIN al server (chiude scrittura)
            sock.shutdown(socket.SHUT_WR)
            if logger:
                logger.debug(f"[CLOSE] FIN inviato al server {ip_server}:{dport}")
            
            # 2. Leggi eventuali dati rimanenti fino a ricevere FIN dal server
            sock.settimeout(2.0)  # Timeout breve per non bloccare troppo
            try:
                while True:
                    data = sock.recv(4096)
                    if not data:
                        # EOF ricevuto: il server ha inviato FIN
                        if logger:
                            logger.debug(f"[CLOSE] FIN ricevuto dal server {ip_server}:{dport}")
                        break
            except socket.timeout:
                if logger:
                    logger.warning(f"[CLOSE] Timeout attesa FIN dal server {ip_server}:{dport}")
            except Exception as e:
                if logger:
                    logger.debug(f"[CLOSE] Errore lettura finale: {e}")
        except Exception as e:
            if logger:
                logger.warning(f"[CLOSE] Errore shutdown: {e}")
        
        # 3. Chiudi il socket
        try:
            sock.close()
            if logger:
                logger.debug(f"[CLOSE] Socket chiuso {ip_client}:{sport}")
        except Exception:
            pass

    elapsed = time.time() - start
    if logger:
        logger.info(f"[FLOW] Completato in {elapsed:.2f}s: {total_packets} send applicative, {total_bursts} burst")

    return {
        "duration": elapsed,
        "packets": total_packets,
        "bursts": total_bursts,
        "avg_burst_size": total_packets / max(total_bursts, 1)
    }


def setup_logger(csv_file, ip_client, debug_enabled=True):
    global logger
    if not debug_enabled:
        logger = None
        return
    os.makedirs('/results', exist_ok=True)
    csv_basename = os.path.splitext(os.path.basename(csv_file))[0]
    ip_safe = ip_client.replace('.', '_').replace(':', '_')
    log_file = f"/results/{csv_basename}_{ip_safe}.log"
    logger = logging.getLogger(f'client_socket_{ip_client}')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info('='*60)
    logger.info(f"CLIENT SOCKET DEBUG LOG - {csv_basename}")
    logger.info(f"IP Client: {ip_client}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info('='*60)
    print(f"[+] Log debug salvato in: {log_file}")


def start_client(csv_file, ip_client, ip_server, output="/results/burst_dataset.csv", config_file=None, debug=True):
    setup_logger(csv_file, ip_client, debug)
    if logger:
        logger.info(f"Avvio client socket: CSV={csv_file}, Client={ip_client}, Server={ip_server}")
    df = pd.read_csv(csv_file)
    params = load_params(config_file)

    if "Source IP" in df.columns and "Destination IP" in df.columns:
        src_col, dst_col = "Source IP", "Destination IP"
    elif "Src IP" in df.columns and "Dst IP" in df.columns:
        src_col, dst_col = "Src IP", "Dst IP"
    else:
        print(f"[!] ERRORE: Colonne IP non trovate. Colonne disponibili: {df.columns.tolist()}")
        return

    flows = df[(df[src_col] == ip_client) & (df[dst_col] == ip_server)]
    print(f"[+] CSV: {csv_file}")
    print(f"[+] Ricerca flussi diretti {ip_client} -> {ip_server}")
    print(f"[+] Colonne usate: {src_col}, {dst_col}")
    print(f"[+] Righe totali nel CSV: {len(df)}")
    print(f"[+] Flussi selezionati: {len(flows)}")

    if len(flows) == 0:
        print("[!] ATTENZIONE: Nessun flusso trovato!")
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


if __name__ == "__main__":
    if len(sys.argv) < 4 or len(sys.argv) > 6:
        print("Uso: python client_socket.py flows.csv IPclient IPserver [config_file] [--no-debug]")
        exit(1)
    ip_client = sys.argv[2]
    ip_server = sys.argv[3]
    config_file = None
    debug = True
    for arg in sys.argv[4:]:
        if arg == "--no-debug":
            debug = False
        else:
            config_file = arg
    output_file = f"/results/burst_dataset_{ip_client.replace('.', '_')}_{ip_server.replace('.', '_')}.csv"
    start_client(sys.argv[1], ip_client, ip_server, output_file, config_file, debug)
