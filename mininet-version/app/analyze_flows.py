#!/usr/bin/env python3
"""
Analizza flussi da CSV CICFlowMeter e conta coppie IP con porte diverse
"""

import sys
import csv
import json
import ipaddress
from collections import defaultdict
from pathlib import Path


def analyze_flows(csv_file):
    """
    Analizza un file CSV di flussi e conta le coppie IP con porte diverse
    
    Args:
        csv_file: path al file CSV da analizzare
    """
    # Dizionario per contare le coppie IP -> set di porte usate
    ip_pairs = defaultdict(lambda: {'src_ports': set(), 'dst_ports': set(), 'count': 0})
    
    # Set di tutti gli IP trovati
    all_ips = set()
    src_ips = set()  # IP sorgente
    dst_ips = set()  # IP destinazione
    
    total_flows = 0
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                total_flows += 1
                
                src_ip = row.get('Src IP', '').strip()
                src_port = row.get('Src Port', '').strip()
                dst_ip = row.get('Dst IP', '').strip()
                dst_port = row.get('Dst Port', '').strip()
                
                if not all([src_ip, src_port, dst_ip, dst_port]):
                    continue
                
                # Aggiungi IP ai set
                all_ips.add(src_ip)
                all_ips.add(dst_ip)
                src_ips.add(src_ip)
                dst_ips.add(dst_ip)
                
                # Crea la chiave della coppia IP (ordinata per consistenza)
                pair_key = f"{src_ip} <-> {dst_ip}"
                
                # Aggiungi le porte al set
                ip_pairs[pair_key]['src_ports'].add(src_port)
                ip_pairs[pair_key]['dst_ports'].add(dst_port)
                ip_pairs[pair_key]['count'] += 1
    
    except FileNotFoundError:
        print(f"❌ Errore: File '{csv_file}' non trovato")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Errore durante la lettura del file: {e}")
        sys.exit(1)
    
    return ip_pairs, total_flows, all_ips, src_ips, dst_ips


def print_results(ip_pairs, total_flows):
    """Stampa i risultati dell'analisi"""
    
    print("\n" + "="*80)
    print("📊 ANALISI FLUSSI DI RETE")
    print("="*80)
    print(f"\n📈 Totale flussi analizzati: {total_flows}")
    print(f"🔗 Coppie IP uniche: {len(ip_pairs)}")
    print("\n" + "-"*80)
    
    # Ordina per numero di flussi (decrescente)
    sorted_pairs = sorted(ip_pairs.items(), key=lambda x: x[1]['count'], reverse=True)
    
    for pair_key, data in sorted_pairs:
        src_ip, dst_ip = pair_key.split(' <-> ')
        num_src_ports = len(data['src_ports'])
        num_dst_ports = len(data['dst_ports'])
        total_port_combinations = num_src_ports * num_dst_ports
        
        print(f"\n🔹 {pair_key}")
        print(f"   └─ Flussi totali: {data['count']}")
        print(f"   └─ Porte sorgente uniche: {num_src_ports}")
        print(f"   └─ Porte destinazione uniche: {num_dst_ports}")
        print(f"   └─ Combinazioni porte possibili: {total_port_combinations}")
        
        # Mostra le porte se sono poche
        if num_src_ports <= 10:
            print(f"   └─ Porte src: {', '.join(sorted(data['src_ports'], key=int))}")
        if num_dst_ports <= 10:
            print(f"   └─ Porte dst: {', '.join(sorted(data['dst_ports'], key=int))}")
    
    print("\n" + "="*80)


def print_source_ips_analysis(src_ips, dst_ips):
    """
    Stampa l'analisi degli IP sorgente
    
    Args:
        src_ips: set di IP sorgente
        dst_ips: set di IP destinazione
    """
    print("\n" + "="*80)
    print("📡 ANALISI IP SORGENTE")
    print("="*80)
    
    print(f"\n🔵 IP Sorgente unici: {len(src_ips)}")
    print(f"🔴 IP Destinazione unici: {len(dst_ips)}")
    
    # IP che sono solo sorgente
    only_src = src_ips - dst_ips
    # IP che sono solo destinazione
    only_dst = dst_ips - src_ips
    # IP che sono sia sorgente che destinazione
    both = src_ips & dst_ips
    
    print(f"🟢 IP solo sorgente: {len(only_src)}")
    print(f"🟡 IP solo destinazione: {len(only_dst)}")
    print(f"🟣 IP sia sorgente che destinazione: {len(both)}")
    
    print("\n" + "-"*80)
    print("📋 LISTA IP SORGENTE:")
    print("-"*80)
    
    # Ordina e mostra gli IP sorgente
    for i, ip in enumerate(sorted(src_ips), 1):
        role = ""
        if ip in only_src:
            role = " [solo client]"
        elif ip in both:
            role = " [client & server]"
        
        print(f"{i:3}. {ip}{role}")
    
    # Se ci sono IP solo destinazione, mostrali
    if only_dst:
        print("\n" + "-"*80)
        print("📋 IP SOLO DESTINAZIONE (server):")
        print("-"*80)
        for i, ip in enumerate(sorted(only_dst), 1):
            print(f"{i:3}. {ip}")
    
    print("\n" + "="*80)


