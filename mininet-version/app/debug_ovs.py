#!/usr/bin/env python3
"""Debug OVS configuration in Mininet"""

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.log import setLogLevel, info
import time


def debug_ovs():
    """Debug OVS switch configuration"""
    
    info("*** Creazione rete\n")
    net = Mininet(controller=None, switch=OVSSwitch)
    
    s1 = net.addSwitch('s1')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    
    info("*** Avvio rete\n")
    net.start()
    
    info("\n*** Verifica switch prima del flow\n")
    info(s1.cmd('ovs-ofctl show s1'))
    
    info("\n*** Aggiunta flow\n")
    result = s1.cmd('ovs-ofctl add-flow s1 action=normal')
    info(f"Risultato: {result}\n")
    
    time.sleep(1)
    
    info("\n*** Verifica flow installati\n")
    info(s1.cmd('ovs-ofctl dump-flows s1'))
    
    info("\n*** Test ping\n")
    result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
    info(result)
    
    info("\n*** Verifica interfacce h1\n")
    info(h1.cmd('ip addr'))
    
    info("\n*** Verifica interfacce h2\n")
    info(h2.cmd('ip addr'))
    
    info("\n*** Verifica ARP table h1\n")
    info(h1.cmd('arp -n'))
    
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    debug_ovs()
