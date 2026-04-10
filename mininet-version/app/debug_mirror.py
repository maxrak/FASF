#!/usr/bin/env python3
"""Debug port mirroring OVS"""

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.log import setLogLevel, info
import time


def debug_mirror():
    """Debug configurazione port mirroring"""
    
    info("*** Creazione rete\n")
    net = Mininet(controller=None, switch=OVSSwitch)
    
    s1 = net.addSwitch('s1')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    probe = net.addHost('probe', ip='10.0.0.254/24')
    
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(probe, s1)
    
    info("*** Avvio rete\n")
    net.start()
    s1.cmd('ovs-ofctl add-flow s1 action=normal')
    
    # Disabilita IPv6
    for host in [h1, h2, probe]:
        host.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
    
    time.sleep(1)
    
    info("\n*** Interfacce switch s1:\n")
    result = s1.cmd('ovs-ofctl show s1')
    info(result)
    
    info("\n*** Ports del bridge s1:\n")
    result = s1.cmd('ovs-vsctl list-ports s1')
    info(result)
    
    info("\n*** Configurazione port mirroring\n")
    # Lista le porte per trovare quella del probe
    ports = s1.cmd('ovs-vsctl list-ports s1').strip().split('\n')
    info(f"  - Porte disponibili: {ports}\n")
    
    # Il probe dovrebbe essere su s1-eth3 (ultima porta)
    probe_port = 's1-eth3'
    info(f"  - Porta probe: {probe_port}\n")
    
    # Configura mirroring
    s1.cmd(
        f'ovs-vsctl -- set Bridge s1 mirrors=@m '
        f'-- --id=@probeport get Port {probe_port} '
        f'-- --id=@m create Mirror name=testmirror select-all=true output-port=@probeport'
    )
    
    info("\n*** Verifica configurazione mirror:\n")
    result = s1.cmd('ovs-vsctl list Mirror')
    info(result)
    
    # Avvia tcpdump    
    info("\n*** Avvio tcpdump\n")
    tcpdump_proc = probe.popen(["tcpdump", "-i", "probe-eth0", "-nn", "ip", "-w", "/pcap/mirror_test.pcap"])
    time.sleep(1)
    
    # Genera traffico
    info("*** Generazione traffico ping\n")
    h1.cmd('ping -c 5 10.0.0.2 > /dev/null &')
    time.sleep(6)
    
    # Ferma tcpdump
    info("*** Stop tcpdump\n")
    tcpdump_proc.terminate()
    tcpdump_proc.wait()
    time.sleep(0.5)
    
    # Verifica file
    info("\n*** Verifica file catturato:\n")
    info(probe.cmd('ls -lh /pcap/mirror_test.pcap'))
    info("\n*** Contenuto:\n")
    info(probe.cmd('tcpdump -r /pcap/mirror_test.pcap -nn -c 20 2>&1'))
    
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    debug_mirror()
