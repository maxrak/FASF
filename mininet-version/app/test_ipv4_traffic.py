#!/usr/bin/env python3
"""
Test script per verificare traffico IPv4 in Mininet
Genera semplice traffico ping tra host per verificare:
1. IPv6 è disabilitato
2. Il probe cattura traffico IPv4
"""

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.log import setLogLevel, info
import time


def test_ipv4_traffic():
    """Test semplice per generare traffico IPv4"""
    
    info("*** Creazione rete di test\n")
    net = Mininet(controller=None, switch=OVSSwitch)
    
    # Crea switch
    s1 = net.addSwitch('s1')
    
    # Crea host
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    probe = net.addHost('probe', ip='10.0.0.254/24')
    
    # Collegamenti
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(probe, s1)
    
    # Avvia rete
    info("*** Avvio rete\n")
    net.start()
    
    # Configura switch
    s1.cmd('ovs-ofctl add-flow s1 action=normal')
    
    # Disabilita IPv6
    info("*** Disabilitazione IPv6\n")
    for host in [h1, h2, probe]:
        host.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
        host.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1 > /dev/null 2>&1')
        for intf in host.intfList():
            if intf.name != 'lo':
                host.cmd(f'sysctl -w net.ipv6.conf.{intf.name}.disable_ipv6=1 > /dev/null 2>&1')
    
    info("  - IPv6 disabilitato\n")
    time.sleep(2)  # Attendi che IPv6 sia completamente disabilitato
    
    # Avvia packet capture con filtro per solo IPv4 (in background con popen)
    info("*** Avvio packet capture sul probe (solo IPv4)\n")
    tcpdump_proc = probe.popen("tcpdump -i probe-eth0 'ip' -w /pcap/test_capture.pcap")
    time.sleep(1)
    
    # Test connettività
    info("*** Test connettività (ping)\n")
    info(f"  - h1 -> h2: ")
    result = h1.cmd('ping -c 5 -W 1 10.0.0.2')
    if '5 received' in result or '5 packets received' in result:
        info("OK\n")
    else:
        info("FAIL\n")
    
    # Genera più traffico
    info("*** Generazione traffico aggiuntivo\n")
    
    # Ping inverso
    info("  - h2 -> h1: ")
    result = h2.cmd('ping -c 5 -W 1 10.0.0.1')
    if '5 received' in result or '5 packets received' in result:
        info("OK\n")
    else:
        info("FAIL\n")
    
    # TCP - usa netcat per generare traffico TCP
    info("  - Test TCP h1 <-> h2...\n")
    h2.cmd('nc -l 8080 > /dev/null &')
    time.sleep(0.5)
    h1.cmd('echo "test message" | nc 10.0.0.2 8080 &')
    time.sleep(1)
    
    # Attendi per catturare più traffico
    info("*** Attesa per cattura traffico (5 secondi)...\n")
    time.sleep(5)
    
    # Ferma packet capture
    info("*** Arresto packet capture\n")
    tcpdump_proc.terminate()
    tcpdump_proc.wait()
    time.sleep(0.5)
    
    # Arresta rete
    info("*** Arresto rete\n")
    net.stop()
    
    info("\n✅ Test completato!\n")
    info("   File generato: /pcap/test_capture.pcap\n")
    info("\n📊 Verifica risultati:\n")
    info("   docker compose run --rm mininet tcpdump -r /pcap/test_capture.pcap -n -c 20\n")


if __name__ == '__main__':
    setLogLevel('info')
    test_ipv4_traffic()