def group_ips_by_subnet(ips, subnet_mask=24):
    """
    Raggruppa IP per sottorete
    
    Args:
        ips: set di indirizzi IP (stringhe)
        subnet_mask: maschera di sottorete (default /24)
    
    Returns:
        dict: {network_address: [list of IPs in that subnet]}
    """
    subnets = defaultdict(list)
    
    for ip_str in ips:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            # Crea la rete con la maschera specificata
            network = ipaddress.ip_network(f"{ip_str}/{subnet_mask}", strict=False)
            subnets[str(network.network_address)].append(ip_str)
        except ValueError:
            # Ignora IP non validi
            continue
    
    return dict(subnets)


def find_inter_subnet_connections(ip_pairs, subnets_map):
    """
    Trova le connessioni tra sottoreti diverse
    
    Args:
        ip_pairs: dizionario delle coppie IP
        subnets_map: mappa IP -> sottorete
    
    Returns:
        set: coppie di sottoreti che comunicano
    """
    inter_subnet_links = set()
    
    for pair_key in ip_pairs.keys():
        src_ip, dst_ip = pair_key.split(' <-> ')
        src_subnet = subnets_map.get(src_ip)
        dst_subnet = subnets_map.get(dst_ip)
        
        if src_subnet and dst_subnet and src_subnet != dst_subnet:
            # Ordina per consistenza
            link = tuple(sorted([src_subnet, dst_subnet]))
            inter_subnet_links.add(link)
    
    return inter_subnet_links


