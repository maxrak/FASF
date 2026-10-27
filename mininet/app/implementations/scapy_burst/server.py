from scapy.all import *
import os
import sys
import logging
import socket
from datetime import datetime

# ---------------------------
# LOGGER SETUP
# ---------------------------
def setup_logger(server_ip=None, debug_enabled=True):
    """Configura il logger per il server"""
    if not debug_enabled:
        return None
    
    # Se IP non fornito, prova a rilevarlo
    if not server_ip:
        try:
            hostname = socket.gethostname()
            server_ip = socket.gethostbyname(hostname)
        except:
            server_ip = "unknown"
    
    ip_safe = server_ip.replace('.', '_').replace(':', '_')
    
    # Nome file log: server_{ip}.log
    log_file = f"/results/tmp/tmp/server_{ip_safe}.log"
    
    # Configura logger
    logger = logging.getLogger(f'server_{ip_safe}')
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
    logger.info(f"SERVER DEBUG LOG")
    logger.info(f"Server IP: {server_ip}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("="*60)
    
    print(f"[+] Log server salvato in: {log_file}")
    
    return logger


# Parse parametri
debug = True
iface = None  # Interfaccia di rete (None = tutte)
server_ip = None  # IP del server per logging

for arg in sys.argv[1:]:
    if arg == "--no-debug":
        debug = False
    elif arg.startswith("--iface="):
        iface = arg.split("=")[1]
    elif arg.startswith("--ip="):
        server_ip = arg.split("=")[1]
    elif not arg.startswith("--"):
        # Backward compatibility: primo argomento è l'interfaccia
        if not iface:
            iface = arg

logger = setup_logger(server_ip, debug)

if logger:
    logger.info("Avvio server scapy su tutte le porte TCP...")

# Disabilita RST automatico del kernel su TUTTE le porte TCP
# Altrimenti il kernel risponde con RST prima che scapy possa gestire il pacchetto
os.system("iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP 2>/dev/null")

if logger:
    logger.info("Regola iptables configurata: DROP RST automatici del kernel")

def handle(pkt):
    if pkt.haslayer(TCP):
        ip = pkt[IP]
        tcp = pkt[TCP]
        
        # Log ogni pacchetto TCP ricevuto (anche se non gestito)
        if logger:
            logger.debug(f"[PKT] Ricevuto: {ip.src}:{tcp.sport} -> {ip.dst}:{tcp.dport} flags={tcp.flags}")

        if tcp.flags == "S":
            if logger:
                logger.info(f"[SYN] Ricevuto da {ip.src}:{tcp.sport} -> {ip.dst}:{tcp.dport} (seq={tcp.seq})")
            
            response = IP(dst=ip.src, src=ip.dst) / TCP(
                sport=tcp.dport, 
                dport=tcp.sport,
                flags="SA", 
                seq=1000, 
                ack=tcp.seq + 1
            )
            
            if logger:
                logger.info(f"[SYN-ACK] Invio a {ip.src}:{tcp.sport} <- {ip.dst}:{tcp.dport} (seq=1000, ack={tcp.seq + 1})")
            
            send(response, verbose=0)

        elif "P" in tcp.flags:
            payload_len = len(tcp.payload) if tcp.payload else 0
            
            if logger:
                logger.debug(f"[PSH-ACK] Ricevuto da {ip.src}:{tcp.sport} -> {ip.dst}:{tcp.dport} (seq={tcp.seq}, ack={tcp.ack}, payload={payload_len}B)")
            
            response = IP(dst=ip.src, src=ip.dst) / TCP(
                sport=tcp.dport, 
                dport=tcp.sport,
                flags="A",
                seq=tcp.ack,
                ack=tcp.seq + payload_len
            )
            
            if logger:
                logger.debug(f"[ACK] Invio a {ip.src}:{tcp.sport} <- {ip.dst}:{tcp.dport} (seq={tcp.ack}, ack={tcp.seq + payload_len})")
            
            send(response, verbose=0)
        
        elif tcp.flags == "A":
            # ACK puro (handshake completion)
            if logger:
                logger.debug(f"[ACK] Ricevuto da {ip.src}:{tcp.sport} -> {ip.dst}:{tcp.dport} (seq={tcp.seq}, ack={tcp.ack})")
        
        elif "F" in tcp.flags:
            # FIN: chiusura connessione
            if logger:
                logger.info(f"[FIN] Ricevuto da {ip.src}:{tcp.sport} -> {ip.dst}:{tcp.dport} (seq={tcp.seq})")
    else:
        # Pacchetto non TCP ricevuto (non dovrebbe succedere con filtro BPF)
        if logger:
            logger.debug(f"[PKT] Pacchetto non-TCP ricevuto (tipo={pkt.summary()})")


if logger:
    if iface:
        logger.info(f"Server in ascolto su interfaccia {iface}, tutte le porte TCP...")
    else:
        logger.info("Server in ascolto su tutte le interfacce, tutte le porte TCP...")
    logger.info("Pronto a ricevere connessioni.")

# Ascolta su tutte le porte TCP invece che solo una specifica
# Se specificata un'interfaccia, usa quella, altrimenti sniffa su tutte
if iface:
    if logger:
        logger.info(f"Sniffing su interfaccia: {iface}")
        logger.info("Modalità: promiscua, filtro BPF: tcp")
    # promisc=True per catturare tutti i pacchetti sull'interfaccia
    # store=False per non memorizzare pacchetti (risparmio memoria)
    sniff(iface=iface, filter="tcp", prn=handle, store=False, promisc=True)
else:
    if logger:
        logger.info("Sniffing su tutte le interfacce")
    sniff(filter="tcp", prn=handle, store=False, promisc=True)