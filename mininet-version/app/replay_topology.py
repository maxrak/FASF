#!/usr/bin/env python3
"""
Replay network topology from JSON and simulate traffic flows
"""

import json
import sys
import time
import pandas as pd
from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink


def adapt_csv_columns(csv_file, output_file='/tmp/flows_adapted.csv'):
    """
    Adatta il CSV per client_scapy_burst_optimized.py
    Rinomina 'Src IP' -> 'Source IP' e 'Dst IP' -> 'Destination IP'
    
    Args:
        csv_file: path al CSV originale
        output_file: path al CSV adattato
    
    Returns:
        path al CSV adattato
    """
    try:
        df = pd.read_csv(csv_file)
        
        # Rinomina le colonne se necessario
        column_mapping = {
            'Src IP': 'Source IP',
            'Dst IP': 'Destination IP'
        }
        
        df = df.rename(columns=column_mapping)
        df.to_csv(output_file, index=False)
        
        info(f"*** CSV adattato salvato in {output_file}\n")
        return output_file
    
    except Exception as e:
        info(f"*** Errore nell'adattamento del CSV: {e}\n")
        return csv_file


def load_topology(json_file):
    """Carica la topologia dal file JSON"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File '{json_file}' non trovato")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Errore nel parsing JSON: {e}")
        sys.exit(1)


def create_network_from_topology(topology, max_subnets=10):
    """
    Crea una rete Mininet dalla topologia JSON
    
    Args:
        topology: dizionario con la topologia di rete
        max_subnets: numero massimo di sottoreti da creare (per evitare topologie troppo complesse)
    
    Returns:
        net: oggetto Mininet
        host_map: dizionario IP -> host Mininet
        probe: nodo probe per cattura pacchetti (None se non presente)
    """
    info("*** Creazione rete Mininet\n")
    
    # Crea rete Mininet senza controller (standalone mode)
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
    
    # Mappa IP -> host Mininet
    host_map = {}
    
    # Switch unico centrale per tutti gli host (architettura semplificata)
    # Tutti gli host connessi direttamente a s0 per permettere port mirroring completo
    central_switch = net.addSwitch('s0')
    info("*** Switch centrale (gateway) creato: s0\n")
    
    # Limita il numero di sottoreti per evitare topologie troppo complesse
    subnets_to_create = topology['subnets'][:max_subnets]
    info(f"*** Creazione di {len(subnets_to_create)} sottoreti (su {len(topology['subnets'])} totali)\n")
    info("*** NOTA: tutti gli host connessi direttamente a s0 per cattura completa\n")
    
    # Crea gli host e connettili TUTTI direttamente a s0
    info("*** Creazione host (tutti connessi a s0)\n")
    host_counter = 1
    for subnet_info in subnets_to_create:
        subnet = subnet_info['network']
        
        for ip in subnet_info['hosts']:
            host_name = f"h{host_counter}"
            # Estrai la parte host dell'IP per l'interfaccia
            host = net.addHost(host_name, ip=f"{ip}/24")
            host_map[ip] = host
            
            # Connetti host direttamente al gateway centrale
            net.addLink(host, central_switch)
            
            info(f"  - Host {host_name}: {ip} (connesso a s0)\n")
            host_counter += 1
    
    # Crea il nodo probe se presente nella topologia
    probe = None
    if 'probe' in topology:
        probe_config = topology['probe']
        probe_name = probe_config.get('name', 'probe')
        probe_ip = probe_config.get('ip', '10.255.255.254/24')
        
        info("*** Creazione nodo probe per packet capture\n")
        probe = net.addHost(probe_name, ip=probe_ip)
        
        # Connetti il probe al gateway centrale (punto strategico per vedere tutto il traffico)
        net.addLink(probe, central_switch)
        
        info(f"  - Probe {probe_name}: {probe_ip} (connesso a s0)\n")
    
    # Ritorna il numero di host invece di subnet (per calcolo porta probe)
    num_hosts = len(host_map)
    return net, host_map, probe, num_hosts


def disable_ipv6(net, host_map, probe=None):
    """Disabilita IPv6 su tutti gli host per forzare l'uso di IPv4"""
    info("*** Disabilitazione IPv6 su tutti gli host\n")
    
    # Disabilita IPv6 su tutti gli host
    for ip, host in host_map.items():
        # Disabilita IPv6 globalmente
        host.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
        host.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1 > /dev/null 2>&1')
        host.cmd('sysctl -w net.ipv6.conf.lo.disable_ipv6=1 > /dev/null 2>&1')
        
        # Disabilita IPv6 su tutte le interfacce dell'host
        for intf in host.intfList():
            if intf.name != 'lo':
                host.cmd(f'sysctl -w net.ipv6.conf.{intf.name}.disable_ipv6=1 > /dev/null 2>&1')
    
    # Disabilita IPv6 anche sul probe
    if probe:
        probe.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
        probe.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1 > /dev/null 2>&1')
        probe.cmd('sysctl -w net.ipv6.conf.lo.disable_ipv6=1 > /dev/null 2>&1')
        
        # Disabilita IPv6 su tutte le interfacce del probe
        for intf in probe.intfList():
            if intf.name != 'lo':
                probe.cmd(f'sysctl -w net.ipv6.conf.{intf.name}.disable_ipv6=1 > /dev/null 2>&1')
        
        info("  - IPv6 disabilitato anche sul probe\n")
    
    # Disabilita IPv6 sugli switch
    for switch in net.switches:
        switch.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
        switch.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1 > /dev/null 2>&1')
    
    info("  - IPv6 disabilitato su tutti i nodi\n")
    
    # Attendi che le modifiche abbiano effetto
    time.sleep(1)