def generate_network_topology(all_ips, ip_pairs, src_ips, dst_ips, output_file='network_topology.json'):
    """
    Genera un file JSON con la configurazione di rete per Mininet.
    
    Architettura:
    - Subnet separate per client raggruppati per rete (es. 172.16.0.0/16, 192.168.0.0/16)
    - Una subnet "Internet" per tutti i server di destinazione
    - Un router centrale che connette le subnet client con Internet
    
    Args:
        all_ips: set di tutti gli IP trovati
        ip_pairs: dizionario delle coppie IP
        src_ips: set di IP sorgente (client)
        dst_ips: set di IP destinazione (server)
        output_file: path del file JSON di output
    """
    # Raggruppa IP sorgente per sottorete (client)
    # Usa maschere variabili per raggruppare in modo intelligente
    client_subnets = {}
    for ip_str in src_ips:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            # Determina la maschera in base alla classe di rete
            if ip_str.startswith('10.'):
                # Rete privata classe A: /8
                network = ipaddress.ip_network(f"{ip_str}/8", strict=False)
            elif ip_str.startswith('172.16.') or ip_str.startswith('172.17.') or \
                 any(ip_str.startswith(f'172.{i}.') for i in range(16, 32)):
                # Rete privata classe B: /16
                network = ipaddress.ip_network(f"{ip_str}/16", strict=False)
            elif ip_str.startswith('192.168.'):
                # Rete privata classe C: /16 (per raggruppare tutte le 192.168.x.x)
                network = ipaddress.ip_network(f"{ip_str}/16", strict=False)
            else:
                # IP pubblici: raggruppali per /16
                network = ipaddress.ip_network(f"{ip_str}/16", strict=False)
            
            subnet_key = str(network.network_address) + f"/{network.prefixlen}"
            if subnet_key not in client_subnets:
                client_subnets[subnet_key] = []
            client_subnets[subnet_key].append(ip_str)
        except ValueError:
            continue
    
    # Prepara i flussi
    flows = []
    for pair_key, data in ip_pairs.items():
        src_ip, dst_ip = pair_key.split(' <-> ')
        flows.append({
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_ports": sorted(data['src_ports'], key=int),
            "dst_ports": sorted(data['dst_ports'], key=int),
            "flow_count": data['count']
        })
    
    # Costruisci la topologia
    topology = {
        "description": "Network topology for Mininet - Client subnets + Internet",
        "architecture": "client_subnets_with_central_router",
        "subnets": [],
        "routers": [],
        "probe": {
            "name": "probe",
            "ip": "10.255.255.254/24",
            "connection": "gateway_router",
            "interface": "probe-eth0",
            "capture_file": "/pcap/capture.pcap",
            "capture_filter": "",
            "purpose": "Packet capture for traffic analysis"
        },
        "flows": flows,
        "statistics": {
            "total_ips": len(all_ips),
            "client_subnets": len(client_subnets),
            "server_ips": len(dst_ips),
            "total_flows": len(flows)
        }
    }
    
    # Aggiungi subnet client
    for subnet_addr, ips in sorted(client_subnets.items()):
        topology["subnets"].append({
            "type": "client_subnet",
            "network": subnet_addr,
            "switch_name": f"s{subnet_addr.split('/')[0].replace('.', '_')}",
            "hosts": sorted(ips),
            "num_hosts": len(ips)
        })
    
    # Aggiungi subnet Internet (tutti gli IP destinazione)
    topology["subnets"].append({
        "type": "internet",
        "network": "0.0.0.0/0",
        "switch_name": "s_internet",
        "hosts": sorted(dst_ips),
        "num_hosts": len(dst_ips)
    })
    
    # Aggiungi router centrale
    client_networks = [s["network"] for s in topology["subnets"] if s["type"] == "client_subnet"]
    topology["routers"].append({
        "id": "gateway_router",
        "type": "central_gateway",
        "connects_clients": client_networks,
        "connects_internet": "0.0.0.0/0",
        "purpose": "Route traffic between client subnets and Internet"
    })
    
    # Salva JSON
    try:
        with open(output_file, 'w') as f:
            json.dump(topology, f, indent=2)
        print(f"\n✅ Topologia di rete salvata in: {output_file}")
        
        # Stampa sommario
        print(f"\n🌐 CONFIGURAZIONE DI RETE GENERATA:")
        print(f"   └─ Architettura: Client Subnets + Central Router + Internet")
        print(f"   └─ {len(client_subnets)} subnet client")
        print(f"   └─ 1 subnet Internet (con {len(dst_ips)} server)")
        print(f"   └─ {len(all_ips)} host totali")
        print(f"   └─ {len(flows)} flussi di traffico")
        print(f"   └─ {len(topology['routers'])} router (gateway centrale)")
        print(f"   └─ 1 nodo probe per packet capture")
        
        # Dettagli subnet client
        print(f"\n📊 SUBNET CLIENT:")
        for subnet_addr, ips in sorted(client_subnets.items()):
            print(f"   └─ {subnet_addr}: {len(ips)} host")
        
        # Dettagli probe
        print(f"\n🔍 PROBE CONFIGURATION:")
        print(f"   └─ Nome: {topology['probe']['name']}")
        print(f"   └─ IP: {topology['probe']['ip']}")
        print(f"   └─ File capture: {topology['probe']['capture_file']}")
        print(f"   └─ Connesso a: {topology['probe']['connection']}")
        
    except Exception as e:
        print(f"❌ Errore durante il salvataggio: {e}")


def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_flows.py <csv_file> [output_json]")
        print("\nEsempi:")
        print("  python analyze_flows.py /features/reconstructed.csv")
        print("  python analyze_flows.py features/flows.csv network_config.json")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else 'network_topology.json'
    
    # Se il path non esiste, prova a cercarlo nella cartella features
    if not Path(csv_file).exists():
        # Cerca in tutte le sottocartelle di features
        features_dir = Path('/features')
        if features_dir.exists():
            found_files = list(features_dir.rglob('*.csv'))
            if found_files:
                print(f"📂 File CSV trovati in /features:")
                for i, f in enumerate(found_files, 1):
                    print(f"  {i}. {f}")
                print()
        
        print(f"❌ File '{csv_file}' non trovato")
        sys.exit(1)
    
    print(f"📂 Analisi del file: {csv_file}")
    
    ip_pairs, total_flows, all_ips, src_ips, dst_ips = analyze_flows(csv_file)
    
    if total_flows == 0:
        print("\n⚠️  Nessun flusso trovato nel file CSV")
        sys.exit(0)
    
    print_results(ip_pairs, total_flows)
    
    # Stampa analisi IP sorgente
    print_source_ips_analysis(src_ips, dst_ips)
    
    # Genera la topologia di rete
    generate_network_topology(all_ips, ip_pairs, src_ips, dst_ips, output_json)


if __name__ == '__main__':
    main()
