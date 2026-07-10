#!/usr/bin/env python3
"""
Replay network topology from JSON and simulate traffic flows
"""

import json
import sys
import os
import time
import ipaddress
import pandas as pd
from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.clean import cleanup
import subprocess
import re


def cleanup_mininet_state():
    """Pulisce stato residuo Mininet/OVS prima e dopo il replay.

    Utile quando una run precedente termina con eccezione e lascia veth come
    sw1-mon/sw1-m, bridge OVS o processi Mininet ancora vivi.
    """
    info("*** Cleanup stato Mininet/OVS precedente\n")

    # Cleanup ufficiale Mininet: bridge, controller, namespace e processi comuni.
    try:
        cleanup()
    except Exception as exc:
        info(f"*** Warning: cleanup() Mininet fallito: {exc}\n")

    # Cleanup aggiuntivo per interfacce con nomi custom generate da short_switch_intf().
    # Esempi: sw1-mon, sw1-m, sw2-gw, sw3-pr, sw4-h12.
    try:
        result = subprocess.run(
            ["ip", "-o", "link", "show"],
            check=False,
            text=True,
            capture_output=True,
        )
        for line in result.stdout.splitlines():
            match = re.match(r"\d+:\s+([^:@]+)", line)
            if not match:
                continue
            intf = match.group(1)
            if re.match(r"^sw\d+-(mon|m|gw|pr|h\d+)$", intf):
                subprocess.run(
                    ["ip", "link", "delete", intf],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except Exception as exc:
        info(f"*** Warning: cleanup interfacce custom fallito: {exc}\n")



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


def choose_router_ip(network_cidr, used_ips):
    """Sceglie un IP libero nella subnet da assegnare all'interfaccia del router."""
    network = ipaddress.ip_network(network_cidr, strict=False)
    used = {ipaddress.ip_address(ip) for ip in used_ips}

    if network.version != 4:
        raise ValueError(f"Subnet non IPv4 non supportata: {network_cidr}")

    if network.prefixlen >= 31:
        candidates = [network.network_address]
    else:
        max_offset = min(network.num_addresses - 1, 512)
        candidates = [network.network_address + offset for offset in range(1, max_offset)]

    for candidate in candidates:
        if candidate not in used and candidate not in (network.network_address, network.broadcast_address):
            return str(candidate)

    raise ValueError(f"Nessun IP libero per il router nella subnet {network_cidr}")


def short_switch_intf(subnet_index, suffix):
    """Genera nomi interfaccia sotto il limite Linux di 15 caratteri."""
    return f"sw{subnet_index}-{suffix}"[:15]


MAX_HOSTS_PER_OVS_SWITCH = 45


def chunks(items, size):
    """Divide una lista in blocchi di dimensione massima size."""
    for index in range(0, len(items), size):
        yield items[index:index + size]


def chunked_switch_name(base_name, chunk_index, total_chunks):
    """Crea nomi switch corti e stabili per subnet suddivise in più bridge."""
    if total_chunks == 1:
        return base_name

    suffix = f"_{chunk_index}"
    return f"{base_name[:15 - len(suffix)]}{suffix}"


def internet_transit_ip(chunk_index):
    """IP gateway di transito per chunk internet isolati su bridge diversi."""
    if chunk_index <= 255:
        return f"198.18.{chunk_index}.1"

    return f"198.19.{chunk_index - 255}.1"


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
    network_info = {
        'router': None,
        'router_name': 'central_gateway',
        'subnets': [],
        'host_info': {},
        'probe_switch_ports': [],
    }

    # Router centrale reale: collega gli switch di subnet e abilita routing L3.
    # Il nome Mininet resta corto per evitare nomi interfaccia oltre 15 caratteri.
    router = net.addHost('r0', ip=None)
    network_info['router'] = router
    info("*** Router centrale creato: r0 (central_gateway)\n")
    
    # Limita il numero di sottoreti per evitare topologie troppo complesse
    subnets_to_create = topology['subnets'][:max_subnets]
    info(f"*** Creazione di {len(subnets_to_create)} sottoreti (su {len(topology['subnets'])} totali)\n")
    
    # Verifica se esiste monitoring switch nella topologia
    has_monitoring_switch = 'monitoring_switch' in topology and topology['monitoring_switch'] is not None
    if has_monitoring_switch:
        info("*** Architettura: host -> switch subnet -> monitoring_switch -> r0 (per private) | s_internet -> r0 (per pubbliche)\n")
    else:
        info("*** Architettura: host -> switch subnet -> r0 central_gateway\n")
    
    # Info per creare monitoring switch successivamente
    monitoring_info = {
        'private_switches': [],  # Lista di switch privati da collegare al monitoring
        'internet_switches': [],  # Lista di switch internet da collegare al monitoring
        'router_intf_index': 0,
    }
    
    # Crea gli switch di subnet, collega il router (solo per subnet internet se c'è monitoring) e poi gli host.
    info("*** Creazione switch, router links e host\n")
    host_counter = 1
    router_intf_index = 0
    switch_counter = 1
    for subnet_index, subnet_info in enumerate(subnets_to_create, start=1):
        subnet = subnet_info['network']
        subnet_type = subnet_info.get('type', 'client_subnet')
        base_switch_name = subnet_info.get('switch_name', f's{subnet_index}')
        all_hosts = [str(ip) for ip in subnet_info.get('hosts', [])]
        is_internet = subnet_type == 'internet' or subnet == '0.0.0.0/0'

        if is_internet:
            host_groups = list(chunks(all_hosts, MAX_HOSTS_PER_OVS_SWITCH)) or [[]]
        else:
            host_groups = [all_hosts]

        if len(host_groups) > 1:
            info(
                f"  - Subnet {base_switch_name} divisa in {len(host_groups)} switch "
                f"({len(all_hosts)} host totali)\n"
            )

        for chunk_index, hosts in enumerate(host_groups, start=1):
            switch_slot = switch_counter
            switch_counter += 1
            switch_name = chunked_switch_name(base_switch_name, chunk_index, len(host_groups))
            switch = net.addSwitch(switch_name, dpid=f"{switch_slot:016x}")
            
            # Inizializza router_intf a None (verrà assegnato solo se non c'è monitoring switch)
            router_intf = None

            if is_internet:
                router_ip = internet_transit_ip(switch_slot)
                router_prefix = 24
                host_prefix = 32
            else:
                router_ip = choose_router_ip(subnet, hosts)
                router_prefix = int(subnet.split('/')[-1]) if '/' in subnet else 24
                host_prefix = router_prefix

            # Se c'è monitoring switch, TUTTI gli switch passano attraverso di esso
            # Salva le info per collegarle al monitoring switch dopo
            if has_monitoring_switch:
                # NON creare link router->switch, lo faremo tramite monitoring switch
                # Distingui private da internet per gestione IP successiva
                switch_info = {
                    'switch': switch,
                    'switch_name': switch_name,
                    'switch_slot': switch_slot,
                    'router_ip': router_ip,
                    'router_prefix': router_prefix,
                    'is_internet': is_internet,
                }
                
                if is_internet:
                    monitoring_info['internet_switches'].append(switch_info)
                    info(
                        f"  - Switch {switch_name}: {subnet} (internet, via monitoring), "
                        f"router={router_ip}/{router_prefix}, host={len(hosts)}\n"
                    )
                else:
                    monitoring_info['private_switches'].append(switch_info)
                    info(
                        f"  - Switch {switch_name}: {subnet} (private, via monitoring), "
                        f"router={router_ip}/{router_prefix}, host={len(hosts)}\n"
                    )
            else:
                # Senza monitoring: collega direttamente al router (architettura vecchia)
                router_intf = f"gw-eth{router_intf_index}"
                router_intf_index += 1
                switch_router_intf = short_switch_intf(switch_slot, 'gw')
                net.addLink(
                    router,
                    switch,
                    intfName1=router_intf,
                    intfName2=switch_router_intf,
                    params1={'ip': f'{router_ip}/{router_prefix}'}
                )
                info(
                    f"  - Switch {switch_name}: {subnet} ({subnet_type}), "
                    f"router {router_intf}={router_ip}/{router_prefix}, "
                    f"host={len(hosts)}\n"
                )
            
            # Crea subnet_state per network_info
            subnet_state = {
                'type': subnet_type,
                'network': subnet,
                'switch': switch,
                'switch_name': switch_name,
                'router_ip': router_ip,
                'router_prefix': router_prefix,
                'router_intf': router_intf if not has_monitoring_switch else None,  # Se c'è monitoring, tutti gli switch passano attraverso di esso
                'hosts': hosts,
            }
            network_info['subnets'].append(subnet_state)
            
            for ip in hosts:
                host_name = f"h{host_counter}"
                host = net.addHost(host_name, ip=f"{ip}/{host_prefix}")
                host_map[ip] = host
                network_info['host_info'][ip] = {
                    'host': host,
                    'subnet': subnet,
                    'subnet_type': subnet_type,
                    'switch': switch,
                    'switch_name': switch_name,
                    'gateway_ip': router_ip,
                    'prefix': host_prefix,
                }

                net.addLink(
                    host,
                    switch,
                    intfName1=f"{host_name}-eth0",
                    intfName2=short_switch_intf(switch_slot, f"h{host_counter}")
                )

                info(f"    - Host {host_name}: {ip}/{host_prefix} gw {router_ip} via {switch_name}\n")
                host_counter += 1
    
    # Salva router_intf_index per il monitoring switch
    monitoring_info['router_intf_index'] = router_intf_index
    
    # Crea monitoring switch se presente nella topologia
    monitoring_switch = None
    if has_monitoring_switch:
        info("\n*** Creazione Monitoring Switch\n")
        monitoring_config = topology['monitoring_switch']
        monitoring_switch_name = monitoring_config.get('name', 's_monitoring')
        monitoring_switch = net.addSwitch(monitoring_switch_name, dpid=f"{switch_counter:016x}")
        switch_counter += 1
        
        info(f"  - Monitoring switch: {monitoring_switch_name}\n")
        
        # Collega monitoring switch al router
        monitoring_router_intf = f"gw-eth{monitoring_info['router_intf_index']}"
        monitoring_info['router_intf_index'] += 1
        monitoring_router_ip = "10.255.255.1"  # IP dedicato per il link monitoring<->router
        monitoring_router_prefix = 24
        
        net.addLink(
            router,
            monitoring_switch,
            intfName1=monitoring_router_intf,
            intfName2="mon-gw",
            params1={'ip': f'{monitoring_router_ip}/{monitoring_router_prefix}'}
        )
        info(f"  - Monitoring -> Router: {monitoring_router_intf}={monitoring_router_ip}/{monitoring_router_prefix}\n")
        
        # Aggiungi IP secondari sull'interfaccia del router per ogni subnet (privata e internet)
        # Questo permette al router di essere il gateway per ogni subnet attraverso il monitoring switch
        all_switches = monitoring_info['private_switches'] + monitoring_info['internet_switches']
        info(f"  - Configurazione IP secondari sul router per {len(all_switches)} subnet:\n")
        for sw_info in all_switches:
            router_ip = sw_info['router_ip']
            router_prefix = sw_info['router_prefix']
            # Aggiungi IP secondario
            router.cmd(f'ip addr add {router_ip}/{router_prefix} dev {monitoring_router_intf}')
            subnet_label = "internet" if sw_info.get('is_internet') else "private"
            info(f"      {router_ip}/{router_prefix} ({subnet_label})\n")
        
        # Salva l'interfaccia monitoring per reference
        network_info['monitoring_router_intf'] = monitoring_router_intf
        
        # Collega tutti gli switch (privati e internet) al monitoring switch
        info(f"  - Collegamento {len(all_switches)} switch al monitoring:\n")
        for idx, sw_info in enumerate(all_switches, start=1):
            switch = sw_info['switch']
            switch_name = sw_info['switch_name']
            switch_slot = sw_info['switch_slot']
            subnet_label = "internet" if sw_info.get('is_internet') else "private"
            
            # Link switch <-> monitoring_switch
            # Usa switch_slot per garantire nomi unici
            switch_intf = short_switch_intf(switch_slot, 'mon')
            mon_intf = short_switch_intf(switch_slot, 'm')
            
            net.addLink(
                switch,
                monitoring_switch,
                intfName1=switch_intf,
                intfName2=mon_intf
            )
            info(f"      {switch_name} <-> {monitoring_switch_name} ({subnet_label})\n")
        
        # Aggiungi monitoring switch alla switch_map
        network_info['monitoring_switch'] = monitoring_switch
        network_info['monitoring_switch_name'] = monitoring_switch_name
    
    # Crea mappa switch_name -> switch object per facilitare lookup
    switch_map = {}
    for subnet_state in network_info['subnets']:
        switch_map[subnet_state['switch_name']] = subnet_state['switch']
    # Aggiungi monitoring switch alla mappa se esiste
    if monitoring_switch:
        switch_map[monitoring_switch_name] = monitoring_switch
    network_info['switch_map'] = switch_map
    
    # Crea il nodo probe se presente nella topologia
    probe = None
    if 'probe' in topology:
        probe_config = topology['probe']
        probe_name = probe_config.get('name', 'probe')
        mirror_switches = probe_config.get('mirror_switches', [])
        
        info("*** Creazione nodo probe per packet capture\n")
        # Probe senza IP - sarà puramente passivo
        probe = net.addHost(probe_name, ip=None)
        
        # Connetti il probe solo agli switch specificati in mirror_switches
        probe_links = []
        for idx, switch_name in enumerate(mirror_switches):
            switch = switch_map.get(switch_name)
            if not switch:
                info(f"  ! Warning: Switch '{switch_name}' non trovato, skip\n")
                continue
            
            probe_intf = f"{probe_name}-eth{idx}"
            switch_probe_intf = short_switch_intf(idx + 1, 'pr')
            net.addLink(
                probe,
                switch,
                intfName1=probe_intf,
                intfName2=switch_probe_intf
            )
            probe_links.append({
                'switch': switch,
                'switch_name': switch.name,
                'port_name': switch_probe_intf,
                'probe_intf': probe_intf,
            })
        
        network_info['probe_switch_ports'] = probe_links
        info(f"  - Probe {probe_name}: passivo (connesso a {len(probe_links)} switch mirror)\n")
    
    return net, host_map, probe, network_info


def disable_ipv6(net, host_map, probe=None, router=None):
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
    
    # Disabilita IPv6 anche sul probe e assicura che sia passivo
    if probe:
        probe.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
        probe.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1 > /dev/null 2>&1')
        probe.cmd('sysctl -w net.ipv6.conf.lo.disable_ipv6=1 > /dev/null 2>&1')
        
        # Disabilita IPv6 su tutte le interfacce del probe
        for intf in probe.intfList():
            if intf.name != 'lo':
                probe.cmd(f'sysctl -w net.ipv6.conf.{intf.name}.disable_ipv6=1 > /dev/null 2>&1')
        
        # Disabilita forwarding su probe per mantenerlo completamente passivo
        probe.cmd('sysctl -w net.ipv4.ip_forward=0 > /dev/null 2>&1')
        probe.cmd('sysctl -w net.ipv6.conf.all.forwarding=0 > /dev/null 2>&1')
        
        info("  - IPv6 disabilitato e forwarding disabilitato sul probe (passivo)\n")

    # Disabilita IPv6 anche sul router centrale
    if router:
        router.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
        router.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1 > /dev/null 2>&1')
        router.cmd('sysctl -w net.ipv6.conf.lo.disable_ipv6=1 > /dev/null 2>&1')

        for intf in router.intfList():
            if intf.name != 'lo':
                router.cmd(f'sysctl -w net.ipv6.conf.{intf.name}.disable_ipv6=1 > /dev/null 2>&1')

        info("  - IPv6 disabilitato anche sul router centrale\n")
    
    # Disabilita IPv6 sugli switch
    for switch in net.switches:
        switch.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1')
        switch.cmd('sysctl -w net.ipv6.conf.default.disable_ipv6=1 > /dev/null 2>&1')
    
    info("  - IPv6 disabilitato su tutti i nodi\n")
    
    # Attendi che le modifiche abbiano effetto
    time.sleep(1)


def configure_interface_addresses(network_info):
    """Riassegna gli indirizzi IPv4 con iproute2 per rispettare prefissi /32 e /16."""
    router = network_info['router']
    info("*** Normalizzazione indirizzi IPv4 su host e central_gateway\n")

    for subnet_state in network_info['subnets']:
        router_intf = subnet_state['router_intf']
        router_ip = subnet_state['router_ip']
        router_prefix = subnet_state['router_prefix']

        router.cmd(f'ip addr flush dev {router_intf}')
        router.cmd(f'ip addr add {router_ip}/{router_prefix} dev {router_intf}')
        router.cmd(f'ip link set dev {router_intf} up')

    for ip, host_info in network_info['host_info'].items():
        host = host_info['host']
        iface = f"{host.name}-eth0"
        prefix = host_info['prefix']

        host.cmd(f'ip addr flush dev {iface}')
        host.cmd(f'ip addr add {ip}/{prefix} dev {iface}')
        host.cmd(f'ip link set dev {iface} up')

    info("  - Prefissi IPv4 applicati esplicitamente\n")


def configure_l3_routing(network_info):
    """Configura forwarding, default gateway host e rotte del router centrale."""
    router = network_info['router']
    info("*** Configurazione routing L3 su central_gateway (r0)\n")

    router.cmd('sysctl -w net.ipv4.ip_forward=1 > /dev/null')
    router.cmd('iptables -P FORWARD ACCEPT 2>/dev/null || true')

    client_networks = []
    internet_subnets = []
    internet_host_ips = []
    
    # Verifica se c'è monitoring switch
    has_monitoring = 'monitoring_switch' in network_info and network_info['monitoring_switch'] is not None
    monitoring_router_ip = "10.255.255.1"  # IP del router sull'interfaccia monitoring

    for subnet_state in network_info['subnets']:
        subnet = subnet_state['network']
        subnet_type = subnet_state['type']
        router_ip = subnet_state['router_ip']
        router_intf = subnet_state['router_intf']

        if subnet_type == 'internet' or subnet == '0.0.0.0/0':
            internet_subnets.append(subnet_state)
            internet_host_ips.extend(subnet_state['hosts'])
            # Route specifiche per ogni host internet
            if router_intf:  # Solo se collegato direttamente (senza monitoring)
                for host_ip in subnet_state['hosts']:
                    router.cmd(f'ip route replace {host_ip}/32 dev {router_intf}')
                info(
                    f"  - Route router verso {len(subnet_state['hosts'])} host internet "
                    f"via {router_intf} ({subnet_state['switch_name']})\n"
                )
            elif has_monitoring:
                # Internet switch collegato via monitoring: le route verranno aggiunte dopo
                pass
        else:
            # Subnet privata (client_subnet o private_subnet)
            client_networks.append(subnet)
            if has_monitoring and router_intf is None:
                # Subnet privata collegata via monitoring switch
                # La route verrà aggiunta in blocco per tutte le private
                pass
            elif router_intf:
                # Collegamento diretto al router (architettura vecchia)
                router.cmd(f'ip route replace {subnet} dev {router_intf} src {router_ip}')
                info(
                    f"  - Route router verso {subnet} via {router_intf} "
                    f"({subnet_state['switch_name']})\n"
                )
    
    # Se c'è monitoring switch, aggiungi route per tutte le reti private
    if has_monitoring:
        monitoring_intf = network_info.get('monitoring_router_intf')
        if monitoring_intf:
            info(f"  - Monitoring switch interface sul router: {monitoring_intf}\n")
            
            # Aggiungi route esplicite per TUTTE le reti (private e internet) via monitoring switch
            # (anche se con gli IP secondari potrebbero già essere configurate)
            route_count = 0
            internet_host_count = 0
            for subnet_state in network_info['subnets']:
                if subnet_state['router_intf'] is None:  # Tutte le subnet via monitoring
                    subnet = subnet_state['network']
                    router_ip = subnet_state['router_ip']
                    subnet_type = subnet_state['type']
                    
                    if subnet_type == 'internet':
                        # Per subnet internet, aggiungi route /32 per ogni host
                        for host_ip in subnet_state['hosts']:
                            router.cmd(f'ip route replace {host_ip}/32 dev {monitoring_intf} src {router_ip}')
                            internet_host_count += 1
                    else:
                        # Per subnet private, aggiungi route per l'intera rete
                        router.cmd(f'ip route replace {subnet} dev {monitoring_intf} src {router_ip}')
                        route_count += 1
            
            info(f"  - Route router verso {route_count} reti private via monitoring switch ({monitoring_intf})\n")
            if internet_host_count > 0:
                info(f"  - Route router verso {internet_host_count} host internet via monitoring switch ({monitoring_intf})\n")

    overlap_host_routes = 0
    for ip, host_info in network_info['host_info'].items():
        host = host_info['host']
        iface = f"{host.name}-eth0"
        gateway_ip = host_info['gateway_ip']

        # onlink rende valido anche il caso internet: host con IP pubblico /32
        # che usa il router su una subnet di transito.
        host.cmd(f'ip route replace default via {gateway_ip} dev {iface} onlink')

        if host_info['subnet_type'] == 'internet':
            for client_network in client_networks:
                host.cmd(f'ip route replace {client_network} via {gateway_ip} dev {iface} onlink')
        else:
            local_network = ipaddress.ip_network(host_info['subnet'], strict=False)
            for internet_ip in internet_host_ips:
                if internet_ip == ip:
                    continue

                if ipaddress.ip_address(internet_ip) in local_network:
                    host.cmd(f'ip route replace {internet_ip}/32 via {gateway_ip} dev {iface} onlink')
                    overlap_host_routes += 1

    if overlap_host_routes:
        info(
            f"  - Route host-specific client -> internet per overlap di prefisso: "
            f"{overlap_host_routes}\n"
        )

    info("*** Tabella routing central_gateway (r0)\n")
    for line in router.cmd('ip -4 route show').strip().splitlines():
        info(f"    {line}\n")

    info("*** Verifica route da central_gateway verso switch/subnet connessi\n")
    for subnet_state in network_info['subnets']:
        hosts = subnet_state['hosts']
        if not hosts:
            continue
        probe_ip = hosts[0]
        route = router.cmd(f'ip route get {probe_ip}').strip().splitlines()
        first_line = route[0] if route else 'N/D'
        info(f"  - {subnet_state['switch_name']} ({subnet_state['network']}): {first_line}\n")


def configure_switches_standalone(net):
    """Configura tutti gli OVS switch come learning switch."""
    info("*** Configurazione switch in modalità standalone\n")
    for switch in net.switches:
        switch.cmd(f'ovs-ofctl add-flow {switch.name} action=normal')


def configure_probe_monitoring(topology, probe, network_info):
    """
    Configura probe monitoring con OVS mirroring e tcpdump.
    
    For each switch listed in `probe.mirror_switches`:
    - Add a link between the switch and the probe (already done in create_network_from_topology)
    - Configure an Open vSwitch mirror that replicates all switch traffic to the probe interface
    - Start tcpdump on the probe using the configured interface, output file and optional BPF filter
    
    The probe is passive and must not forward or generate application traffic.
    
    Args:
        topology: topologia JSON con configurazione probe
        probe: nodo probe Mininet
        network_info: informazioni di rete con probe_switch_ports
    
    Returns:
        tcpdump_proc: processo tcpdump avviato (per cleanup successivo)
    """
    probe_ports = network_info.get('probe_switch_ports', [])
    if not probe_ports or not probe:
        return None

    probe_config = topology.get('probe', {})
    
    # Configura OVS mirroring per ogni switch
    info("*** Configurazione port mirroring per probe\n")
    for mirror_idx, probe_link in enumerate(probe_ports, start=1):
        switch = probe_link['switch']
        port_name = probe_link['port_name']
        mirror_name = f"probe_mirror_{mirror_idx}"
        
        # Ottieni tutte le porte dello switch (escludendo la porta probe)
        all_ports_raw = switch.cmd(f'ovs-vsctl list-ports {switch.name}').strip().split('\n')
        # Pulisci i nomi delle porte da whitespace/carriage return
        all_ports = [p.strip() for p in all_ports_raw if p.strip()]
        
        # Filtra le porte per escludere:
        # 1. La porta probe
        # 2. La porta "mon-gw" (porta verso il gateway sul monitoring switch)
        # 3. Le porte verso s_internet (pattern specifici per s_internet)
        # Manteniamo tutte le altre porte (verso host locali e verso altri switch di subnet)
        monitored_ports = []
        excluded_ports = []
        
        for p in all_ports:
            # Escludi porta probe
            if p == port_name:
                excluded_ports.append((p, "porta probe"))
                continue
            
            # Escludi porta mon-gw (collegamento al gateway)
            if p == 'mon-gw':
                excluded_ports.append((p, "collegamento gateway"))
                continue
            
            # Escludi porte verso s_internet (iniziano con pattern specifico per s_internet)
            # Assumiamo che s_internet abbia porte con naming specifico da identificare
            # Per sicurezza, escludiamo solo se il nome contiene "inet" o simili pattern
            if 'inet' in p.lower():
                excluded_ports.append((p, "collegamento s_internet"))
                continue
            
            # Questa è una porta da monitorare
            monitored_ports.append(p)
        
        info(f"  DEBUG: Porte trovate su {switch.name}: {all_ports}\n")
        info(f"  DEBUG: Porta probe: {port_name}\n")
        info(f"  DEBUG: Porte escluse: {[f'{p[0]} ({p[1]})' for p in excluded_ports]}\n")
        info(f"  DEBUG: Porte da monitorare: {monitored_ports}\n")
        
        # Configura OVS mirror: monitora sia src che dst per traffico bidirezionale
        # Questo cattura sia il traffico in uscita che in ingresso, ma ogni pacchetto è catturato una sola volta
        if not monitored_ports:
            info(f"  - ATTENZIONE: Nessuna porta da monitorare su {switch.name}, mirror non configurato\n")
            continue
        
        port_get_cmds = []
        port_refs = []
        for idx, port in enumerate(monitored_ports):
            # Ogni comando get deve essere preceduto da --
            port_get_cmds.append(f'-- --id=@port{idx} get Port {port}')
            port_refs.append(f'@port{idx}')
        
        # Formato corretto per OVS: [uuid1,uuid2,...] tra parentesi quadre
        port_refs_str = '[' + ','.join(port_refs) + ']'
        port_get_str = ' '.join(port_get_cmds)
        
        # Configura OVS mirror: monitora SOLO le porte specificate (select-src-port)
        ovs_cmd = (
            f'ovs-vsctl -- --id=@probeport get Port {port_name} '
            f'{port_get_str} '
            f'-- --id=@m create Mirror name={mirror_name} '
            f'select-src-port={port_refs_str} output-port=@probeport '
            f'-- set Bridge {switch.name} mirrors=@m'
        )
        
        info(f"  DEBUG: Comando OVS: {ovs_cmd}\n")
        result = switch.cmd(ovs_cmd)
        info(f"  DEBUG: Risultato OVS: {result}\n")
        info(
            f"  - Mirror {switch.name}:{port_name} -> "
            f"{probe_link['probe_intf']} (select-src+dst-port, {len(monitored_ports)} porte monitorate)\n"
        )
        
        # Debug: verifica configurazione mirror
        mirror_status = switch.cmd(f'ovs-vsctl list Mirror {mirror_name}')
        info(f"    DEBUG Mirror config:\n")
        for line in mirror_status.strip().split('\n')[:5]:  # prime 5 righe
            info(f"      {line}\n")
        
        # Debug: verifica porte switch
        ports_status = switch.cmd(f'ovs-vsctl list-ports {switch.name}')
        info(f"    DEBUG Ports on {switch.name}: {ports_status.strip()}\n")
    
    # Avvia tcpdump sul probe
    capture_file = probe_config.get('capture_file', 'pcap/capture.pcap')
    capture_filter = probe_config.get('capture_filter', '')
    deduplication = probe_config.get('deduplication', True)
    
    info(f"*** Avvio packet capture sul probe\n")
    info(f"  - File: {capture_file}\n")
    
    # Usa solo la prima interfaccia probe invece di 'any' per evitare di catturare traffico Docker
    interface = probe_ports[0]['probe_intf']
    if len(probe_ports) > 1:
        info(f"  - NOTA: {len(probe_ports)} probe ports presenti, cattura solo su {interface}\n")
    info(f"  - Interface: {interface}\n")
    
    # Costruisci comando tcpdump
    tcpdump_args = ["tcpdump", "-i", interface, "-w", capture_file]
    
    # Aggiungi filtro BPF se specificato
    if capture_filter:
        # Forza IPv4 e combina con filtro custom
        tcpdump_args.append(f"ip and ({capture_filter})")
        info(f"  - Filtro: ip and ({capture_filter})\n")
    else:
        # Solo IPv4 (esclude IPv6, ARP, etc.)
        tcpdump_args.append("ip")
        info(f"  - Filtro: Solo IPv4 ('ip')\n")
    
    if deduplication and len(probe_ports) == 1:
        info(f"  - Deduplication: abilitata (cattura su singola interfaccia)\n")
    
    # Avvia tcpdump come processo background sul probe
    tcpdump_proc = probe.popen(tcpdump_args)
    time.sleep(1)  # Attendi avvio tcpdump
    info("  - Packet capture avviata sul probe passivo\n")
    
    return tcpdump_proc


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
    Mantiene la direzione dei flussi: A->B e B->A sono flussi distinti.
    
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
        
        # Crea mappa IP -> subnet network per verificare che gli IP siano nella topologia
        ip_to_subnet = {}
        for subnet_info in topology['subnets']:
            subnet_network = subnet_info['network']  # es: "10.0.0.0/8"
            for ip in subnet_info['hosts']:
                ip_to_subnet[ip] = subnet_network
        
        # Trova tutti i flussi che hanno ENTRAMBI gli IP nella topologia creata
        valid_flows = []
        seen_pairs = set()  # Evita duplicati solo se direzione identica
        
        for _, row in df.iterrows():
            src_ip = str(row[src_col])
            dst_ip = str(row[dst_col])
            
            # Verifica che entrambi gli IP esistano come host
            if src_ip in host_map and dst_ip in host_map:
                # Verifica che entrambi gli IP siano presenti nella topologia.
                src_subnet = ip_to_subnet.get(src_ip)
                dst_subnet = ip_to_subnet.get(dst_ip)
                
                if not src_subnet or not dst_subnet:
                    continue  # Salta flussi cross-subnet o IP senza subnet mappata
                
                # Salta broadcast addresses (.255)
                if dst_ip.endswith('.255'):
                    continue
                
                # Evita duplicati identici, ma conserva A->B e B->A come distinti
                pair = (src_ip, dst_ip)
                if pair not in seen_pairs:
                    valid_flows.append({
                        'src_ip': src_ip,
                        'dst_ip': dst_ip
                    })
                    seen_pairs.add(pair)
        
        info(f"  - Flussi direzionali generati dal CSV: {len(valid_flows)} (no broadcast)\n")
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
        
        # Costruisce il path del file di configurazione per questa coppia src->dst
        # Formato: {base_name}_{src_ip}_{dst_ip}.config
        src_ip_safe = src_ip.replace('.', '_').replace(':', '_')
        dst_ip_safe = dst_ip.replace('.', '_').replace(':', '_')
        config_file = f"{config_dir}/{base_name}_{src_ip_safe}_{dst_ip_safe}.config"
        
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
    cleanup_mininet_state()
    net = None
    tcpdump_proc = None

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
    
    try:
        # Crea rete
        net, host_map, probe, network_info = create_network_from_topology(topology, max_subnets)
    
        # Avvia rete
        info("*** Avvio rete\n")
        net.start()

        # Mininet può interpretare male alcuni prefissi /32: applicali esplicitamente.
        configure_interface_addresses(network_info)
    
        # Disabilita IPv6 per forzare IPv4
        disable_ipv6(net, host_map, probe, router=network_info.get('router'))
    
        # Attendi che IPv6 sia completamente disabilitato
        info("*** Attesa disabilitazione completa IPv6...\n")
        time.sleep(2)
    
        # Configura switch, routing e probe monitoring secondo la topologia JSON
        configure_switches_standalone(net)
        configure_l3_routing(network_info)
       
        # Avvia server
        start_servers(net, host_map, implementation)
    
        # Con molti host, serve più tempo perché server + switch siano pronti
        info("*** Attesa inizializzazione server e popolamento MAC table...\n")
        time.sleep(5)  # Tempo aggiuntivo per server
    
        # Usa pingall per popolare completamente ARP/MAC tables
        # Con molti host questo può richiedere tempo, limita il numero
        info("*** Popolamento tabelle ARP/MAC con ping di connettività\n")
        # Pingall completo solo per topologie piccole (<50 host)
        if len(host_map) < 15:
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

        #Sleep per far terminare tutti i ping
        info("*** Attesa per completamento ping...\n")
        time.sleep(10)

        info("*** Attivo il probe...\n")
        # Configura probe monitoring: OVS mirroring + tcpdump
        # La funzione restituisce il processo tcpdump per cleanup successivo
        tcpdump_proc = configure_probe_monitoring(topology, probe, network_info)
    
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

    finally:
        if tcpdump_proc:
            try:
                info("*** Arresto packet capture\n")
                tcpdump_proc.terminate()
                tcpdump_proc.wait(timeout=5)
            except Exception:
                try:
                    tcpdump_proc.kill()
                except Exception:
                    pass

        if net is not None:
            try:
                info("*** Arresto rete\n")
                net.stop()
            except Exception as exc:
                info(f"*** Warning: net.stop() fallito: {exc}\n")

        cleanup_mininet_state()


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
