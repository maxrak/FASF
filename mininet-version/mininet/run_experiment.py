from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
import time
import os


def run():

    net = Mininet(controller=Controller, link=TCLink)

    h1 = net.addHost('h1', ip='10.0.0.1')
    h2 = net.addHost('h2', ip='10.0.0.2')
    h3 = net.addHost('h3', ip='10.0.0.3')

    s1 = net.addSwitch('s1')

    net.addLink(h1, s1, delay='50ms', loss=1)
    net.addLink(h2, s1, delay='50ms', loss=1)
    net.addLink(h3, s1)

    net.start()

    print("[+] Avvio server")
    h2.cmd("python3 /app/server_adv.py &")

    print("[+] Avvio probe")
    h3.cmd("tcpdump -i h3-eth0 -w /pcap/capture.pcap &")

    time.sleep(2)

    print("[+] Avvio client")
    h1.cmd("python3 /app/client_scapy_burst_optimized.py /app/flows.csv 10.0.0.1 10.0.0.2 &")

    time.sleep(60)

    print("[+] Stop capture")
    h3.cmd("pkill tcpdump")

    net.stop()


if __name__ == "__main__":
    run()