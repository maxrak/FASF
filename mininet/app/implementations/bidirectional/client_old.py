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
VERSION = 1
# magic(4), version(1), flags(1), reverse_bytes(4), payload_len(4), flow_id(4), burst_id(4)
HEADER_STRUCT = struct.Struct("!4sBBIIII")
HEADER_SIZE = HEADER_STRUCT.size
FLAG_REVERSE = 0x01

logger = None


def setup_logger(csv_file, ip_client, debug_enabled=True):
    global logger
    if not debug_enabled:
        logger = None
        return
    os.makedirs("/results", exist_ok=True)
    csv_basename = os.path.splitext(os.path.basename(csv_file))[0]
    ip_safe = ip_client.replace(".", "_").replace(":", "_")
    log_file = f"/results/{csv_basename}_{ip_safe}_bidirectional.log"
    logger = logging.getLogger(f"client_bidir_{ip_safe}")
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
    logger.info("CLIENT BIDIRECTIONAL FLOW EMULATOR")
    logger.info(f"CSV: {csv_file}")
    logger.info(f"Client IP: {ip_client}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 70)
    print(f"[+] Log client salvato in: {log_file}")


def load_params(config_file=None):
    if config_file is None:
        return {}
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            params = json.load(f)
        print(f"[+] Parametri caricati da {config_file}: {params}")
        return params
    except FileNotFoundError:
        print(f"[!] File configurazione {config_file} non trovato, uso default")
        return {}
    except Exception as exc:
        print(f"[!] Errore caricamento configurazione {config_file}: {exc}")
        return {}


def col(row, names, default=None):
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return default


def parse_timestamp(value):
    if value is None or pd.isna(value):
        return None
    # CICFlowMeter usa spesso formati come 02/03/2018 08:47:38 o ISO-like.
    ts = pd.to_datetime(value, errors="coerce", dayfirst=False)
    if pd.isna(ts):
        ts = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(ts):
        return None
    return ts.to_pydatetime()


def packet_size_sequence(row, params):
    min_len = int(max(1, float(col(row, ["Fwd Packet Length Min", "Fwd Packet Len Min"], 1))))
    max_len = int(max(min_len, float(col(row, ["Fwd Packet Length Max", "Fwd Packet Len Max"], min_len))))
    mean_len = float(col(row, ["Fwd Packet Length Mean", "Fwd Packet Len Mean"], min_len))
    std_len = float(col(row, ["Fwd Packet Length Std", "Fwd Packet Len Std"], max(1.0, mean_len / 2.0)))

    total_fwd_bytes = col(row, [
        "Total Length of Fwd Packet",  # Singolare (usato in molti CSV)
        "Total Length of Fwd Packets",  # Plurale
        "TotLen Fwd Pkts",
        "Fwd Packets Length Total",
        "Total Fwd Packet Length",
    ], None)
    total_fwd_pkts = int(max(1, float(col(row, [
        "Total Fwd Packet",  # Singolare
        "Total Fwd Packets",  # Plurale
        "Tot Fwd Pkts", 
        "Fwd Packet Count"
    ], 0) or 0)))

    if total_fwd_bytes is None or float(total_fwd_bytes) <= 0:
        target_total = int(round(mean_len * total_fwd_pkts))
    else:
        target_total = int(round(float(total_fwd_bytes)))

    target_total = max(min_len, target_total)

    # Se il conteggio pacchetti e' incompatibile con il totale, lo correggiamo per rispettare min/max.
    if total_fwd_pkts * min_len > target_total:
        total_fwd_pkts = max(1, target_total // min_len)
    if total_fwd_pkts * max_len < target_total:
        total_fwd_pkts = int(np.ceil(target_total / max_len))

    sizes = []
    remaining = target_total
    remaining_pkts = total_fwd_pkts
    rng = np.random.default_rng()

    while remaining_pkts > 0:
        if remaining_pkts == 1:
            size = remaining
        else:
            low = max(min_len, remaining - max_len * (remaining_pkts - 1))
            high = min(max_len, remaining - min_len * (remaining_pkts - 1))
            if high < low:
                size = min(max(remaining // remaining_pkts, min_len), max_len)
            else:
                if std_len > 0 and mean_len > 0:
                    sampled = int(round(rng.normal(mean_len, std_len)))
                else:
                    sampled = int(round(mean_len))
                size = min(max(sampled, low), high)
        sizes.append(int(size))
        remaining -= int(size)
        remaining_pkts -= 1

    random.shuffle(sizes)
    return sizes, target_total, min_len, max_len, mean_len


def split_into_bursts(sizes, params):
    p = float(params.get("burst_size_p", 0.3))
    p = min(max(p, 0.01), 1.0)
    bursts = []
    i = 0
    while i < len(sizes):
        n = int(np.random.geometric(p=p))
        n = max(1, min(n, len(sizes) - i))
        bursts.append(sizes[i:i + n])
        i += n
    return bursts


def reverse_budget(row):
    total_bwd_bytes = col(row, [
        "Total Length of Bwd Packet",  # Singolare (usato in molti CSV)
        "Total Length of Bwd Packets",  # Plurale
        "TotLen Bwd Pkts",
        "Bwd Packets Length Total",
        "Total Bwd Packet Length",
    ], 0)
    try:
        return max(0, int(round(float(total_bwd_bytes))))
    except Exception:
        return 0


def allocate_reverse_bursts(bursts, total_reverse_bytes):
    if total_reverse_bytes <= 0 or not bursts:
        return [0 for _ in bursts]
    weights = np.array([sum(b) for b in bursts], dtype=float)
    if weights.sum() <= 0:
        weights = np.ones(len(bursts), dtype=float)
    raw = weights / weights.sum() * total_reverse_bytes
    alloc = np.floor(raw).astype(int)
    remainder = total_reverse_bytes - int(alloc.sum())
    if remainder > 0:
        frac_order = np.argsort(-(raw - alloc))
        for idx in frac_order[:remainder]:
            alloc[idx] += 1
    return alloc.tolist()


def sample_iat(row, params):
    rate = float(col(row, ["Flow Packets/s", "Flow Pkts/s"], 200) or 200)
    rate = float(params.get("iat_rate", rate * 5.0))
    if rate <= 0:
        return 0.001
    return min(float(np.random.exponential(1.0 / rate)), float(params.get("max_iat", 0.01)))


def sample_idle(row, params):
    idle_mean = float(col(row, ["Idle Mean"], 0) or 0) / 1e6
    if idle_mean <= 0:
        idle_mean = float(params.get("idle_default", 0.001))
    alpha = float(params.get("idle_pareto_alpha", 1.5))
    value = (np.random.pareto(alpha) + 1.0) * idle_mean
    return min(value, float(params.get("max_idle", 3.0)))


def connect_tcp(src_ip, dst_ip, sport, dport, timeout):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
    s.settimeout(timeout)
    try:
        s.bind((src_ip, int(sport)))
        s.connect((dst_ip, int(dport)))
        return s
    except Exception:
        try:
            s.close()
        except Exception:
            pass
        raise


def recv_exact(sock, n):
    chunks = []
    got = 0
    while got < n:
        data = sock.recv(n - got)
        if not data:
            return None
        chunks.append(data)
        got += len(data)
    return b"".join(chunks)


def receiver_loop(sock, stats, stop_evt):
    try:
        while not stop_evt.is_set():
            header = recv_exact(sock, HEADER_SIZE)
            if not header:
                break
            magic, version, flags, reverse_bytes, payload_len, flow_id, burst_id = HEADER_STRUCT.unpack(header)
            if magic != MAGIC or version != VERSION:
                # Compatibilita': se qualcosa non e' framed, consuma e continua.
                stats["rx_protocol_errors"] += 1
                break
            remaining = payload_len
            while remaining > 0:
                chunk = sock.recv(min(65536, remaining))
                if not chunk:
                    return
                stats["reverse_bytes_received"] += len(chunk)
                remaining -= len(chunk)
            stats["reverse_messages_received"] += 1
    except socket.timeout:
        pass
    except Exception as exc:
        stats["rx_errors"] += 1
        if logger:
            logger.debug(f"[RX] receiver_loop terminato: {exc}")


def send_framed(sock, payload_len, reverse_bytes, flow_id, burst_id):
    header = HEADER_STRUCT.pack(MAGIC, VERSION, 0, int(reverse_bytes), int(payload_len), int(flow_id), int(burst_id))
    sock.sendall(header)
    remaining = int(payload_len)
    zero = b"\x00" * 65536
    while remaining > 0:
        n = min(len(zero), remaining)
        sock.sendall(zero[:n])
        remaining -= n


def generate_flow(flow_id, row, ip_client, ip_server, params, base_time, first_timestamp):
    sport = int(col(row, ["Source Port", "Src Port", "Sport"], random.randint(1024, 65535)))
    dport = int(col(row, ["Destination Port", "Dst Port", "Dport"], 9000))

    ts = parse_timestamp(col(row, ["Timestamp", "Flow Start Time", "Start Time"], None))
    offset = max(0.0, (ts - first_timestamp).total_seconds()) if ts and first_timestamp else 0.0
    due = base_time + offset
    delay = due - time.monotonic()
    if delay > 0:
        time.sleep(delay)

    stats = {
        "flow_id": flow_id,
        "sport": sport,
        "dport": dport,
        "scheduled_offset_s": offset,
        "forward_bytes_target": 0,
        "forward_bytes_sent": 0,
        "forward_messages_sent": 0,
        "bursts_sent": 0,
        "reverse_bytes_requested": 0,
        "reverse_bytes_received": 0,
        "reverse_messages_received": 0,
        "rx_protocol_errors": 0,
        "rx_errors": 0,
        "status": "started",
    }

    try:
        sizes, target_total, min_len, max_len, mean_len = packet_size_sequence(row, params)
        bursts = split_into_bursts(sizes, params)
        total_reverse = reverse_budget(row)
        reverse_alloc = allocate_reverse_bursts(bursts, total_reverse)
        stats["forward_bytes_target"] = target_total
        stats["reverse_bytes_requested"] = sum(reverse_alloc)

        if logger:
            logger.info(
                f"[FLOW {flow_id}] start offset={offset:.6f}s {ip_client}:{sport}->{ip_server}:{dport} "
                f"fwd_target={target_total} pkts={len(sizes)} bursts={len(bursts)} "
                f"min={min_len} max={max_len} mean={mean_len:.2f} bwd_target={total_reverse} "
                f"bwd_alloc={reverse_alloc}"
            )

        sock = connect_tcp(ip_client, ip_server, sport, dport, float(params.get("connect_timeout", 10.0)))
        sock.settimeout(float(params.get("socket_timeout", 20.0)))
        stop_evt = threading.Event()
        rx_thread = threading.Thread(target=receiver_loop, args=(sock, stats, stop_evt), daemon=True)
        rx_thread.start()

        for burst_id, pkt_sizes in enumerate(bursts):
            reverse_bytes = reverse_alloc[burst_id]
            if logger and reverse_bytes > 0:
                logger.info(
                    f"[BURST {flow_id}:{burst_id}] Inviando burst con {len(pkt_sizes)} pkts, "
                    f"richiedendo {reverse_bytes} bytes reverse"
                )
            for j, pkt_len in enumerate(pkt_sizes):
                instruction = reverse_bytes if j == 0 else 0
                if logger and instruction > 0:
                    logger.debug(
                        f"[REVERSE_REQ] flow={flow_id} burst={burst_id} pkt={j} "
                        f"requesting {instruction} reverse bytes"
                    )
                send_framed(sock, pkt_len, instruction, flow_id, burst_id)
                stats["forward_bytes_sent"] += pkt_len
                stats["forward_messages_sent"] += 1
                time.sleep(sample_iat(row, params))
            stats["bursts_sent"] += 1
            time.sleep(sample_idle(row, params))

        try:
            sock.shutdown(socket.SHUT_WR)
        except Exception:
            pass
        time.sleep(float(params.get("post_send_wait", 0.2)))
        stop_evt.set()
        try:
            sock.close()
        except Exception:
            pass
        stats["status"] = "ok"
    except Exception as exc:
        stats["status"] = f"error: {exc}"
        if logger:
            logger.error(f"[FLOW {flow_id}] errore: {exc}")
    return stats


def start_client(csv_file, ip_client, ip_server, output, config_file=None, debug=True):
    setup_logger(csv_file, ip_client, debug)
    params = load_params(config_file)
    df = pd.read_csv(csv_file)

    if "Source IP" in df.columns and "Destination IP" in df.columns:
        src_col, dst_col = "Source IP", "Destination IP"
    elif "Src IP" in df.columns and "Dst IP" in df.columns:
        src_col, dst_col = "Src IP", "Dst IP"
    else:
        raise ValueError(f"Colonne IP non trovate. Disponibili: {df.columns.tolist()}")

    flows = df[(df[src_col] == ip_client) & (df[dst_col] == ip_server)].copy()
    print(f"[+] CSV: {csv_file}")
    print(f"[+] Flussi selezionati {ip_client} -> {ip_server}: {len(flows)} / {len(df)}")
    if flows.empty:
        pd.DataFrame([]).to_csv(output, index=False)
        return

    first_ts = None
    if "Timestamp" in df.columns:
        parsed = [parse_timestamp(v) for v in df["Timestamp"]]
        parsed = [x for x in parsed if x is not None]
        first_ts = min(parsed) if parsed else None
    if first_ts is None:
        # Fallback: primo timestamp valido nei soli flussi selezionati, o nessuna schedulazione.
        ts_values = [parse_timestamp(col(r, ["Timestamp", "Flow Start Time", "Start Time"], None)) for _, r in flows.iterrows()]
        ts_values = [x for x in ts_values if x is not None]
        first_ts = min(ts_values) if ts_values else None

    if first_ts:
        print(f"[+] Timestamp primo flusso CSV: {first_ts}")
    else:
        print("[!] Nessun timestamp valido: i flussi partiranno subito")

    base_time = time.monotonic()
    max_workers = int(params.get("max_parallel_flows", 128))
    sem = threading.Semaphore(max_workers)
    results = []
    lock = threading.Lock()

    def worker(flow_id, row):
        with sem:
            res = generate_flow(flow_id, row, ip_client, ip_server, params, base_time, first_ts)
            with lock:
                results.append(res)

    threads = []
    for flow_id, (_, row) in enumerate(flows.iterrows()):
        t = threading.Thread(target=worker, args=(flow_id, row), daemon=False)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    results.sort(key=lambda x: x["flow_id"])
    pd.DataFrame(results).to_csv(output, index=False)
    print(f"[+] Risultati salvati in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client TCP bidirezionale per emulazione flussi CSV")
    parser.add_argument("csv_file")
    parser.add_argument("ip_client")
    parser.add_argument("ip_server")
    parser.add_argument("config_file", nargs="?")
    parser.add_argument("--no-debug", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    out = args.output or f"/results/bidir_dataset_{args.ip_client.replace('.', '_')}_{args.ip_server.replace('.', '_')}.csv"
    start_client(args.csv_file, args.ip_client, args.ip_server, out, args.config_file, not args.no_debug)
