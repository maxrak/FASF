import argparse
import json
import logging
import os
import random
import socket
import struct
import threading
import time
from datetime import datetime

import numpy as np
import pandas as pd

MAGIC = b"FEMU"
VERSION = 2  # Aggiornata versione protocollo
HEADER_STRUCT = struct.Struct("!4sBBIIII")
HEADER_SIZE = HEADER_STRUCT.size

# Flag del protocollo
FLAG_CONFIG = 0x02  # Indica che il payload contiene il JSON di configurazione Bwd

logger = None

def setup_logger(csv_file, ip_client, debug_enabled=True):
    global logger
    if not debug_enabled:
        logger = None
        return
    os.makedirs("/results", exist_ok=True)
    csv_basename = os.path.splitext(os.path.basename(csv_file))[0]
    ip_safe = ip_client.replace(".", "_").replace(":", "_")
    log_file = f"/results/{csv_basename}_{ip_safe}_configurable.log"
    logger = logging.getLogger(f"client_configurable_{ip_safe}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    fh = logging.FileHandler(log_file, mode="w")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info("=" * 70)
    logger.info("CLIENT DECOUPLED INDEPENDENT FLOW EMULATOR")
    logger.info(f"CSV: {csv_file}")
    logger.info(f"Client IP: {ip_client}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 70)
    print(f"[+] Log client salvato in: {log_file}")

def deep_merge(base, override):
    if not isinstance(override, dict):
        return base
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out

def flattened_config(config):
    flat = {}
    if isinstance(config, dict):
        flat.update(config)
        if isinstance(config.get("global"), dict):
            flat = deep_merge(flat, config["global"])
        if isinstance(config.get("models"), dict):
            flat = deep_merge(flat, config["models"])
    return flat

def load_params(config_file=None):
    defaults = {
        "seed": None,
        "max_parallel_flows": 128,
        "connect_timeout": 10.0,
        "socket_timeout": 30.0,
        "post_send_wait": 0.25,
        "initial_delay_s": 0.0,
        "close_delay_ms": 0.0,
        "tcp_nodelay": True,
        "send_buffer": None,
        "recv_buffer": None,
        "mss_hint": None,
        "chunk_size": 1448,
        "packet_size_model": "csv_stats",
        "payload_mean_scale": 1.0,
        "payload_std_scale": 1.0,
        "payload_min_scale": 1.0,
        "payload_max_scale": 1.0,
        "fwd_payload_mean_scale": None,
        "fwd_payload_std_scale": None,
        "bwd_payload_mean_scale": None,
        "bwd_payload_std_scale": None,
        "zero_payload_fill": 0,
        "shuffle_payload_sizes": True,
        "use_fwd_iat": True,
        "use_flow_iat_fallback": True,
        "use_active_idle": True,
        "iat_scale": 1.0,
        "iat_std_scale": 1.0,
        "fwd_iat_scale": None,
        "bwd_iat_scale": None,  # Aggiunto per controllo esplicito bwd
        "duration_scale": 1.0,
        "burst_probability": 0.0,
        "burst_factor": 2.0,
    }
    raw = {}
    if config_file is not None:
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as exc:
            print(f"[!] Errore caricamento configurazione: {exc}")
    params = deep_merge(defaults, flattened_config(raw))
    params["_raw_config"] = raw if isinstance(raw, dict) else {}
    return params

def col(row, names, default=None):
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return default

def f_col(row, names, default=0.0):
    value = col(row, names, default)
    try:
        return float(value) if value is not None and not pd.isna(value) else float(default)
    except Exception:
        return float(default)

def i_col(row, names, default=0):
    try:
        return int(round(f_col(row, names, default)))
    except Exception:
        return int(default)

def parse_timestamp(value):
    if value is None or pd.isna(value):
        return None
    ts = pd.to_datetime(value, errors="coerce")
    return ts.to_pydatetime() if not pd.isna(ts) else None

def duration_seconds(row, params=None):
    params = params or {}
    scale = float(params.get("duration_scale", 1.0))
    return max(0.0, f_col(row, ["Flow Duration", "Flow Duration Microseconds"], 0.0) / 1_000_000.0 * scale)

def total_names(direction):
    if direction == "fwd":
        return {
            "count": ["Total Fwd Packet", "Total Fwd Packets", "Tot Fwd Pkts"],
            "total": ["Total Length of Fwd Packet", "Total Length of Fwd Packets", "TotLen Fwd Pkts"],
            "min": ["Fwd Packet Length Min", "Fwd Packet Len Min"],
            "max": ["Fwd Packet Length Max", "Fwd Packet Len Max"],
            "mean": ["Fwd Packet Length Mean", "Fwd Packet Len Mean"],
            "std": ["Fwd Packet Length Std", "Fwd Packet Len Std"],
            "act": ["Fwd Act Data Pkts"],
        }
    return {
        "count": ["Total Bwd packets", "Total Bwd Packet", "Total Bwd Packets", "Tot Bwd Pkts"],
        "total": ["Total Length of Bwd Packet", "Total Length of Bwd Packets", "TotLen Bwd Pkts"],
        "min": ["Bwd Packet Length Min", "Bwd Packet Len Min"],
        "max": ["Bwd Packet Length Max", "Bwd Packet Len Max"],
        "mean": ["Bwd Packet Length Mean", "Bwd Packet Len Mean"],
        "std": ["Bwd Packet Length Std", "Bwd Packet Len Std"],
        "act": ["Bwd Act Data Pkts"],
    }

def _adjust_sum(values, target, low, high):
    values = [int(max(low, min(high, v))) for v in values]
    diff = int(target) - sum(values)
    loops = 0
    while diff != 0 and loops < len(values) * 4 + 10:
        changed = False
        order = list(range(len(values)))
        random.shuffle(order)
        for idx in order:
            if diff == 0: break
            if diff > 0:
                room = high - values[idx]
                if room > 0:
                    add = min(room, diff)
                    values[idx] += add
                    diff -= add
                    changed = True
            else:
                room = values[idx] - low
                if room > 0:
                    sub = min(room, -diff)
                    values[idx] -= sub
                    diff += sub
                    changed = True
        if not changed: break
        loops += 1
    if diff != 0 and values:
        values[-1] += diff
    return values

def exact_packet_size_sequence(row, direction="fwd", params=None):
    params = params or {}
    names = total_names(direction)
    n_pkts = max(0, i_col(row, names["count"], 0))
    target_total = max(0, i_col(row, names["total"], 0))
    if n_pkts == 0: return [], target_total, {}

    csv_min = max(0, i_col(row, names["min"], 0))
    csv_max = max(csv_min, i_col(row, names["max"], max(csv_min, target_total)))
    mean_len = f_col(row, names["mean"], target_total / max(n_pkts, 1))
    std_len = max(0.0, f_col(row, names["std"], 0.0))

    mean_scale = params.get(f"{direction}_payload_mean_scale") or params.get("payload_mean_scale", 1.0)
    std_scale = params.get(f"{direction}_payload_std_scale") or params.get("payload_std_scale", 1.0)
    
    mean_len *= float(mean_scale)
    std_len *= float(std_scale)

    low = int(round(csv_min * float(params.get("payload_min_scale", 1.0))))
    high = max(int(round(csv_max * float(params.get("payload_max_scale", 1.0)))), 1 if target_total > 0 else 0)

    rng = np.random.default_rng()
    values = []
    for _ in range(n_pkts):
        if std_len > 0 and mean_len > 0:
            val = int(round(rng.normal(mean_len, std_len)))
        else:
            val = int(round(target_total / max(1, n_pkts)))
        values.append(max(low, min(high, val)))

    if n_pkts >= 1 and target_total >= csv_max: values[-1] = csv_max
    values = _adjust_sum(values, target_total, low, high)
    if params.get("shuffle_payload_sizes", True):
        random.shuffle(values)
    return values, target_total, {"actual_min": min(values) if values else 0, "actual_max": max(values) if values else 0}

def build_iat_sequence_directional(row, n_packets, direction, params):
    if n_packets <= 1: return []
    
    # Selettore di campi basato sulla direzione fwd o bwd per l'allineamento perfetto delle feature
    prefix = "Fwd" if direction == "fwd" else "Bwd"
    target_duration_us = max(0.0, f_col(row, [f"{prefix} IAT Total"], f_col(row, ["Flow Duration"], 0.0)))
    
    iat_scale = float(params.get(f"{direction}_iat_scale") or params.get("iat_scale", 1.0))
    target_total = target_duration_us / 1_000_000.0 * iat_scale

    mean_us = f_col(row, [f"{prefix} IAT Mean"], 0.0)
    std_us = f_col(row, [f"{prefix} IAT Std"], 0.0) * float(params.get("iat_std_scale", 1.0))
    min_us = max(0.0, f_col(row, [f"{prefix} IAT Min"], 0.0))
    max_us = max(min_us, f_col(row, [f"{prefix} IAT Max"], target_duration_us))

    k = n_packets - 1
    low = min_us / 1_000_000.0
    high = max(max_us / 1_000_000.0, low)

    rng = np.random.default_rng()
    values = []
    for _ in range(k):
        if std_us > 0 and mean_us > 0:
            val = float(rng.normal(mean_us / 1_000_000.0, std_us / 1_000_000.0))
        else:
            val = target_total / k
        values.append(max(low, min(high, val)))

    # Correzione convergenza somma totale degli IAT
    diff = target_total - sum(values)
    if abs(diff) > 1e-9 and values:
        values[-1] += diff
    return [max(0.0, float(v)) for v in values]

def configure_socket(sock, row, params):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1 if params.get("tcp_nodelay", True) else 0)
    if params.get("send_buffer"): sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, int(params.get("send_buffer")))
    if params.get("recv_buffer"): sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, int(params.get("recv_buffer")))

