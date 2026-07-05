#!/usr/bin/env python3
"""
Wrapper semplificato per testare implementazioni client
Fornisce interfaccia uniforme: dst_ip dst_port duration
"""

import sys
import socket
from scapy.all import *

def get_if_addr_safe():
    """Ottiene IP dell'interfaccia in modo sicuro"""
    try:
        return get_if_addr(conf.iface)
    except:
        return "127.0.0.1"


# Importa la funzione send_traffic dal modulo originale
import importlib.util
from pathlib import Path

# Carica il modulo client originale
spec = importlib.util.spec_from_file_location("client_orig", Path(__file__).parent / "client.py")
client_orig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_orig)


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_client.py <dst_ip> <dst_port> [duration]")
        sys.exit(1)
    
    dst_ip = sys.argv[1]
    dst_port = int(sys.argv[2])
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    src_ip = get_if_addr_safe()
    
    print(f"[TEST] Invio traffico da {src_ip} a {dst_ip}:{dst_port} per {duration}s")
    
    # Usa la funzione originale
    client_orig.send_traffic(src_ip, dst_ip, dst_port, duration, pps=10)


if __name__ == '__main__':
    main()
