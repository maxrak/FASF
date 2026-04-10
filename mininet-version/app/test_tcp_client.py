#!/usr/bin/env python3
"""Test client scapy minimale"""
from scapy.all import *
import sys

def test_tcp_syn():
    """Invia un SYN packet e attende SYN-ACK"""
    src_ip = sys.argv[1] if len(sys.argv) > 1 else '10.0.0.1'
    dst_ip = sys.argv[2] if len(sys.argv) > 2 else '10.0.0.2'
    
    print(f"[+] Test TCP handshake: {src_ip} -> {dst_ip}:9000")
    
    try:
        # Crea SYN packet
        syn = IP(src=src_ip, dst=dst_ip)/TCP(sport=12345, dport=9000, flags='S', seq=1000)
        print(f"[+] Invio SYN: {syn.summary()}")
        
        # Invia e attendi risposta
        response = sr1(syn, timeout=3, verbose=1)
        
        if response:
            print(f"[✅] Risposta ricevuta: {response.summary()}")
            if response.haslayer(TCP):
                tcp = response[TCP]
                print(f"    TCP flags: {tcp.flags}")
                print(f"    SEQ: {tcp.seq}, ACK: {tcp.ack}")
                
                if tcp.flags == "SA":
                    print("[✅] SYN-ACK ricevuto - Server funziona!")
                    return True
        else:
            print("[❌] Nessuna risposta (timeout)")
            return False
            
    except Exception as e:
        print(f"[❌] Errore: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_tcp_syn()
    sys.exit(0 if success else 1)
