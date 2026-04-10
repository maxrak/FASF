#!/usr/bin/env python3
"""Test se scapy RAW sockets funziona in Mininet hosts"""

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.log import setLogLevel, info
import time


def test_scapy():
    """Test scapy send/receive in Mininet"""
    
    info("*** Creazione rete\n")
    net = Mininet(controller=None, switch=OVSSwitch)
    
    s0 = net.addSwitch('s0')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    
    net.addLink(h1, s0)
    net.addLink(h2, s0)
    
    info("*** Avvio rete\n")
    net.start()
    s0.cmd('ovs-ofctl add-flow s0 action=normal')
    
    # Disabilita IPv6
    for h in [h1, h2]:
        h.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
    
    time.sleep(1)
    
    # Test 1: Verifica connettività base
    info("\n*** Test 1: Ping base\n")
    result = h1.cmd('ping -c 2 10.0.0.2')
    info(result)
    
    # Test 2: Server TCP scapy su h2
    info("\n*** Test 2: Avvio server scapy su h2 (porta 9000)\n")
    h2.cmd('python3 /app/server_adv.py > /tmp/test_server.log 2>&1 &')
    time.sleep(2)
    
    # Verifica se server è partito
    result = h2.cmd('ps aux | grep server_adv | grep -v grep')
    if result.strip():
        info(f"  ✅ Server partito: {result}\n")
    else:
        info("  ❌ Server NON partito\n")
    
    # Test 3: Client scapy send TCP SYN
    info("\n*** Test 3: Invio TCP SYN con scapy da h1\n")
    test_scapy_cmd = """
python3 -c "
from scapy.all import *
import sys

# Prova a inviare un SYN packet
try:
    syn = IP(src='10.0.0.1', dst='10.0.0.2')/TCP(sport=12345, dport=9000, flags='S', seq=1000)
    print('[+] Invio SYN packet...')
    send(syn, verbose=0)
    print('[✅] Packet inviato con successo!')
    
    # Prova a ricevere SYN-ACK
    print('[+] Attesa SYN-ACK...')
    response = sr1(syn, timeout=2, verbose=0)
    if response:
        print(f'[✅] Ricevuto: {response.summary()}')
    else:
        print('[⚠️] Nessuna risposta ricevuta (timeout)')
except Exception as e:
    print(f'[❌] Errore: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1
    """
    
    result = h1.cmd(test_scapy_cmd)
    info(result)
    
    # Verifica log server
    info("\n*** Log server:\n")
    log = h2.cmd('cat /tmp/test_server.log 2>/dev/null | head -20')
    info(log if log.strip() else "  (vuoto)\n")
    
    # Cleanup
    h2.cmd('pkill -f server_adv')
    
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    test_scapy()
