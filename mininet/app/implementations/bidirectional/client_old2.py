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


def int_col(row, names, default=0):
    value = col(row, names, default)
    try:
        if value is None or pd.isna(value):
            return int(default)
        return int(round(float(value)))
    except Exception:
        return int(default)


def exact_packet_size_sequence(row, direction="fwd"):
    """Build exactly N logical payload sizes whose sum is exactly Total Length.

    CICFlowMeter packet counts include pure TCP packets/ACKs with payload length 0.
    For this reason the lower bound is allowed to be 0 when the CSV min is 0.
    The function never changes the CSV packet count; if max/min constraints are
    mathematically incompatible with the requested total, it still preserves count
    and total and logs/clamps individual samples as needed.
    """
    if direction == "fwd":
        pkt_names = ["Total Fwd Packet", "Total Fwd Packets", "Tot Fwd Pkts", "Fwd Packet Count"]
        total_names = [
            "Total Length of Fwd Packet", "Total Length of Fwd Packets", "TotLen Fwd Pkts",
            "Fwd Packets Length Total", "Total Fwd Packet Length",
        ]
        min_names = ["Fwd Packet Length Min", "Fwd Packet Len Min"]
        max_names = ["Fwd Packet Length Max", "Fwd Packet Len Max"]
        mean_names = ["Fwd Packet Length Mean", "Fwd Packet Len Mean"]
        std_names = ["Fwd Packet Length Std", "Fwd Packet Len Std"]
    else:
        pkt_names = ["Total Bwd packets", "Total Bwd Packet", "Total Bwd Packets", "Tot Bwd Pkts", "Bwd Packet Count"]
        total_names = [
            "Total Length of Bwd Packet", "Total Length of Bwd Packets", "TotLen Bwd Pkts",
            "Bwd Packets Length Total", "Total Bwd Packet Length",
        ]
        min_names = ["Bwd Packet Length Min", "Bwd Packet Len Min"]
        max_names = ["Bwd Packet Length Max", "Bwd Packet Len Max"]
        mean_names = ["Bwd Packet Length Mean", "Bwd Packet Len Mean"]
        std_names = ["Bwd Packet Length Std", "Bwd Packet Len Std"]

    n_pkts = max(0, int_col(row, pkt_names, 0))
    target_total = max(0, int_col(row, total_names, 0))
    if n_pkts == 0:
        return [], target_total, 0, 0, 0.0

    csv_min = max(0, int_col(row, min_names, 0))
    csv_max = max(csv_min, int_col(row, max_names, max(csv_min, target_total)))
    mean_len = float(col(row, mean_names, (target_total / n_pkts if n_pkts else 0)) or 0)
    std_len = float(col(row, std_names, max(1.0, mean_len / 2.0)) or 0)

    # If the CSV reports min=0, zeros are legitimate packets. This is common for ACKs.
    min_len = csv_min
    max_len = max(csv_max, 1 if target_total > 0 else 0)

    # Preserve exact packet count and exact total even when CSV stats are inconsistent.
    if target_total < n_pkts * min_len:
        min_len = 0
    if target_total > n_pkts * max_len:
        max_len = target_total

    rng = np.random.default_rng()
    sizes = []
    remaining = target_total
    remaining_pkts = n_pkts
    while remaining_pkts > 0:
        if remaining_pkts == 1:
            size = remaining
        else:
            low = max(min_len, remaining - max_len * (remaining_pkts - 1))
            high = min(max_len, remaining - min_len * (remaining_pkts - 1))
            if high < low:
                size = max(0, remaining // remaining_pkts)
            else:
                if std_len > 0 and mean_len > 0:
                    sampled = int(round(rng.normal(mean_len, std_len)))
                else:
                    sampled = int(round(target_total / n_pkts))
                size = min(max(sampled, low), high)
        sizes.append(int(size))
        remaining -= int(size)
        remaining_pkts -= 1

    random.shuffle(sizes)
    return sizes, target_total, csv_min, csv_max, mean_len


def packet_size_sequence(row, params):
    # Backward-compatible wrapper: the adapted client now always preserves the
    # original FWD packet count and total byte length.
    return exact_packet_size_sequence(row, "fwd")

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
    """Send one logical CSV packet as one userspace write.

    The old version wrote the protocol header and payload separately; with
    TCP_NODELAY that often became two TCP segments. Combining them reduces the
    packet inflation visible to CICFlowMeter.
    """
    header = HEADER_STRUCT.pack(MAGIC, VERSION, 0, int(reverse_bytes), int(payload_len), int(flow_id), int(burst_id))
    payload_len = int(payload_len)
    if payload_len <= 0:
        sock.sendall(header)
        return
    zero = b"\x00" * payload_len
    sock.sendall(header + zero)


def duration_seconds(row):
    value = col(row, ["Flow Duration", "Flow Duration Microseconds", "Flow Duration us"], 0)
    try:
        return max(0.0, float(value) / 1_000_000.0)
    except Exception:
        return 0.0


def make_reverse_requests(row, fwd_count, params):
    """Return per-FWD-packet reverse byte requests.

    With the unmodified server one reverse request can generate either one
    reverse message (if <= reverse_chunk_size) or multiple 1448-byte chunks.
    Therefore exact BWD byte total is always enforced, while exact BWD packet
    count is feasible only when the server packetization can represent it.
    """
    bwd_sizes, bwd_total, _, _, _ = exact_packet_size_sequence(row, "bwd")
    requests = [0 for _ in range(max(0, fwd_count))]
    if not requests or bwd_total <= 0:
        return requests, bwd_total, len(bwd_sizes), False

    chunk = int(params.get("reverse_chunk_size", 1448))
    chunk = max(1, chunk)

    # Best case: one BWD logical packet per FWD packet, preserving BWD count when possible.
    if len(bwd_sizes) <= len(requests) and all(x <= chunk for x in bwd_sizes):
        for i, size in enumerate(bwd_sizes):
            requests[i] = int(size)
        return requests, bwd_total, len(bwd_sizes), True

    # Otherwise preserve exact BWD total length and distribute it across FWD packets.
    # The current server cannot be told to emit more than one arbitrary-size BWD
    # packet per FWD packet without changing the protocol.
    active = min(len(requests), max(1, len(bwd_sizes)))
    remaining = bwd_total
    for i in range(active):
        left = active - i
        val = remaining // left
        requests[i] = int(val)
        remaining -= int(val)
    return requests, bwd_total, len(bwd_sizes), False

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
        target_duration = duration_seconds(row)
        reverse_requests, total_reverse, target_bwd_pkts, exact_bwd_count = make_reverse_requests(row, len(sizes), params)
        stats["forward_bytes_target"] = target_total
        stats["reverse_bytes_requested"] = sum(reverse_requests)
        stats["target_fwd_packets"] = len(sizes)
        stats["target_bwd_packets"] = target_bwd_pkts
        stats["target_duration_s"] = target_duration
        stats["exact_bwd_count_feasible_with_current_server"] = exact_bwd_count

        if logger:
            logger.info(
                f"[FLOW {flow_id}] start offset={offset:.6f}s {ip_client}:{sport}->{ip_server}:{dport} "
                f"fwd_target={target_total} pkts={len(sizes)} min={min_len} max={max_len} "
                f"mean={mean_len:.2f} duration_target={target_duration:.6f}s "
                f"bwd_target={total_reverse} bwd_pkts={target_bwd_pkts} "
                f"bwd_count_exact_feasible={exact_bwd_count}"
            )

        sock = connect_tcp(ip_client, ip_server, sport, dport, float(params.get("connect_timeout", 10.0)))
        sock.settimeout(float(params.get("socket_timeout", 20.0)))
        stop_evt = threading.Event()
        rx_thread = threading.Thread(target=receiver_loop, args=(sock, stats, stop_evt), daemon=True)
        rx_thread.start()

        flow_start = time.monotonic()
        n = len(sizes)
        if n <= 1 or target_duration <= 0:
            spacing = 0.0
        else:
            spacing = target_duration / float(n - 1)

        for pkt_idx, pkt_len in enumerate(sizes):
            due_pkt = flow_start + pkt_idx * spacing
            wait = due_pkt - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            instruction = reverse_requests[pkt_idx] if pkt_idx < len(reverse_requests) else 0
            if logger and instruction > 0:
                logger.debug(f"[REVERSE_REQ] flow={flow_id} pkt={pkt_idx} requesting {instruction} reverse bytes")
            send_framed(sock, pkt_len, instruction, flow_id, pkt_idx)
            stats["forward_bytes_sent"] += pkt_len
            stats["forward_messages_sent"] += 1

        stats["bursts_sent"] = n
        # Keep the TCP connection open until the target flow duration has elapsed.
        # This helps CICFlowMeter recover Flow Duration and Fwd/Bwd IAT totals.
        remaining_duration = (flow_start + target_duration) - time.monotonic()
        if remaining_duration > 0:
            time.sleep(remaining_duration)

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
