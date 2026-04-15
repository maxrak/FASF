#!/usr/bin/env python3
"""
Replay network topology from JSON and simulate traffic flows
"""

import json
import sys
import os
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
        # Estrai netmask dalla configurazione subnet (es: "10.0.0.0/8" -> 8)
        subnet = subnet_info['network']
        netmask = subnet.split('/')[-1] if '/' in subnet else '24'
        
        for ip in subnet_info['hosts']:
            host_name = f"h{host_counter}"
            # Usa il netmask corretto dalla topologia invece di hardcodare /24
            host = net.addHost(host_name, ip=f"{ip}/{netmask}")
            host_map[ip] = host
            
            # Connetti host direttamente al gateway centrale
            net.addLink(host, central_switch)
            
            info(f"  - Host {host_name}: {ip}/{netmask} (connesso a s0)\n")
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


def start_servers(net, host_map, implementation='scapy_burst'):
    """
    Avvia il server su tutti gli host
    
    Args:
        net: rete Mininet
        host_map: mappa IP -> host
        implementation: tipo di implementazione da usare (scapy_burst, tcp_simple, flow_emulator)
    """
    info(f"*** Avvio server su tutti gli host (implementation: {implementation})\n")
    
    # Path al server in base all'implementazione scelta
    server_script = f"/app/implementations/{implementation}/server.py"
    
    for ip, host in host_map.items():
        # Avvia il server corretto in base all'implementazione
        # Passa IP e interfaccia per logging e sniffing corretto
        iface = f"{host.name}-eth0"
        cmd = "python3 {} --iface={} --ip={} > /tmp/server_{}_{}.log 2>&1 &".format(
            server_script,
            iface,
            ip,
            implementation,
            ip.replace('.', '_')
        )
        host.cmd(cmd)
        info(f"  - Server {implementation} avviato su {ip} (interfaccia {iface})\n")
    
    # Attendi che i server si avviino
    time.sleep(3)  # Tempo extra per permettere a scapy di inizializzare
    info("  - Server pronti\n")


def generate_flows_from_csv(csv_file, host_map, topology):
    """
    Genera lista di flussi dagli IP effettivamente creati e dal CSV
    Filtra solo flussi nella stessa subnet (usando netmask reale dalla topologia)
    
    Args:
        csv_file: path al CSV con i flussi
        host_map: mappa IP -> host degli host creati
        topology: dizionario topology per estrarre netmask corretti
    
    Returns:
        lista di dict con {src_ip, dst_ip} per flussi validi
    """
    try:
        df = pd.read_csv(csv_file)
        
        # Identifica colonne IP
        if "Source IP" in df.columns:
            src_col, dst_col = "Source IP", "Destination IP"
        elif "Src IP" in df.columns:
            src_col, dst_col = "Src IP", "Dst IP"
        else:
            info("  ! Colonne IP non trovate nel CSV\n")
            return []
        
        # Crea mappa IP -> subnet network per determinare se due IP sono nella stessa subnet
        ip_to_subnet = {}
        for subnet_info in topology['subnets']:
            subnet_network = subnet_info['network']  # es: "10.0.0.0/8"
            for ip in subnet_info['hosts']:
                ip_to_subnet[ip] = subnet_network
        
        # Trova tutti i flussi che hanno ENTRAMBI gli IP nella topologia creata
        valid_flows = []
        seen_pairs = set()  # Evita duplicati
        
        for _, row in df.iterrows():
            src_ip = str(row[src_col])
            dst_ip = str(row[dst_col])
            
            # Verifica che entrambi gli IP esistano come host
            if src_ip in host_map and dst_ip in host_map:
               #Verifica che siano nella stessa subnet (usando mappa dalla topologia)
                src_subnet = ip_to_subnet.get(src_ip)
                dst_subnet = ip_to_subnet.get(dst_ip)
                
                if not src_subnet or not dst_subnet:
                    continue  # Salta flussi cross-subnet o IP senza subnet mappata
                
                # Salta broadcast addresses (.255)
                if dst_ip.endswith('.255'):
                    continue
                
                # Evita duplicati (stessa coppia già vista)
                pair = tuple(sorted([src_ip, dst_ip]))
                if pair not in seen_pairs:
                    valid_flows.append({
                        'src_ip': src_ip,
                        'dst_ip': dst_ip
                    })
                    seen_pairs.add(pair)
        
        info(f"  - Flussi generati dal CSV: {len(valid_flows)} (solo same-subnet, no broadcast)\n")
        return valid_flows
        
    except Exception as e:
        info(f"  ! Errore generazione flows: {e}\n")
        return []