def recv_exact(sock, n):
    chunks = []
    got = 0
    while got < n:
        data = sock.recv(n - got)
        if not data: return None
        chunks.append(data)
        got += len(data)
    return b"".join(chunks)

def receiver_loop(sock, stats, stop_evt):
    """Il ricevitore si limita a consumare asincronamente i pacchetti iniettati dal server."""
    try:
        while not stop_evt.is_set():
            header = recv_exact(sock, HEADER_SIZE)
            if not header: break
            magic, version, flags, _, payload_len, _, _ = HEADER_STRUCT.unpack(header)
            remaining = payload_len
            while remaining > 0:
                chunk = sock.recv(min(65536, remaining))
                if not chunk: return
                stats["reverse_bytes_received"] += len(chunk)
                remaining -= len(chunk)
            stats["reverse_messages_received"] += 1
    except Exception:
        pass

def generate_flow(flow_id, row, ip_client, ip_server, params, base_time, first_timestamp):
    protocol = i_col(row, ["Protocol"], 6)
    sport = i_col(row, ["Source Port", "Src Port", "Sport"], random.randint(1024, 65535))
    dport = i_col(row, ["Destination Port", "Dst Port", "Dport"], 9000)

    ts = parse_timestamp(col(row, ["Timestamp", "Flow Start Time"], None))
    offset = max(0.0, (ts - first_timestamp).total_seconds()) if ts and first_timestamp else 0.0
    due = base_time + offset
    delay = due - time.monotonic()
    if delay > 0: time.sleep(delay)

    stats = {
        "flow_id": flow_id, "sport": sport, "dport": dport, "protocol": protocol,
        "forward_bytes_sent": 0, "forward_messages_sent": 0,
        "reverse_bytes_received": 0, "reverse_messages_received": 0, "status": "started"
    }

    if protocol != 6:
        stats["status"] = "skipped: TCP only"
        return stats

    try:
        # 1. Generazione sequenze indipendenti (Fwd e Bwd) basate sulle reali feature della riga
        fwd_sizes, _, fwd_meta = exact_packet_size_sequence(row, "fwd", params)
        fwd_iats = build_iat_sequence_directional(row, len(fwd_sizes), "fwd", params)

        bwd_sizes, _, bwd_meta = exact_packet_size_sequence(row, "bwd", params)
        bwd_iats = build_iat_sequence_directional(row, len(bwd_sizes), "bwd", params)

        # Configurazione da spedire al Server nell'handshake iniziale
        bwd_config = {"sizes": bwd_sizes, "iats": bwd_iats, "flow_id": flow_id}
        config_bytes = json.dumps(bwd_config).encode("utf-8")

        # Connessione
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        configure_socket(sock, row, params)
        sock.settimeout(float(params.get("connect_timeout", 10.0)))
        sock.bind((ip_client, sport))
        sock.connect((ip_server, dport))
        sock.settimeout(float(params.get("socket_timeout", 30.0)))

        # 2. FASE DI HANDSHAKE: Invio della mappa dei flussi Bwd al server
        header_cfg = HEADER_STRUCT.pack(MAGIC, VERSION, FLAG_CONFIG, 0, len(config_bytes), flow_id, 0)
        sock.sendall(header_cfg + config_bytes)

        stop_evt = threading.Event()
        rx_thread = threading.Thread(target=receiver_loop, args=(sock, stats, stop_evt), daemon=True)
        rx_thread.start()

        # 3. MOTORE FWD INDIPENDENTE: Generazione temporizzata dei pacchetti Fwd senza attesa di risposte
        flow_start = time.monotonic()
        due_pkt = flow_start
        fill_byte = int(params.get("zero_payload_fill", 0))

        for pkt_idx, pkt_len in enumerate(fwd_sizes):
            if pkt_idx > 0:
                due_pkt += fwd_iats[pkt_idx - 1]
            wait = due_pkt - time.monotonic()
            if wait > 0: time.sleep(wait)

            header = HEADER_STRUCT.pack(MAGIC, VERSION, 0, 0, pkt_len, flow_id, pkt_idx)
            payload = bytes([fill_byte & 0xff]) * pkt_len
            sock.sendall(header + payload)

            stats["forward_bytes_sent"] += pkt_len
            stats["forward_messages_sent"] += 1

        # Mantenimento attivo per la durata attesa del flusso
        target_duration = duration_seconds(row, params)
        remaining = (flow_start + target_duration) - time.monotonic()
        if remaining > 0: time.sleep(remaining)

        sock.shutdown(socket.SHUT_WR)
        time.sleep(float(params.get("post_send_wait", 0.25)))
        stop_evt.set()
        sock.close()
        stats["status"] = "ok"
    except Exception as exc:
        stats["status"] = f"error: {exc}"
    return stats

