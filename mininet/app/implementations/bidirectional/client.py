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
    log_file = f"/results/{csv_basename}_{ip_safe}_feature_aware.log"
    logger = logging.getLogger(f"client_feature_aware_{ip_safe}")
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
    logger.info("CLIENT FEATURE-AWARE BIDIRECTIONAL FLOW EMULATOR")
    logger.info(f"CSV: {csv_file}")
    logger.info(f"Client IP: {ip_client}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 70)
    print(f"[+] Log client salvato in: {log_file}")


def load_params(config_file=None):
    defaults = {
        "seed": None,
        "max_parallel_flows": 128,
        "connect_timeout": 10.0,
        "socket_timeout": 30.0,
        "post_send_wait": 0.25,
        "reverse_chunk_size": 1448,
        "preserve_fwd_count": True,
        "preserve_bwd_total": True,
        "use_fwd_iat": True,
        "use_flow_iat_fallback": True,
        "use_active_idle": True,
        "use_tcp_buffers_from_init_win": True,
        "use_tcp_maxseg_from_seg_size_min": True,
        "zero_payload_fill": 0,
        "jitter_fraction": 0.02,
    }
    if config_file is None:
        return defaults
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            user_params = json.load(f)
        defaults.update(user_params)
        print(f"[+] Parametri caricati da {config_file}: {defaults}")
        return defaults
    except FileNotFoundError:
        print(f"[!] File configurazione {config_file} non trovato, uso default")
        return defaults
    except Exception as exc:
        print(f"[!] Errore caricamento configurazione {config_file}: {exc}")
        return defaults


def col(row, names, default=None):
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return default


def f_col(row, names, default=0.0):
    value = col(row, names, default)
    try:
        if value is None or pd.isna(value):
            return float(default)
        return float(value)
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
    ts = pd.to_datetime(value, errors="coerce", dayfirst=False)
    if pd.isna(ts):
        ts = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(ts):
        return None
    return ts.to_pydatetime()


def duration_seconds(row):
    return max(0.0, f_col(row, ["Flow Duration", "Flow Duration Microseconds", "Flow Duration us"], 0.0) / 1_000_000.0)


def total_names(direction):
    if direction == "fwd":
        return {
            "count": ["Total Fwd Packet", "Total Fwd Packets", "Tot Fwd Pkts", "Fwd Packet Count", "Subflow Fwd Packets"],
            "total": ["Total Length of Fwd Packet", "Total Length of Fwd Packets", "TotLen Fwd Pkts", "Fwd Packets Length Total", "Total Fwd Packet Length", "Subflow Fwd Bytes"],
            "min": ["Fwd Packet Length Min", "Fwd Packet Len Min"],
            "max": ["Fwd Packet Length Max", "Fwd Packet Len Max"],
            "mean": ["Fwd Packet Length Mean", "Fwd Packet Len Mean", "Fwd Segment Size Avg"],
            "std": ["Fwd Packet Length Std", "Fwd Packet Len Std"],
            "act": ["Fwd Act Data Pkts"],
        }
    return {
        "count": ["Total Bwd packets", "Total Bwd Packet", "Total Bwd Packets", "Tot Bwd Pkts", "Bwd Packet Count", "Subflow Bwd Packets"],
        "total": ["Total Length of Bwd Packet", "Total Length of Bwd Packets", "TotLen Bwd Pkts", "Bwd Packets Length Total", "Total Bwd Packet Length", "Subflow Bwd Bytes"],
        "min": ["Bwd Packet Length Min", "Bwd Packet Len Min"],
        "max": ["Bwd Packet Length Max", "Bwd Packet Len Max"],
        "mean": ["Bwd Packet Length Mean", "Bwd Packet Len Mean", "Bwd Segment Size Avg"],
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
            if diff == 0:
                break
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
        if not changed:
            break
        loops += 1
    if diff != 0 and values:
        values[-1] += diff
    return values


def exact_packet_size_sequence(row, direction="fwd"):
    names = total_names(direction)
    n_pkts = max(0, i_col(row, names["count"], 0))
    target_total = max(0, i_col(row, names["total"], 0))
    if n_pkts == 0:
        return [], target_total, {"exact_stats": True}

    csv_min = max(0, i_col(row, names["min"], 0))
    csv_max = max(csv_min, i_col(row, names["max"], max(csv_min, target_total)))
    mean_len = f_col(row, names["mean"], target_total / max(n_pkts, 1))
    std_len = max(0.0, f_col(row, names["std"], 0.0))
    act_data = max(0, i_col(row, names["act"], n_pkts))

    low = csv_min
    high = max(csv_max, 1 if target_total > 0 else 0)
    if target_total < n_pkts * low:
        low = 0
    if target_total > n_pkts * high:
        high = target_total

    rng = np.random.default_rng()
    nonzero_hint = min(n_pkts, act_data) if act_data > 0 else min(n_pkts, sum(1 for _ in range(n_pkts)))
    zero_count = max(0, n_pkts - nonzero_hint) if csv_min == 0 and target_total > 0 else 0

    values = []
    for idx in range(n_pkts):
        if idx < zero_count:
            values.append(0)
        else:
            if std_len > 0 and mean_len > 0:
                val = int(round(rng.normal(mean_len, std_len)))
            else:
                val = int(round(target_total / max(1, n_pkts - zero_count)))
            values.append(max(low, min(high, val)))

    # Force at least one observed min and max when feasible. This helps CICFlowMeter reproduce min/max.
    if n_pkts >= 1 and target_total >= csv_max and csv_max > 0:
        values[-1] = csv_max
    if n_pkts >= 2 and csv_min == 0:
        values[0] = 0
    elif n_pkts >= 2 and target_total >= csv_min + values[-1]:
        values[0] = csv_min

    values = _adjust_sum(values, target_total, low, high)
    random.shuffle(values)
    meta = {
        "csv_min": csv_min,
        "csv_max": csv_max,
        "csv_mean": mean_len,
        "csv_std": std_len,
        "target_total": target_total,
        "target_count": n_pkts,
        "actual_min": min(values) if values else 0,
        "actual_max": max(values) if values else 0,
        "actual_mean": float(np.mean(values)) if values else 0.0,
        "actual_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
    }
    return values, target_total, meta


def build_iat_sequence(row, n_packets, params):
    if n_packets <= 1:
        return []
    target_duration_us = max(0.0, f_col(row, ["Fwd IAT Total"], f_col(row, ["Flow Duration"], 0.0)))
    if target_duration_us <= 0:
        target_duration_us = f_col(row, ["Flow Duration"], 0.0)
    target_total = target_duration_us / 1_000_000.0

    mean_us = f_col(row, ["Fwd IAT Mean"], 0.0)
    std_us = f_col(row, ["Fwd IAT Std"], 0.0)
    min_us = max(0.0, f_col(row, ["Fwd IAT Min"], 0.0))
    max_us = max(min_us, f_col(row, ["Fwd IAT Max"], max(min_us, target_duration_us)))

    if mean_us <= 0 and params.get("use_flow_iat_fallback", True):
        mean_us = f_col(row, ["Flow IAT Mean"], target_duration_us / max(1, n_packets - 1))
        std_us = f_col(row, ["Flow IAT Std"], std_us)
        min_us = max(0.0, f_col(row, ["Flow IAT Min"], min_us))
        max_us = max(min_us, f_col(row, ["Flow IAT Max"], max_us))

    k = n_packets - 1
    if target_total <= 0:
        return [0.0 for _ in range(k)]

    low = min_us / 1_000_000.0
    high = max(max_us / 1_000_000.0, low)
    if target_total < k * low:
        low = 0.0
    if target_total > k * high:
        high = target_total

    rng = np.random.default_rng()
    values = []
    for _ in range(k):
        if std_us > 0 and mean_us > 0:
            val = float(rng.normal(mean_us / 1_000_000.0, std_us / 1_000_000.0))
        elif mean_us > 0:
            val = mean_us / 1_000_000.0
        else:
            val = target_total / k
        values.append(max(low, min(high, val)))

    if k >= 1 and high > 0:
        values[0] = min(high, target_total)
    if k >= 2:
        values[1] = low

    # Adjust exact total while respecting low/high as much as possible.
    diff = target_total - sum(values)
    for _ in range(k * 4 + 10):
        if abs(diff) < 1e-9:
            break
        changed = False
        order = list(range(k))
        random.shuffle(order)
        for idx in order:
            if abs(diff) < 1e-9:
                break
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
        if not changed:
            break
    if abs(diff) > 1e-9 and values:
        values[-1] += diff

    return [max(0.0, float(v)) for v in values]


def inject_active_idle(iats, row, params):
    if not iats or not params.get("use_active_idle", True):
        return iats
    idle_mean_us = f_col(row, ["Idle Mean"], 0.0)
    idle_max_us = f_col(row, ["Idle Max"], idle_mean_us)
    active_mean_us = f_col(row, ["Active Mean"], 0.0)
    if idle_mean_us <= 0 or active_mean_us <= 0:
        return iats
    # Keep the exact total, but move larger gaps toward the reported idle scale.
    total = sum(iats)
    if total <= 0:
        return iats
    idle_s = min(max(idle_mean_us, 0.0), max(idle_max_us, idle_mean_us)) / 1_000_000.0
    if idle_s <= 0 or idle_s >= total:
        return iats
    idx = int(np.argmax(iats))
    iats[idx] = max(iats[idx], idle_s)
    scale_total = sum(iats)
    if scale_total > 0:
        iats = [v * total / scale_total for v in iats]
    return iats


def make_reverse_requests(row, fwd_count, params):
    bwd_sizes, bwd_total, bwd_meta = exact_packet_size_sequence(row, "bwd")
    requests = [0 for _ in range(max(0, fwd_count))]
    if not requests or bwd_total <= 0:
        return requests, bwd_total, len(bwd_sizes), True, bwd_meta

    chunk = max(1, int(params.get("reverse_chunk_size", 1448)))
    exact_count = False

    # If the server can emit one BWD logical reply per FWD logical packet, preserve the BWD sequence.
    if len(bwd_sizes) <= len(requests) and all(x <= chunk for x in bwd_sizes):
        for i, size in enumerate(bwd_sizes):
            requests[i] = int(size)
        exact_count = True
    else:
        # Preserve exact BWD byte total. The current protocol cannot force >1 arbitrary BWD packets per FWD packet.
        active = min(len(requests), max(1, len(bwd_sizes)))
        remaining = bwd_total
        for i in range(active):
            left = active - i
            val = remaining // left
            requests[i] = int(val)
            remaining -= int(val)
    return requests, bwd_total, len(bwd_sizes), exact_count, bwd_meta


def configure_socket(sock, row, params):
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
    if params.get("use_tcp_buffers_from_init_win", True):
        fwd_win = i_col(row, ["FWD Init Win Bytes", "Init_Win_bytes_forward", "Init Win bytes forward"], 0)
        bwd_win = i_col(row, ["Bwd Init Win Bytes", "Init_Win_bytes_backward", "Init Win bytes backward"], 0)
        # These are hints. Linux may double/clamp buffers and the real TCP window is kernel-controlled.
        try:
            if fwd_win > 0:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, max(4096, fwd_win))
        except Exception:
            pass
        try:
            if bwd_win > 0:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, max(4096, bwd_win))
        except Exception:
            pass
    if params.get("use_tcp_maxseg_from_seg_size_min", True):
        seg_min = i_col(row, ["Fwd Seg Size Min", "Fwd Segment Size Min"], 0)
        # Do not use tiny values like 20/32 as MSS; those are usually header-size features, not MSS.
        if seg_min >= 536:
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_MAXSEG, seg_min)
            except Exception:
                pass