def start_servers(net, host_map):
    """Avvia il server su tutti gli host"""
    info("*** Avvio server su tutti gli host\n")
    
    for ip, host in host_map.items():
        # Avvia server TCP semplice invece di scapy (più affidabile)
        # server_tcp_simple.py gestisce handshake correttamente
        cmd = "python3 /app/server_tcp_simple.py > /tmp/server_{}.log 2>&1 &".format(
            ip.replace('.', '_')
        )
        host.cmd(cmd)
        info(f"  - Server avviato su {ip}\n")
    
    # Attendi che i server si avviino
    time.sleep(2)
    info("  - Server pronti\n")
    time.sleep(2)


def start_traffic_flows(net, host_map, flows, csv_file='/features/target.csv', duration=30):
    """
    Avvia i client per generare traffico tra gli host
    
    Args:
        net: rete Mininet
        host_map: mappa IP -> host
        flows: lista dei flussi da generare
        csv_file: path al CSV con i dati dei flussi originali
        duration: durata del traffico in secondi (non usato con client_scapy_burst_optimized)
    """
    info("*** Avvio generazione traffico\n")
    
    # Conta quanti flussi effettivi vengono avviati
    started = 0
    
    for flow in flows:
        src_ip = flow['src_ip']
        dst_ip = flow['dst_ip']
        
        src_host = host_map.get(src_ip)
        dst_host = host_map.get(dst_ip)
        
        if not src_host or not dst_host:
            info(f"  ! Host non trovato per flusso {src_ip} -> {dst_ip}\n")
            continue
        
        info(f"  - Traffico da {src_ip} a {dst_ip}\n")
        
        # Avvia client_scapy_burst_optimized.py in background
        # Parametri: flows.csv IPclient IPserver
        cmd = f"python3 /app/client_scapy_burst_optimized.py {csv_file} {src_ip} {dst_ip} > /tmp/client_{src_ip.replace('.', '_')}_{dst_ip.replace('.', '_')}.log 2>&1 &"
        src_host.cmd(cmd)
        started += 1
    
    info(f"*** {started} flussi di traffico avviati\n")


