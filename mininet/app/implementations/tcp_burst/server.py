import os
import sys
import logging
import socket
import threading
import signal
from datetime import datetime

stop_event = threading.Event()


def setup_logger(server_ip=None, debug_enabled=True):
    """Configura il logger per il server. Stessa interfaccia della versione Scapy."""
    if not debug_enabled:
        return None
    if not server_ip:
        try:
            hostname = socket.gethostname()
            server_ip = socket.gethostbyname(hostname)
        except Exception:
            server_ip = "unknown"
    os.makedirs('/results', exist_ok=True)
    ip_safe = server_ip.replace('.', '_').replace(':', '_')
    log_file = f"/results/server_{ip_safe}.log"
    logger = logging.getLogger(f'server_socket_{ip_safe}')
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
    logger.info('SERVER SOCKET DEBUG LOG')
    logger.info(f'Server IP: {server_ip}')
    logger.info(f'Timestamp: {datetime.now()}')
    logger.info('='*60)
    print(f"[+] Log server salvato in: {log_file}")
    return logger


def handle(conn, addr, local_port, logger=None):
    """
    Analogo logico di handle(pkt): consuma i byte della connessione TCP reale.
    Non risponde a livello applicativo: gli ACK TCP sono generati dal kernel.
    """
    total = 0
    conn.settimeout(10.0)
    peer = f"{addr[0]}:{addr[1]}"
    if logger:
        logger.info(f"[ACCEPT] {peer} -> local_port={local_port}")
    try:
        while not stop_event.is_set():
            data = conn.recv(65535)
            if not data:
                break
            total += len(data)
            if logger:
                logger.debug(f"[DATA] {peer} -> :{local_port} bytes={len(data)} total={total}")
    except socket.timeout:
        if logger:
            logger.warning(f"[TIMEOUT] {peer} -> :{local_port} dopo {total} byte")
    except Exception as e:
        if logger:
            logger.error(f"[ERROR] {peer} -> :{local_port}: {e}")
    finally:
        # Chiusura corretta TCP con FIN (four-way handshake)
        try:
            # Invia FIN al client prima di chiudere
            conn.shutdown(socket.SHUT_RDWR)
            if logger:
                logger.debug(f"[CLOSE] FIN inviato a {peer}")
        except Exception as e:
            if logger:
                logger.debug(f"[CLOSE] Shutdown error (connessione già chiusa?): {e}")
        
        try:
            conn.close()
        except Exception:
            pass
        if logger:
            logger.info(f"[CLOSE] {peer} -> :{local_port}, total_bytes={total}")


def _serve_port(bind_ip, port, logger):
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
        logger.info(f"[LISTEN] {bind_ip or '0.0.0.0'}:{port}")
    while not stop_event.is_set():
        try:
            conn, addr = s.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        t = threading.Thread(target=handle, args=(conn, addr, port, logger), daemon=True)
        t.start()
    try:
        s.close()
    except Exception:
        pass


def parse_ports(value):
    ports = set()
    for part in value.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            ports.update(range(int(a), int(b) + 1))
        else:
            ports.add(int(part))
    return sorted(p for p in ports if 1 <= p <= 65535)


def _signal_handler(signum, frame):
    stop_event.set()


# Parse parametri compatibili con server.py Scapy
if __name__ == '__main__':
    debug = True
    iface = None       # mantenuto per compatibilita', non usato dalle socket
    server_ip = None   # se fornito, bind su quell'IP; altrimenti 0.0.0.0
    ports = None

    for arg in sys.argv[1:]:
        if arg == '--no-debug':
            debug = False
        elif arg.startswith('--iface='):
            iface = arg.split('=', 1)[1]
        elif arg.startswith('--ip='):
            server_ip = arg.split('=', 1)[1]
        elif arg.startswith('--ports='):
            ports = parse_ports(arg.split('=', 1)[1])
        elif arg.startswith('--port-range='):
            ports = parse_ports(arg.split('=', 1)[1])
        elif not arg.startswith('--'):
            if not iface:
                iface = arg

    logger = setup_logger(server_ip, debug)
    bind_ip = server_ip if server_ip else '0.0.0.0'

    # Default: porte viste spesso nei dataset CIC/HTTP/HTTPS + fallback.
    # Per compatibilita' piena con dport arbitrari usa: --ports=1-65535, ma puo' richiedere root e molte fd.
    if ports is None:
        ports = [53, 80, 443, 139, 161, 445, 1900, 5351, 5355, 5480, 7001, 8443, 8080, 9000,50000]

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    if logger:
        logger.info('Avvio server socket TCP reale')
        if iface:
            logger.info(f'Parametro iface ricevuto per compatibilita: {iface}')
        logger.info(f'Bind IP: {bind_ip}')
        logger.info(f'Porte: {ports[:20]}{" ..." if len(ports) > 20 else ""}')

    print(f"[+] Server socket in ascolto su {bind_ip}, porte: {ports[:20]}{' ...' if len(ports) > 20 else ''}")

    threads = []
    failed = []
    for p in ports:
        try:
            t = threading.Thread(target=_serve_port, args=(bind_ip, p, logger), daemon=True)
            t.start()
            threads.append(t)
        except Exception as e:
            failed.append((p, str(e)))

    if failed:
        print(f"[!] Alcune porte non sono state avviate: {failed[:10]}")
        if logger:
            logger.warning(f"Porte fallite: {failed}")

    try:
        while not stop_event.is_set():
            signal.pause()
    except AttributeError:
        while not stop_event.is_set():
            stop_event.wait(1.0)