def connect_tcp(src_ip, dst_ip, sport, dport, timeout, row, params):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    configure_socket(s, row, params)
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


def send_framed(sock, payload_len, reverse_bytes, flow_id, packet_id, fill_byte=0):
    header = HEADER_STRUCT.pack(MAGIC, VERSION, 0, int(reverse_bytes), int(payload_len), int(flow_id), int(packet_id))
    payload_len = int(payload_len)
    if payload_len <= 0:
        sock.sendall(header)
        return
    payload = bytes([int(fill_byte) & 0xff]) * payload_len
    sock.sendall(header + payload)


def generate_flow(flow_id, row, ip_client, ip_server, params, base_time, first_timestamp):
    protocol = i_col(row, ["Protocol"], 6)
    sport = i_col(row, ["Source Port", "Src Port", "Sport"], random.randint(1024, 65535))
    dport = i_col(row, ["Destination Port", "Dst Port", "Dport"], 9000)

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
        "protocol": protocol,
        "scheduled_offset_s": offset,
        "forward_bytes_target": 0,
        "forward_bytes_sent": 0,
        "forward_messages_sent": 0,
        "reverse_bytes_requested": 0,
        "reverse_bytes_received": 0,
        "reverse_messages_received": 0,
        "target_duration_s": duration_seconds(row),
        "status": "started",
    }

    if protocol not in (6, "6"):
        stats["status"] = f"skipped: unsupported protocol {protocol}; this client emulates TCP only"
        return stats

    try:
        sizes, target_total, fwd_meta = exact_packet_size_sequence(row, "fwd")
        iats = build_iat_sequence(row, len(sizes), params) if params.get("use_fwd_iat", True) else []
        iats = inject_active_idle(iats, row, params)
        target_duration = duration_seconds(row)
        reverse_requests, total_reverse, target_bwd_pkts, exact_bwd_count, bwd_meta = make_reverse_requests(row, len(sizes), params)

        stats.update({
            "forward_bytes_target": target_total,
            "reverse_bytes_requested": sum(reverse_requests),
            "target_fwd_packets": len(sizes),
            "target_bwd_packets": target_bwd_pkts,
            "exact_bwd_count_feasible_with_current_server": exact_bwd_count,
            "fwd_actual_min": fwd_meta.get("actual_min", 0),
            "fwd_actual_max": fwd_meta.get("actual_max", 0),
            "fwd_actual_mean": fwd_meta.get("actual_mean", 0),
            "fwd_actual_std": fwd_meta.get("actual_std", 0),
            "bwd_planned_min": bwd_meta.get("actual_min", 0),
            "bwd_planned_max": bwd_meta.get("actual_max", 0),
        })

        if logger:
            logger.info(
                f"[FLOW {flow_id}] {ip_client}:{sport}->{ip_server}:{dport} "
                f"fwd={target_total}B/{len(sizes)}pkts min/max/mean/std="
                f"{fwd_meta.get('actual_min')}/{fwd_meta.get('actual_max')}/"
                f"{fwd_meta.get('actual_mean'):.2f}/{fwd_meta.get('actual_std'):.2f} "
                f"duration={target_duration:.6f}s iats={len(iats)} "
                f"bwd={total_reverse}B/{target_bwd_pkts}pkts exact_bwd={exact_bwd_count}"
            )

        sock = connect_tcp(ip_client, ip_server, sport, dport, float(params.get("connect_timeout", 10.0)), row, params)
        sock.settimeout(float(params.get("socket_timeout", 30.0)))
        stop_evt = threading.Event()
        rx_thread = threading.Thread(target=receiver_loop, args=(sock, stats, stop_evt), daemon=True)
        rx_thread.start()

        flow_start = time.monotonic()
        due_pkt = flow_start
        fill_byte = int(params.get("zero_payload_fill", 0))
        for pkt_idx, pkt_len in enumerate(sizes):
            if pkt_idx > 0:
                due_pkt += iats[pkt_idx - 1] if pkt_idx - 1 < len(iats) else 0.0
            wait = due_pkt - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            instruction = reverse_requests[pkt_idx] if pkt_idx < len(reverse_requests) else 0
            send_framed(sock, pkt_len, instruction, flow_id, pkt_idx, fill_byte)
            stats["forward_bytes_sent"] += int(pkt_len)
            stats["forward_messages_sent"] += 1

        # Keep the connection open until both target Flow Duration and Fwd IAT Total have elapsed.
        planned_end = flow_start + max(target_duration, sum(iats) if iats else 0.0)
        remaining_duration = planned_end - time.monotonic()
        if remaining_duration > 0:
            time.sleep(remaining_duration)

        try:
            sock.shutdown(socket.SHUT_WR)
        except Exception:
            pass
        time.sleep(float(params.get("post_send_wait", 0.25)))
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
    params = load_params(config_file)
    seed = params.get("seed")
    if seed is not None:
        random.seed(int(seed))
        np.random.seed(int(seed))
    setup_logger(csv_file, ip_client, debug)
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
    for candidate_df in (df, flows):
        if "Timestamp" in candidate_df.columns:
            parsed = [parse_timestamp(v) for v in candidate_df["Timestamp"]]
            parsed = [x for x in parsed if x is not None]
            if parsed:
                first_ts = min(parsed)
                break
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
    parser = argparse.ArgumentParser(description="Client TCP bidirezionale feature-aware per emulazione flussi CSV")
    parser.add_argument("csv_file")
    parser.add_argument("ip_client")
    parser.add_argument("ip_server")
    parser.add_argument("config_file", nargs="?")
    parser.add_argument("--no-debug", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    out = args.output or f"/results/bidir_dataset_{args.ip_client.replace('.', '_')}_{args.ip_server.replace('.', '_')}.csv"
    start_client(args.csv_file, args.ip_client, args.ip_server, out, args.config_file, not args.no_debug)
