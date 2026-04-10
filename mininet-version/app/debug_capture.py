#!/usr/bin/env python3
"""Debug dettagliato packet capture"""

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.log import setLogLevel, info
import time
import os


def debug_capture():
    """Verifica dettagliata cattura pacchetti"""
    
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
    
    # Configura switch in modalità normal
    s1.cmd('ovs-ofctl add-flow s1 action=normal')
    
    # Configura port mirroring per far vedere tutto il traffico al probe
    # Trova le porte
    info("\n*** Configurazione port mirroring\n")
    # Crea un mirror port che copia tutto il traffico verso il probe
    s1.cmd('ovs-vsctl -- set Bridge s1 mirrors=@m \
            -- --id=@probe-eth0 get Port s1-eth3 \
            -- --id=@m create Mirror name=mymirror select-all=true output-port=@probe-eth0')
    
    info("  - Port mirroring configurato\n")
    
    # Disabilita IPv6
    for host in [h1, h2, probe]:
        host.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
        host.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1 > /dev/null 2>&1')
        for intf in host.intfList():
            if intf.name != 'lo':
                host.cmd(f'sysctl -w net.ipv6.conf.{intf.name}.disable_ipv6=1 > /dev/null 2>&1')
    
    time.sleep(2)
    
    # Verifica interfaccia probe
    info("\n*** Interfacce probe:\n")
    info(probe.cmd('ip addr'))
    
    # Verifica permessi /pcap
    info("\n*** Permessi /pcap:\n")
    info(probe.cmd('ls -la /pcap'))
    
    # Test connettività
    info("\n*** Test ping h1 -> h2\n")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.2')
    info(result)
    
    # Avvia tcpdump in modo sincrono per 5 secondi
    info("\n*** Avvio tcpdump (5 secondi)...\n")
    
    # Usa popen per avviare tcpdump
    info("  - Avvio popen tcpdump\n")
    tcpdump_proc = probe.popen(
        ["tcpdump", "-i", "probe-eth0", "-nn", "ip", "-w", "/pcap/debug_capture.pcap"]
    )
    
    #Aspetta che tcpdump parta
    time.sleep(1)
    
    # Genera traffico
    info("  - Generazione traffico ping\n")
    h1.cmd('ping -c 5 10.0.0.2 > /dev/null &')
    h2.cmd('ping -c 5 10.0.0.1 > /dev/null &')
    
    # Aspetta
    time.sleep(4)
    
    # Ferma tcpdump
    info("  - Stop tcpdump\n")
    tcpdump_proc.terminate()
    tcpdump_proc.wait()
    
    time.sleep(0.5)
    
    # Verifica file creato
    info("\n*** Verifica file pcap:\n")
    info(probe.cmd('ls -lh /pcap/debug_capture.pcap'))
    
    info("\n*** Contenuto file:\n")
    result = probe.cmd('tcpdump -r /pcap/debug_capture.pcap -nn -c 20 2>&1')
    info(result)
    
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    debug_capture()
