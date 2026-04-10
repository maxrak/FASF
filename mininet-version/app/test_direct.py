#!/usr/bin/env python3
"""Test: tutti gli host connessi direttamente al gateway con mirror"""

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import time


def test_direct():
    """Test con tutti gli host connessi direttamente a s0"""
    
    info("*** Creazione rete: tutti gli host su s0\n")
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
    
    # Un solo switch
    s0 = net.addSwitch('s0')
    
    # Host tutti connessi a s0
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    probe = net.addHost('probe', ip='10.0.0.254/24')
    
    net.addLink(h1, s0)  # s0-eth1
    net.addLink(h2, s0)  # s0-eth2
    net.addLink(h3, s0)  # s0-eth3
    net.addLink(probe, s0)  # s0-eth4
    
    info("*** Avvio rete\n")
    net.start()
    
    # Configura switch  
    s0.cmd('ovs-ofctl add-flow s0 action=normal')
    
    # Disabilita IPv6
    for host in [h1, h2, h3, probe]:
        host.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
    
    time.sleep(1)
    
    # Port mirroring su s0 -> probe (s0-eth4)
    info("*** Configurazione port mirroring su s0-eth4\n")
    s0.cmd(
        'ovs-vsctl -- set Bridge s0 mirrors=@m '
        '-- --id=@probeport get Port s0-eth4 '
        '-- --id=@m create Mirror name=direct_test select-all=true output-port=@probeport'
    )
    
    # Avvia tcpdump
    info("*** Avvio tcpdump\n")
    tcpdump_proc = probe.popen(["tcpdump", "-i", "probe-eth0", "-nn", "ip", "-w", "/pcap/direct_test.pcap"])
    time.sleep(1)
    
    # Genera traffico
    info("*** Generazione traffico\n")
    info("  - h1 -> h2\n")
    h1.cmd('ping -c 5 10.0.0.2')
    
    info("  - h2 -> h3\n")
    h2.cmd('ping -c 5 10.0.0.3')
    
    time.sleep(1)
    
    # Ferma tcpdump
    info("*** Arresto tcpdump\n")
    tcpdump_proc.terminate()
    tcpdump_proc.wait()
    time.sleep(0.5)
    
    # Verifica file
    info("\n*** Verifica file catturato:\n")
    info(probe.cmd('ls -lh /pcap/direct_test.pcap'))
    info("\n*** Contenuto:\n")
    info(probe.cmd('tcpdump -r /pcap/direct_test.pcap -nn -c 30 2>&1'))
    
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    test_direct()
