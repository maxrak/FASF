#!/usr/bin/env python3
"""Test completo: port mirroring + ping + tcpdump con popen"""

from mininet.net import  Mininet
from mininet.node import OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import time


def test_complete():
    """Test completo del sistema"""
    
    info("*** Creazione rete con gateway centrale\n")
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
    
    # Gateway centrale
    s0 = net.addSwitch('s0')
    
    # 2 subnet switches
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    
    # Collegamenti subnet -> gateway
    net.addLink(s1, s0)  # s0-eth1
    net.addLink(s2, s0)  # s0-eth2
    
    # Host
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='172.16.0.1/24')
    
    # Collegamenti host -> subnet switch
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s2)
    
    # Probe
    probe = net.addHost('probe', ip='10.255.255.254/24')
    net.addLink(probe, s0)  # s0-eth3 (dopo 2 subnet switches)
    
    info("*** Avvio rete\n")
    net.start()
    
    # Configura switches in modalità normal
    for sw in net.switches:
        sw.cmd(f'ovs-ofctl add-flow {sw.name} action=normal')
    
    # Disabilita IPv6
    for host in [h1, h2, h3, probe]:
        host.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
    
    time.sleep(2)
    
    # Port mirroring su s0 -> probe (s0-eth3)
    info("*** Configurazione port mirroring\n")
    s0.cmd(
        'ovs-vsctl -- set Bridge s0 mirrors=@m '
        '-- --id=@probeport get Port s0-eth3 '
        '-- --id=@m create Mirror name=complete_test select-all=true output-port=@probeport'
    )
    
    # Verifica mirror
    info(s0.cmd('ovs-vsctl list Mirror'))
    
    # Avvia tcpdump con popen
    info("\n*** Avvio tcpdump\n")
    tcpdump_proc = probe.popen(["tcpdump", "-i", "probe-eth0", "-nn", "ip", "-w", "/pcap/complete_test.pcap"])
    time.sleep(1)
    
    # Genera traffico tra subnet diverse (passa per s0)
    info("*** Generazione traffico inter-subnet\n")
    info("  - h1 (10.0.0.1/subnet s1) -> h3 (172.16.0.1/subnet s2)\n")
    result = h1.cmd('ping -c 5 -W 2 172.16.0.1')
    info(result)
    
    # Genera traffico intra-subnet
    info("\n*** Generazione traffico intra-subnet\n")
    info("  - h1 -> h2 (stessa subnet s1)\n")
    result = h1.cmd('ping -c 5 -W 2 10.0.0.2')
    info(result)
    
    time.sleep(2)
    
    # Ferma tcpdump
    info("\n*** Arresto tcpdump\n")
    tcpdump_proc.terminate()
    tcpdump_proc.wait()
    time.sleep(0.5)
    
    # Verifica file
    info("\n*** Verifica file catturato:\n")
    info(probe.cmd('ls -lh /pcap/complete_test.pcap'))
    info("\n*** Contenuto (primi 20 pacchetti):\n")
    info(probe.cmd('tcpdump -r /pcap/complete_test.pcap -nn -c 20 2>&1'))
    
    # Statistiche
    info("\n*** Statistiche finali:\n")
    result = probe.cmd('tcpdump -r /pcap/complete_test.pcap -nn 2>&1 | tail -3')
    info(result)
    
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    test_complete()