def start_client(csv_file, ip_client, ip_server, output, config_file=None, debug=True):
    params = load_params(config_file)
    if params.get("seed") is not None:
        random.seed(params["seed"])
        np.random.seed(params["seed"])
    setup_logger(csv_file, ip_client, debug)
    df = pd.read_csv(csv_file)

    src_col = "Source IP" if "Source IP" in df.columns else "Src IP"
    dst_col = "Destination IP" if "Destination IP" in df.columns else "Dst IP"

    flows = df[(df[src_col] == ip_client) & (df[dst_col] == ip_server)].copy()
    if flows.empty:
        pd.DataFrame([]).to_csv(output, index=False)
        return

    first_ts = None
    if "Timestamp" in df.columns:
        parsed = [parse_timestamp(v) for v in df["Timestamp"] if pd.notna(v)]
        if parsed: first_ts = min(parsed)

    base_time = time.monotonic()
    sem = threading.Semaphore(int(params.get("max_parallel_flows", 128)))
    results = []
    lock = threading.Lock()

    def worker(flow_id, row):
        with sem:
            res = generate_flow(flow_id, row, ip_client, ip_server, params, base_time, first_ts)
            with lock: results.append(res)

    threads = []
    for flow_id, (_, row) in enumerate(flows.iterrows()):
        t = threading.Thread(target=worker, args=(flow_id, row))
        t.start()
        threads.append(t)

    for t in threads: t.join()
    pd.DataFrame(results).to_csv(output, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("ip_client")
    parser.add_argument("ip_server")
    parser.add_argument("config_file", nargs="?")
    parser.add_argument("--no-debug", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    out = args.output or f"/results/decoupled_output.csv"
    start_client(args.csv_file, args.ip_client, args.ip_server, out, args.config_file, not args.no_debug)