import argparse
import logging
import os
import signal
import socket
import struct
import threading
from datetime import datetime

MAGIC = b"FEMU"
VERSION = 1
HEADER_STRUCT = struct.Struct("!4sBBIIII")
HEADER_SIZE = HEADER_STRUCT.size
FLAG_REVERSE = 0x01

stop_event = threading.Event()


def setup_logger(server_ip=None, debug_enabled=True):
    if not debug_enabled:
        return None
    os.makedirs("/results/tmp", exist_ok=True)
    if not server_ip:
        try:
            server_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            server_ip = "unknown"
    ip_safe = server_ip.replace(".", "_").replace(":", "_")
    log_file = f"/results/tmp/server_{ip_safe}_bidirectional.log"
    logger = logging.getLogger(f"server_bidir_{ip_safe}")
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
    logger.info("SERVER BIDIRECTIONAL FLOW EMULATOR")
    logger.info(f"Server IP: {server_ip}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 70)
    print(f"[+] Log server salvato in: {log_file}")
    return logger


def parse_ports(value):
    ports = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            ports.update(range(int(a), int(b) + 1))
        else:
            ports.add(int(part))
    return sorted(p for p in ports if 1 <= p <= 65535)


def recv_exact(conn, n):
    chunks = []
    got = 0
    while got < n:
        data = conn.recv(n - got)
        if not data:
            return None
        chunks.append(data)
        got += len(data)
    return b"".join(chunks)


def drain_payload(conn, payload_len):
    remaining = int(payload_len)
    total = 0
    while remaining > 0:
        chunk = conn.recv(min(65536, remaining))
        if not chunk:
            break
        total += len(chunk)
        remaining -= len(chunk)
    return total


def send_reverse_burst(conn, total_bytes, flow_id, burst_id, chunk_size=1448):
    remaining = int(total_bytes)
    messages = 0
    zero = b"\x00" * 65536
    try:
        while remaining > 0:
            payload_len = min(chunk_size, remaining)
            header = HEADER_STRUCT.pack(MAGIC, VERSION, FLAG_REVERSE, 0, payload_len, int(flow_id), int(burst_id))
            conn.sendall(header)
            left = payload_len
            while left > 0:
                n = min(len(zero), left)
                conn.sendall(zero[:n])
                left -= n
            remaining -= payload_len
            messages += 1
    except Exception as exc:
        # Se c'è un errore, logga ma non crashare
        import logging
        logger = logging.getLogger()
        if logger:
            logger.error(f"[REVERSE_ERROR] flow={flow_id} burst={burst_id} sent={messages} msgs, error: {exc}")
        raise
    return messages


def handle(conn, addr, local_port, logger=None, reverse_chunk_size=1448):
    peer = f"{addr[0]}:{addr[1]}"
    total_rx_payload = 0
    total_reverse = 0
    messages = 0
    reverse_messages = 0
    conn.settimeout(30.0)
    if logger:
        logger.info(f"[ACCEPT] {peer} -> local_port={local_port}")
    try:
        while not stop_event.is_set():
            header = recv_exact(conn, HEADER_SIZE)
            if not header:
                if logger:
                    logger.debug(f"[CLOSE] {peer} -> :{local_port} header=None (connessione chiusa)")
                break
            magic, version, flags, reverse_bytes, payload_len, flow_id, burst_id = HEADER_STRUCT.unpack(header)
            if magic != MAGIC or version != VERSION:
                if logger:
                    logger.warning(f"[PROTO] Header non valido da {peer}: magic={magic!r} version={version}")
                break

            received = drain_payload(conn, payload_len)
            total_rx_payload += received
            messages += 1
            if logger:
                logger.debug(
                    f"[DATA] {peer} -> :{local_port} flow={flow_id} burst={burst_id} "
                    f"payload={payload_len} received={received} reverse_request={reverse_bytes}"
                )

            if reverse_bytes > 0:
                if logger:
                    logger.info(
                        f"[REVERSE_START] :{local_port} -> {peer} flow={flow_id} burst={burst_id} "
                        f"sending {reverse_bytes} bytes..."
                    )
                sent_msgs = send_reverse_burst(conn, reverse_bytes, flow_id, burst_id, reverse_chunk_size)
                reverse_messages += sent_msgs
                total_reverse += int(reverse_bytes)
                if logger:
                    logger.info(
                        f"[REVERSE_DONE] :{local_port} -> {peer} flow={flow_id} burst={burst_id} "
                        f"bytes={reverse_bytes} messages={sent_msgs}"
                    )
    except socket.timeout:
        if logger:
            logger.warning(f"[TIMEOUT] {peer} -> :{local_port} dopo {total_rx_payload} byte")
    except Exception as exc:
        if logger:
            logger.error(f"[ERROR] {peer} -> :{local_port}: {exc}")
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        if logger:
            logger.info(
                f"[CLOSE] {peer} -> :{local_port}, rx_payload={total_rx_payload}, "
                f"rx_messages={messages}, reverse_bytes={total_reverse}, reverse_messages={reverse_messages}"
            )


def serve_port(bind_ip, port, logger, reverse_chunk_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
    s.bind((bind_ip, int(port)))
    s.listen(1024)
    s.settimeout(1.0)
    if logger:
        logger.info(f"[LISTEN] {bind_ip}:{port}")
    while not stop_event.is_set():
        try:
            conn, addr = s.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        t = threading.Thread(target=handle, args=(conn, addr, port, logger, reverse_chunk_size), daemon=True)
        t.start()
    try:
        s.close()
    except Exception:
        pass


def signal_handler(signum, frame):
    stop_event.set()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Server TCP bidirezionale per emulazione flussi CSV")
    parser.add_argument("--ip", default=None, help="IP locale su cui fare bind. Default: 0.0.0.0")
    parser.add_argument("--iface", default=None, help="Interfaccia di rete (non usata, per compatibilità)")
    parser.add_argument("--ports", default="53,80,443,139,161,445,1900,5351,5355,5480,7001,8443,8080,9000,50000")
    parser.add_argument("--port-range", default=None, help="Alternativa a --ports, es. 1-65535")
    parser.add_argument("--reverse-chunk-size", type=int, default=1448)
    parser.add_argument("--no-debug", action="store_true")
    args = parser.parse_args()

    logger = setup_logger(args.ip, not args.no_debug)
    bind_ip = args.ip if args.ip else "0.0.0.0"
    ports = parse_ports(args.port_range if args.port_range else args.ports)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"[+] Server bidirezionale in ascolto su {bind_ip}, porte: {ports[:20]}{' ...' if len(ports) > 20 else ''}")
    if logger:
        logger.info(f"Bind IP: {bind_ip}")
        logger.info(f"Interfaccia (ignorata): {args.iface}")
        logger.info(f"Porte: {ports[:20]}{' ...' if len(ports) > 20 else ''}")
        logger.info(f"Numero totale porte: {len(ports)}")
        logger.info(f"Reverse chunk size: {args.reverse_chunk_size}")

    failed = []
    threads = []
    for port in ports:
        try:
            t = threading.Thread(target=serve_port, args=(bind_ip, port, logger, args.reverse_chunk_size), daemon=True)
            t.start()
            threads.append(t)
        except Exception as exc:
            failed.append((port, str(exc)))
            if logger:
                logger.error(f"Errore avvio porta {port}: {exc}")

    if failed:
        print(f"[!] Alcune porte non sono state avviate: {failed[:10]}")
        if logger:
            logger.warning(f"Porte fallite: {failed}")
    else:
        print(f"[+] Tutte le {len(ports)} porte avviate con successo")
        if logger:
            logger.info(f"Tutte le {len(ports)} porte avviate con successo")

    # Piccolo ritardo per dare tempo ai thread di fare bind
    import time
    time.sleep(0.5)
    
    if logger:
        logger.info("Server pronto ad accettare connessioni")
    print("[+] Server pronto ad accettare connessioni")

    while not stop_event.is_set():
        stop_event.wait(1.0)