def start_traffic_flows(net, host_map, flows, csv_file='/features/target.csv', duration=30, config_dir='/app/flows_params', base_name=None, implementation='scapy_burst'):
    """
    Avvia i client per generare traffico tra gli host
    
    Args:
        net: rete Mininet
        host_map: mappa IP -> host
        flows: lista dei flussi da generare
        csv_file: path al CSV con i dati dei flussi originali
        duration: durata del traffico in secondi (non usato con client_scapy_burst_optimized)
        config_dir: directory dove si trovano i file di configurazione per IP
        base_name: nome base per i file di configurazione (se None, estratto da csv_file)
        implementation: tipo di implementazione da usare (scapy_burst, tcp_simple, flow_emulator)
    """
    info(f"*** Avvio generazione traffico (implementation: {implementation})\n")
    
    # Estrae il nome base dal CSV (senza path e senza estensione)
    import os
    if base_name is None:
        base_name = os.path.splitext(os.path.basename(csv_file))[0]
    info(f"  - Nome base flusso: {base_name}\n")
    info(f"  - Directory config: {config_dir}\n")
    
    # Path al client in base all'implementazione scelta
    client_script = f"/app/implementations/{implementation}/client.py"
    
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
        
        # Costruisce il path del file di configurazione per questo IP sorgente
        # Formato: {base_name}_{src_ip}.config
        src_ip_safe = src_ip.replace('.', '_').replace(':', '_')
        config_file = f"{config_dir}/{base_name}_{src_ip_safe}.config"
        
        info(f"  - Traffico da {src_ip} a {dst_ip}\n")
        info(f"    Config: {config_file}\n")
        
        # Avvia il client corretto in base all'implementazione
        # Parametri: flows.csv IPclient IPserver [config_file]
        # Il burst_dataset.csv viene salvato in /results/ (mappato in shared/results/)
        cmd = f"python3 {client_script} {csv_file} {src_ip} {dst_ip} {config_file} > /tmp/client_{implementation}_{src_ip.replace('.', '_')}_{dst_ip.replace('.', '_')}.log 2>&1 &"
        src_host.cmd(cmd)
        started += 1
    
    info(f"*** {started} flussi di traffico avviati\n")


def run_topology_replay(json_file, csv_file='/features/target.csv', duration=60, max_subnets=10, implementation='scapy_burst'):
    """
    Esegue il replay della topologia
    
    Args:
        json_file: path al file JSON con la topologia
        csv_file: path al CSV con i dati dei flussi originali
        duration: durata in secondi (0 per modalità interattiva)
        max_subnets: numero massimo di sottoreti da creare
        implementation: tipo di implementazione client/server da usare (scapy_burst, tcp_simple, flow_emulator)
    """
    # Estrae il nome base dal CSV per generare file PCAP con nome dinamico
    flow_name = os.path.splitext(os.path.basename(csv_file))[0]
    
    # Carica topologia
    info("*** Caricamento topologia da {}\n".format(json_file))
    topology = load_topology(json_file)
    
    # Sovrascrivi il nome del file PCAP con il nome del flusso
    if 'probe' in topology:
        topology['probe']['capture_file'] = f'pcap/capture_{flow_name}.pcap'
        info(f"*** File PCAP: capture_{flow_name}.pcap\n")
    
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
        capture_file = probe_config.get('capture_file', 'pcap/capture.pcap')
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
    start_servers(net, host_map, implementation)
    
    # Con molti host, serve più tempo perché server + switch siano pronti
    info("*** Attesa inizializzazione server e popolamento MAC table...\n")
    time.sleep(5)  # Tempo aggiuntivo per server
    
    # Usa pingall per popolare completamente ARP/MAC tables
    # Con molti host questo può richiedere tempo, limita il numero
    info("*** Popolamento tabelle ARP/MAC con ping di connettività\n")
    # Pingall completo solo per topologie piccole (<50 host)
    if len(host_map) < 50:
        net.pingAll()
    else:
        # Per topologie grandi, ping solo tra host che devono comunicare
        # Almeno testa connettività base
        info("  - Topologia grande: ping campionamento limitato\n")
        hosts_list = list(host_map.values())
        for i in range(min(10, len(hosts_list)-1)):
            hosts_list[i].cmd(f'ping -c 1 -W 1 {hosts_list[i+1].IP()} > /dev/null 2>&1')
        time.sleep(2)
    
    # Estrae il nome base dal CSV originale prima di adattarlo
    # (serve per trovare i file di configurazione)
    # Nota: flow_name già estratto all'inizio della funzione
    
    # Adatta il CSV per compatibilità con client_scapy_burst_optimized.py
    adapted_csv = adapt_csv_columns(csv_file)
    
    # Genera flows dinamicamente dagli IP effettivamente creati e dal CSV ADATTATO
    # Ignora i flows hardcoded nella topologia JSON (contengono IP obsoleti)
    info("*** Generazione flows da CSV e host creati\n")
    flows = generate_flows_from_csv(adapted_csv, host_map, topology)
    
    # Avvia traffico (passa flow_name dal CSV originale)
    if flows:
        start_traffic_flows(net, host_map, flows, adapted_csv, duration, base_name=flow_name, implementation=implementation)
    else:
        info("*** ATTENZIONE: Nessun flusso valido trovato!\n")
        info("    Verifica che il CSV contenga IP presenti nella topologia\n")
    
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
        print("Usage: python replay_topology.py <topology.json> [duration] [flows_csv] [max_subnets] [implementation]")
        print("\nEsempi:")
        print("  python replay_topology.py network_topology.json")
        print("  python replay_topology.py network_topology.json 60")
        print("  python replay_topology.py network_topology.json 60 /features/target.csv")
        print("  python replay_topology.py network_topology.json 60 /features/target.csv 20")
        print("  python replay_topology.py network_topology.json 60 /features/target.csv 20 scapy_burst")
        print("  python replay_topology.py network_topology.json 60 /features/target.csv 20 tcp_simple")
        print("  python replay_topology.py network_topology.json 0  # modalità interattiva")
        print("\nImplementazioni disponibili:")
        print("  - scapy_burst (default): client_scapy_burst_optimized.py + server_adv.py")
        print("  - tcp_simple: client_replay.py + server_tcp_simple.py")
        print("  - flow_emulator: flow_emulator.py + server_adv.py")
        sys.exit(1)
    
    json_file = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    csv_file = sys.argv[3] if len(sys.argv) > 3 else '/features/target.csv'
    max_subnets = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    implementation = sys.argv[5] if len(sys.argv) > 5 else 'scapy_burst'
    
    setLogLevel('info')
    run_topology_replay(json_file, csv_file, duration, max_subnets, implementation)


if __name__ == '__main__':
    main()