def run_topology_replay(json_file, csv_file='/features/target.csv', duration=60, max_subnets=10):
    """
    Esegue il replay della topologia
    
    Args:
        json_file: path al file JSON con la topologia
        csv_file: path al CSV con i dati dei flussi originali
        duration: durata in secondi (0 per modalità interattiva)
        max_subnets: numero massimo di sottoreti da creare
    """
    # Carica topologia
    info("*** Caricamento topologia da {}\n".format(json_file))
    topology = load_topology(json_file)
    
    # Adatta le statistiche per la nuova architettura
    stats = topology['statistics']
    info(f"*** Topologia: {stats.get('total_ips', 0)} host, "
         f"{stats.get('client_subnets', 0)} subnet client, "
         f"{stats.get('total_flows', 0)} flussi\n")
    
    # Crea rete
    net, host_map, probe, num_hosts = create_network_from_topology(topology, max_subnets)
    
    # Avvia rete
    info("*** Avvio rete\n")
    net.start()
    
    # Disabilita IPv6 per forzare IPv4
    disable_ipv6(net, host_map, probe)
    
    # Attendi che IPv6 sia completamente disabilitato
    info("*** Attesa disabilitazione completa IPv6...\n")
    time.sleep(2)
    
    # Configura switch in modalità standalone (learning switch)
    info("*** Configurazione switch in modalità standalone\n")
    for switch in net.switches:
        switch.cmd('ovs-ofctl add-flow {} action=normal'.format(switch.name))
    
    # Configura port mirroring sul gateway centrale per far vedere tutto il traffico al probe
    if probe:
        info("*** Configurazione port mirroring per probe\n")
        # Trova la porta dell'interfaccia del probe connessa al gateway (s0)
        # Il probe è connesso all'ultimo port del gateway after all subnet switches
        probe_config = topology.get('probe', {})
        interface = probe_config.get('interface', 'probe-eth0')
        
        # Calcola il numero di porta del probe: num_hosts host + 1
        # Tutti gli host sono connessi a s0: s0-eth1, s0-eth2, ..., s0-ethN (N=num_hosts)
        # Il probe è connesso dopo, quindi su s0-eth{N+1}
        probe_port_num = num_hosts + 1
        probe_port_name = f"s0-eth{probe_port_num}"
        
        # Configura mirror per copiare tutto il traffico verso il probe
        # select-all=true copia tutti i pacchetti in entrata e uscita
        central_switch = net.switches[0]  # s0 è sempre il primo switch (gateway)
        central_switch.cmd(
            f'ovs-vsctl -- set Bridge s0 mirrors=@m '
            f'-- --id=@probeport get Port {probe_port_name} '
            f'-- --id=@m create Mirror name=probe_mirror select-all=true output-port=@probeport'
        )
        info(f"  - Port mirroring configurato: s0:{probe_port_name} -> {interface}\n")
    
    # Avvia packet capture sul probe
    tcpdump_proc = None  # Dichiarato qui per poterlo usare alla fine
    if probe:
        probe_config = topology.get('probe', {})
        capture_file = probe_config.get('capture_file', '/pcap/capture.pcap')
        interface = probe_config.get('interface', 'probe-eth0')
        capture_filter = probe_config.get('capture_filter', '')
        
        info(f"*** Avvio packet capture sul probe\n")
        info(f"  - File: {capture_file}\n")
        info(f"  - Interface: {interface}\n")
        info(f"  - Filtro: Solo IPv4 ('ip')\n")
        
        # Costruisci comando tcpdump con filtro BPF per catturare solo IPv4
        # Il filtro 'ip' esclude IPv6, ARP e altri protocolli
        # Usa popen con lista di argomenti invece di cmd con & (KeyError: 'SHELL')
        tcpdump_args = ["tcpdump", "-i", interface, "-w", capture_file]
        
        # Se c'è un filtro custom, combinalo con il filtro IPv4
        if capture_filter:
            tcpdump_args.append(f"ip and ({capture_filter})")
        else:
            tcpdump_args.append("ip")
        
        tcpdump_proc = probe.popen(tcpdump_args)
        time.sleep(1)  # Attendi che tcpdump si avvii
        info("  - Packet capture avviata (solo IPv4)\n")
    
    # Avvia server
    start_servers(net, host_map)
    
    # Adatta il CSV per compatibilità con client_scapy_burst_optimized.py
    adapted_csv = adapt_csv_columns(csv_file)
    
    # Avvia traffico
    if 'flows' in topology and topology['flows']:
        start_traffic_flows(net, host_map, topology['flows'], adapted_csv, duration)
    
    # Attendi o apri CLI
    if duration > 0:
        info(f"*** Esecuzione per {duration} secondi\n")
        time.sleep(duration)
        
        info("*** Cattura traffico completata\n")
    else:
        info("*** Modalità interattiva - usa 'exit' per terminare\n")
        CLI(net)
    
    # Ferma packet capture
    if tcpdump_proc:
        info("*** Arresto packet capture\n")
        tcpdump_proc.terminate()
        tcpdump_proc.wait()
        time.sleep(0.5)
    
    # Cleanup
    info("*** Arresto rete\n")
    net.stop()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python replay_topology.py <topology.json> [duration] [flows_csv] [max_subnets]")
        print("\nEsempi:")
        print("  python replay_topology.py network_topology.json")
        print("  python replay_topology.py network_topology.json 60")
        print("  python replay_topology.py network_topology.json 60 /features/target.csv")
        print("  python replay_topology.py network_topology.json 60 /features/target.csv 20")
        print("  python replay_topology.py network_topology.json 0  # modalità interattiva")
        sys.exit(1)
    
    json_file = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    csv_file = sys.argv[3] if len(sys.argv) > 3 else '/features/target.csv'
    max_subnets = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    
    setLogLevel('info')
    run_topology_replay(json_file, csv_file, duration, max_subnets)


if __name__ == '__main__':
    main()
