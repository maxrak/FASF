#!/usr/bin/env python3
"""
Client semplificato per replay di traffico di rete
Accetta IP destinazione e porta dalla riga di comando
"""

import sys
import time
import random
from scapy.all import *


def tcp_handshake(src_ip, dst_ip, sport, dport):
    """Esegue handshake TCP"""
    seq = random.randint(0, 100000)
    
    syn = IP(src=src_ip, dst=dst_ip) / TCP(
        sport=sport, dport=dport, flags="S", seq=seq
    )
    synack = sr1(syn, timeout=2, verbose=0)
    
    if synack is None:
        return None, None
    
    ack = IP(src=src_ip, dst=dst_ip) / TCP(
        sport=sport,
        dport=dport,
        flags="A",
        seq=synack.ack,
        ack=synack.seq + 1
    )
    send(ack, verbose=0)
    
    return synack.ack, synack.seq + 1


def send_traffic(src_ip, dst_ip, dst_port, duration=30, packets_per_sec=10):
    """
    Invia traffico TCP da src a dst
    
    Args:
        src_ip: IP sorgente
        dst_ip: IP destinazione
        dst_port: porta destinazione
        duration: durata in secondi
        packets_per_sec: pacchetti al secondo
    """
    sport = random.randint(40000, 60000)
    
    print(f"[+] Connessione da {src_ip}:{sport} a {dst_ip}:{dst_port}")
    
    # Handshake
    seq, ack = tcp_handshake(src_ip, dst_ip, sport, dst_port)
    
    if seq is None:
        print(f"[-] Handshake fallito")
        return
    
    print(f"[+] Handshake completato, invio traffico per {duration}s")
    
    # Invia pacchetti
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        # Genera payload random
        payload_size = random.randint(100, 1500)
        payload = bytes([random.randint(0, 255) for _ in range(payload_size)])
        
        # Invia pacchetto PSH
        pkt = IP(src=src_ip, dst=dst_ip) / TCP(
            sport=sport,
            dport=dst_port,
            flags="PA",
            seq=seq,
            ack=ack
        ) / Raw(load=payload)
        
        send(pkt, verbose=0)
        seq += len(payload)
        packet_count += 1
        
        # Attendi prima del prossimo pacchetto
        time.sleep(1.0 / packets_per_sec)
    
    # Chiudi connessione (FIN)
    fin = IP(src=src_ip, dst=dst_ip) / TCP(
        sport=sport,
        dport=dst_port,
        flags="FA",
        seq=seq,
        ack=ack
    )
    send(fin, verbose=0)
    
    print(f"[+] Traffico completato: {packet_count} pacchetti inviati")


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python client_replay.py <dst_ip> <dst_port> [duration] [pps]")
        print("\nEsempi:")
        print("  python client_replay.py 10.0.0.2 9000")
        print("  python client_replay.py 10.0.0.2 9000 60 20")
        sys.exit(1)
    
    dst_ip = sys.argv[1]
    dst_port = int(sys.argv[2])
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    pps = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    
    # Ottieni l'IP sorgente dall'interfaccia
    src_ip = get_if_addr(conf.iface)
    
    send_traffic(src_ip, dst_ip, dst_port, duration, pps)


if __name__ == '__main__':
    main()
