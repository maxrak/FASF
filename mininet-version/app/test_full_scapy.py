#!/usr/bin/env python3
"""Test completo client-server scapy con logging"""

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.log import setLogLevel, info
import time


def test_client_server():
    """Test completo client-server con scapy"""
    
    info("*** Creazione rete\n")
    net = Mininet(controller=None, switch=OVSSwitch)
    
    s0 = net.addSwitch('s0')
    server = net.addHost('server', ip='10.0.0.2/24')
    client = net.addHost('client', ip='10.0.0.1/24')
    
    net.addLink(server, s0)
    net.addLink(client, s0)
    
    info("*** Avvio rete\n")
    net.start()
    s0.cmd('ovs-ofctl add-flow s0 action=normal')
    
    # Disabilita IPv6
    for h in [server, client]:
        h.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
    
    time.sleep(1)
    
    # Test connettività
    info("\n*** Test ping\n")
    result = client.cmd('ping -c 2 10.0.0.2')
    if 'ttl' in result.lower():
        info("  ✅ Connettività OK\n")
    else:
        info("  ❌ Connettività fallita\n")
        info(result)
    
    # Avvia server
    info("\n*** Avvio server_adv.py su 10.0.0.2\n")
    server.cmd('python3 /app/server_adv.py > /tmp/server_test.log 2>&1 &')
    time.sleep(2)
    
    # Verifica server running
    ps_result = server.cmd('ps aux | grep server_adv | grep -v grep')
    if ps_result.strip():
        info(f"  ✅ Server running (PID visible)\n")
    else:
        info("  ❌ Server NON running\n")
    
    # Test client
    info("\n*** Test client scapy (test_tcp_client.py)\n")
    result = client.cmd('python3 /app/test_tcp_client.py 10.0.0.1 10.0.0.2 2>&1')
    info(result)
    
    # Controlla log server
    info("\n*** Log server (ultimi 20 righe):\n")
    log = server.cmd('cat /tmp/server_test.log 2>&1 | tail -20')
    if log.strip():
        info(log)
    else:
        info("  (vuoto - nessun output dal server)\n")
    
    # Verifica se server sta ancora girando
    info("\n*** Status finale server:\n")
    ps_final = server.cmd('ps aux | grep python | grep -v grep')
    info(ps_final if ps_final.strip() else "  Nessun processo Python\n")
    
    # Cleanup
    server.cmd('pkill -9 -f server_adv')
    
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    test_client_server()
