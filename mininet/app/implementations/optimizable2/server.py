import argparse
import json
import logging
import os
import signal
import socket
import struct
import threading
import time
from datetime import datetime

MAGIC = b"FEMU"
VERSION = 2  # Allineato al client
HEADER_STRUCT = struct.Struct("!4sBBIIII")
HEADER_SIZE = HEADER_STRUCT.size

FLAG_CONFIG = 0x02

stop_event = threading.Event()

def setup_logger(server_ip=None, debug_enabled=True):
    if not debug_enabled: return None
    os.makedirs("/results/tmp", exist_ok=True)
    ip_safe = (server_ip or "0_0_0_0").replace(".", "_")
    log_file = f"/results/tmp/server_{ip_safe}_decoupled.log"
    logger = logging.getLogger("server_decoupled")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    fh = logging.FileHandler(log_file, mode="w")
    ch = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

def recv_exact(conn, n):
    chunks = []
    got = 0
    while got < n:
        data = conn.recv(n - got)
        if not data: return None
        chunks.append(data)
        got += len(data)
    return b"".join(chunks)

def bwd_sender_worker(conn, sizes, iats, flow_id, logger):
    """MOTORE BWD INDIPENDENTE: Spara i pacchetti Bwd schedulati usando i propri timer isolati."""
    if logger:
        logger.info(f"[BWD_ENGINE_START] Flusso {flow_id}: Avvio trasmissione di {len(sizes)} pacchetti Bwd.")
    try:
        zero_buffer = b"\x00" * 65536
        start_time = time.monotonic()
        due_time = start_time

        for idx, pkt_len in enumerate(sizes):
            if idx > 0:
                due_time += iats[idx - 1]
            wait = due_time - time.monotonic()
            if wait > 0:
                time.sleep(wait)

            header = HEADER_STRUCT.pack(MAGIC, VERSION, 0, 0, pkt_len, int(flow_id), idx)
            conn.sendall(header)
            
            left = pkt_len
            while left > 0:
                n = min(len(zero_buffer), left)
                conn.sendall(zero_buffer[:n])
                left -= n
        if logger:
            logger.info(f"[BWD_ENGINE_DONE] Flusso {flow_id}: Riproduzione sequenza Bwd completata con successo.")
    except Exception as exc:
        if logger:
            logger.error(f"[BWD_ENGINE_ERROR] Errore nel flusso {flow_id}: {exc}")

def handle(conn, addr, local_port, logger=None):
    peer = f"{addr[0]}:{addr[1]}"
    conn.settimeout(30.0)
    bwd_thread = None
    try:
        while not stop_event.is_set():
            header = recv_exact(conn, HEADER_SIZE)
            if not header: break
            
            magic, version, flags, reverse_bytes, payload_len, flow_id, burst_id = HEADER_STRUCT.unpack(header)
            if magic != MAGIC or version != VERSION: break

            # Intercettazione Configurazione Iniziale inviata dal Client
            if flags & FLAG_CONFIG:
                config_data = recv_exact(conn, payload_len)
                bwd_plan = json.loads(config_data.decode("utf-8"))
                
                # Istanziazione del generatore parallelo Bwd
                bwd_thread = threading.Thread(
                    target=bwd_sender_worker, 
                    args=(conn, bwd_plan["sizes"], bwd_plan["iats"], flow_id, logger),
                    daemon=True
                )
                bwd_thread.start()
                continue

            # Processamento normale del traffico Fwd (Ingresso)
            remaining = payload_len
            while remaining > 0:
                chunk = conn.recv(min(65536, remaining))
                if not chunk: break
                remaining -= len(chunk)

    except Exception as exc:
        if logger: logger.error(f"[ERROR] Connessione {peer}: {exc}")
    finally:
        try: conn.close()
        except Exception: pass

def serve_port(bind_ip, port, logger):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try: s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception: pass
    s.bind((bind_ip, int(port)))
    s.listen(1024)
    s.settimeout(1.0)

    while not stop_event.is_set():
        try:
            conn, addr = s.accept()
        except socket.timeout: continue
        except OSError: break
        threading.Thread(target=handle, args=(conn, addr, port, logger), daemon=True).start()
    try: s.close()
    except Exception: pass

def parse_ports(value):
    ports = set()
    for part in value.split(","):
        part = part.strip()
        if not part: continue
        if "-" in part:
            a, b = part.split("-", 1)
            ports.update(range(int(a), int(b) + 1))
        else: ports.add(int(part))
    return sorted(list(ports))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="0.0.0.0")
    parser.add_argument("--ports", default="53,80,443,9000")
    parser.add_argument("--no-debug", action="store_true")
    args = parser.parse_args()

    logger = setup_logger(args.ip, not args.no_debug)
    ports = parse_ports(args.ports)

    def sig_handler(s, f): stop_event.set()
    signal.signal(signal.SIGINT, sig_handler)

    print(f"[+] Server Decoupled attivo sulle porte: {ports}")
    for port in ports:
        threading.Thread(target=serve_port, args=(args.ip, port, logger), daemon=True).start()

    while not stop_event.is_set():
        stop_event.wait(1.0)