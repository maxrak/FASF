#!/usr/bin/env python3
"""Test client_scapy_burst_optimized con CSV e server reale"""

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.log import setLogLevel, info
import time


def test_with_csv():
    """Test con CSV e server TCP reale"""
    
    info("*** Creazione rete\n")
    net = Mininet(controller=None, switch=OVSSwitch)
    
    s0 = net.addSwitch('s0')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    probe = net.addHost('probe', ip='10.0.0.254/24')
    
    net.addLink(h1, s0)
    net.addLink(h2, s0)
    net.addLink(probe, s0)
    
    info("*** Avvio rete\n")
    net.start()
    s0.cmd('ovs-ofctl add-flow s0 action=normal')
    
    # Disabilita IPv6
    for h in [h1, h2, probe]:
        h.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
    
    time.sleep(1)
    
    # Port mirroring
    info("*** Port mirroring su s0-eth3 (probe)\n")
    s0.cmd(
        'ovs-vsctl -- set Bridge s0 mirrors=@m '
        '-- --id=@probeport get Port s0-eth3 '
        '-- --id=@m create Mirror name=test_mirror select-all=true output-port=@probeport'
    )
    
    # Avvia tcpdump
    info("*** Avvio tcpdump su probe\n")
    tcpdump_proc = probe.popen(["tcpdump", "-i", "probe-eth0", "-nn", "ip", "-w", "/pcap/test_csv.pcap"])
    time.sleep(1)
    
    # Avvia server TCP semplice su h2
    info("*** Avvio server TCP su h2:9000\n")
    h2.cmd('python3 /app/server_tcp_simple.py > /tmp/server_tcp.log 2>&1 &')
    time.sleep(2)
    
    # Verifica server
    ps = h2.cmd('ss -tlnp | grep 9000')
    if '9000' in ps:
        info("  ✅ Server in ascolto su porta 9000\n")
    else:
        info("  ⚠️ Server potrebbe non essere in ascolto\n")
    
    # Test connessione TCP base
    info("\n*** Test connessione TCP base h1 -> h2:9000\n")
    result = h1.cmd('timeout 2 bash -c "echo test | nc 10.0.0.2 9000" 2>&1')
    info(f"  Risultato: {result[:100]}\n")
    
    # Avvia client scapy
    info("\n*** Avvio client_scapy_burst_optimized\n")
    info("  CSV: /features/test_flows.csv\n")
    info("  Client IP: 10.0.0.1, Server IP: 10.0.0.2\n")
    
    h1.cmd('python3 /app/client_scapy_burst_optimized.py /features/test_flows.csv 10.0.0.1 10.0.0.2 > /tmp/client_test.log 2>&1 &')
    
    # Attendi generazione traffico (flow duration max 8 secondi nei test)
    info("*** Attesa 12 secondi per generazione traffico...\n")
    for i in range(12):
        time.sleep(1)
        info(".")
    info("\n")
    
    # Log client
    info("\n*** Log client (ultimi 30 righe):\n")
    log = h1.cmd('cat /tmp/client_test.log 2>&1 | tail -30')
    info(log if log.strip() else "  (vuoto)\n")
    
    # Log server
    info("\n*** Log server (ultimi 20 righe):\n")
    slog = h2.cmd('cat /tmp/server_tcp.log 2>&1 | tail -20')
    info(slog if slog.strip() else "  (vuoto)\n")
    
    # Ferma tcpdump
    info("\n*** Arresto tcpdump\n")
    tcpdump_proc.terminate()
    tcpdump_proc.wait()
    time.sleep(0.5)
    
    # Verifica pcap
    info("\n*** Verifica pcap catturato:\n")
    info(probe.cmd('ls -lh /pcap/test_csv.pcap'))
    info("\n*** Primi 20 pacchetti:\n")
    info(probe.cmd('tcpdump -r /pcap/test_csv.pcap -nn -c 20 2>&1'))
    
    # Cleanup
    h1.cmd('pkill -f client_scapy')
    h2.cmd('pkill -f server_tcp')
    
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    test_with_csv()
