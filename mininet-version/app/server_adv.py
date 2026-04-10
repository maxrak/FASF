from scapy.all import *

SERVER_PORT = 9000


def handle(pkt):
    if pkt.haslayer(TCP):
        ip = pkt[IP]
        tcp = pkt[TCP]

        if tcp.flags == "S":
            send(IP(dst=ip.src, src=ip.dst) /
                 TCP(sport=tcp.dport, dport=tcp.sport,
                     flags="SA", seq=1000, ack=tcp.seq + 1),
                 verbose=0)

        elif "P" in tcp.flags:
            send(IP(dst=ip.src, src=ip.dst) /
                 TCP(sport=tcp.dport, dport=tcp.sport,
                     flags="A",
                     seq=tcp.ack,
                     ack=tcp.seq + len(tcp.payload)),
                 verbose=0)


sniff(filter=f"tcp port {SERVER_PORT}", prn=handle)