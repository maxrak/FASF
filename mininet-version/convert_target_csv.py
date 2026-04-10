#!/usr/bin/env python3
"""
Converte target.csv sostituendo IP reali con IP della topologia,
mantenendo tutte le statistiche dei flussi (packet size, rate, duration, ecc.)
"""

import pandas as pd
import json
import sys
import random
from collections import defaultdict

def load_topology_ips(topology_file, max_subnets=None):
    """
    Estrae IP dalla topologia
    
    Args:
        topology_file: Path alla topologia JSON
        max_subnets: Numero massimo di sottoreti da cui prendere IP (None = tutte)
    """
    with open(topology_file) as f:
        topo = json.load(f)
    
    all_ips = []
    subnets_to_use = topo["subnets"][:max_subnets] if max_subnets else topo["subnets"]
    
    for subnet in subnets_to_use:
        all_ips.extend(subnet["hosts"])
    
    print(f"[+] Usando IP da {len(subnets_to_use)} sottoreti")
    
    return all_ips

def convert_csv(input_csv, output_csv, topology_file, max_flows=None, max_subnets=None):
    """
    Converte il CSV sostituendo IP reali con IP della topologia
    
    Args:
        input_csv: Path al CSV originale (es. target.csv)
        output_csv: Path al CSV convertito
        topology_file: Path alla topologia JSON
        max_flows: Numero massimo di flussi da convertire (None = tutti)
        max_subnets: Numero massimo di sottoreti da cui prendere IP (deve matchare replay_topology.py)
    """
    
    # Carica IP disponibili dalla topologia
    topology_ips = load_topology_ips(topology_file, max_subnets)
    print(f"[+] IP disponibili nella topologia: {len(topology_ips)}")
    print(f"    {topology_ips[:5]}...")
    
    # Carica CSV originale
    df = pd.read_csv(input_csv)
    print(f"[+] Flussi nel CSV originale: {len(df)}")
    
    # Limita numero di flussi se richiesto
    if max_flows and max_flows < len(df):
        df = df.sample(n=max_flows, random_state=42)
        print(f"[+] Selezionati {max_flows} flussi random")
    
    # Mappa IP originali → IP topologia
    ip_mapping = {}
    
    def get_mapped_ip(original_ip):
        """Mappa un IP originale ad un IP della topologia"""
        if original_ip not in ip_mapping:
            # Assegna un IP random dalla topologia
            ip_mapping[original_ip] = random.choice(topology_ips)
        return ip_mapping[original_ip]
    
    # Converti IP nelle colonne corrette
    if "Source IP" in df.columns and "Destination IP" in df.columns:
        df["Source IP"] = df["Source IP"].apply(get_mapped_ip)
        df["Destination IP"] = df["Destination IP"].apply(get_mapped_ip)
        print(f"[+] Convertiti Source IP e Destination IP")
    elif "Src IP" in df.columns and "Dst IP" in df.columns:
        df["Src IP"] = df["Src IP"].apply(get_mapped_ip)
        df["Dst IP"] = df["Dst IP"].apply(get_mapped_ip)
        print(f"[+] Convertiti Src IP e Dst IP")
    else:
        print("[!] ERRORE: Colonne IP non trovate nel CSV")
        print(f"    Colonne disponibili: {df.columns.tolist()[:10]}")
        return False
    
    # Statistiche sulla conversione
    print(f"\n[+] Mappatura IP:")
    for orig_ip, topo_ip in list(ip_mapping.items())[:10]:
        print(f"    {orig_ip} → {topo_ip}")
    if len(ip_mapping) > 10:
        print(f"    ... e altri {len(ip_mapping) - 10} IP")
    
    # Conta flussi per coppia IP
    flow_counts = defaultdict(int)
    for _, row in df.iterrows():
        if "Source IP" in df.columns:
            src, dst = row["Source IP"], row["Destination IP"]
        else:
            src, dst = row["Src IP"], row["Dst IP"]
        flow_counts[(src, dst)] += 1
    
    print(f"\n[+] Flussi per coppia IP (top 10):")
    for (src, dst), count in sorted(flow_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"    {src} → {dst}: {count} flussi")
    
    # Salva CSV convertito
    df.to_csv(output_csv, index=False)
    print(f"\n✅ CSV convertito salvato in: {output_csv}")
    print(f"   Flussi totali: {len(df)}")
    print(f"   Coppie IP uniche: {len(flow_counts)}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python convert_target_csv.py <input.csv> <output.csv> [topology.json] [max_flows] [max_subnets]")
        print()
        print("Esempio:")
        print("  python convert_target_csv.py features/target.csv features/target_converted.csv shared/network_topology.json 100 3")
        print()
        print("Parametri:")
        print("  input.csv     : CSV originale con IP reali")
        print("  output.csv    : CSV convertito con IP della topologia")
        print("  topology.json : File topologia (default: shared/network_topology.json)")
        print("  max_flows     : Massimo flussi da convertire (default: tutti)")
        print("  max_subnets   : Numero sottoreti da usare - DEVE matchare replay_topology.py! (default: tutte)")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_csv = sys.argv[2]
    topology_file = sys.argv[3] if len(sys.argv) > 3 else "shared/network_topology.json"
    max_flows = int(sys.argv[4]) if len(sys.argv) > 4 else None
    max_subnets = int(sys.argv[5]) if len(sys.argv) > 5 else None
    
    convert_csv(input_csv, output_csv, topology_file, max_flows, max_subnets)
