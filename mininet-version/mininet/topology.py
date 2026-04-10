from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel


def create_network():

    net = Mininet(controller=Controller, link=TCLink)

    print("[+] Creazione nodi")

    h1 = net.addHost('h1', ip='10.0.0.1')  # client
    h2 = net.addHost('h2', ip='10.0.0.2')  # server
    h3 = net.addHost('h3', ip='10.0.0.3')  # probe

    s1 = net.addSwitch('s1')

    print("[+] Configurazione link realistici")

    net.addLink(h1, s1, delay='20ms', loss=1, bw=10)
    net.addLink(h2, s1, delay='20ms', loss=1, bw=10)
    net.addLink(h3, s1, delay='5ms', loss=0, bw=100)

    net.start()

    print("[+] Network avviata")

    return net, h1, h2, h3


if __name__ == "__main__":
    setLogLevel('info')

    net, h1, h2, h3 = create_network()

    CLI(net)

    net.stop()