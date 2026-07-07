#!/usr/bin/env python3
"""
Genera una vista grafica delle topologie prodotte da analyze_flows.py.

Output:
  - SVG statico renderizzato con Graphviz, utile per documentazione e paper.
  - HTML interattivo con PyVis, utile per esplorare nodi, link e flussi.
"""

import argparse
import html
import json
import math
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path


HOST_COLORS = {
    "client": {"fill": "#d8f3dc", "border": "#2d6a4f"},
    "server": {"fill": "#ffe8d6", "border": "#d9480f"},
    "client_server": {"fill": "#ede7f6", "border": "#6a4c93"},
    "unknown": {"fill": "#f3f4f6", "border": "#6b7280"},
}

SWITCH_COLORS = {
    "client_subnet": {"fill": "#457b9d", "border": "#1d4e89"},
    "internet": {"fill": "#f4a261", "border": "#bc6c25"},
    "default": {"fill": "#64748b", "border": "#334155"},
}

ROUTER_COLOR = {"fill": "#264653", "border": "#132a33"}
PROBE_COLOR = {"fill": "#fff3b0", "border": "#b08900"}
FLOW_COLOR = "#e76f51"
TOPOLOGY_EDGE_COLOR = "#6b7280"
DEFAULT_SVG_FLOW_THRESHOLD = 120


class GraphvizRenderError(RuntimeError):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera SVG Graphviz e HTML PyVis da un JSON di topologia."
    )
    parser.add_argument(
        "topology_json",
        help="File JSON generato da analyze_flows.py, es. topologies/test1.json",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help=(
            "Cartella di output. Default: la cartella del JSON se si chiama "
            "'topologies', altrimenti ./topologies."
        ),
    )
    parser.add_argument(
        "--name",
        help="Nome base dei file generati. Default: nome del JSON senza estensione.",
    )
    parser.add_argument(
        "--height",
        default="900px",
        help="Altezza del canvas HTML PyVis. Default: 900px.",
    )
    parser.add_argument(
        "--skip-svg",
        action="store_true",
        help="Non generare il file SVG Graphviz.",
    )
    parser.add_argument(
        "--skip-html",
        action="store_true",
        help="Non generare il file HTML PyVis.",
    )
    parser.add_argument(
        "--write-dot",
        action="store_true",
        help="Salva anche il sorgente DOT usato da Graphviz.",
    )
    parser.add_argument(
        "--svg-flow-mode",
        choices=["auto", "full", "aggregate", "none"],
        default="auto",
        help=(
            "Come disegnare i flussi nello SVG: full=host-host, "
            "aggregate=subnet/switch, none=solo topologia, auto=full sotto soglia "
            "e aggregate sopra soglia. Default: auto."
        ),
    )
    parser.add_argument(
        "--svg-flow-threshold",
        type=int,
        default=DEFAULT_SVG_FLOW_THRESHOLD,
        help=(
            "Numero massimo di archi host-host per usare full in modalità auto. "
            f"Default: {DEFAULT_SVG_FLOW_THRESHOLD}."
        ),
    )
    return parser.parse_args()


def load_topology(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            topology = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"Errore: file non trovato: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Errore: JSON non valido in {path}: {exc}")

    if not isinstance(topology, dict):
        raise SystemExit("Errore: il file di topologia deve contenere un oggetto JSON.")
    if "subnets" not in topology:
        raise SystemExit("Errore: campo 'subnets' mancante nel JSON di topologia.")

    return topology


def infer_output_dir(input_path, requested_output_dir):
    if requested_output_dir:
        return Path(requested_output_dir)

    if input_path.parent.name == "topologies":
        return input_path.parent

    return Path("topologies")


def sorted_port_values(ports):
    return sorted(
        {str(port) for port in ports},
        key=lambda p: (not p.isdigit(), int(p) if p.isdigit() else p),
    )


def compact_ports(ports, limit=8):
    ports = sorted_port_values(ports)
    if not ports:
        return "-"
    if len(ports) <= limit:
        return ", ".join(ports)
    visible = ", ".join(ports[:limit])
    return f"{visible}, ... (+{len(ports) - limit})"


def normalize_flows(raw_flows):
    aggregated = {}

    for flow in raw_flows or []:
        src_ip = str(flow.get("src_ip", "")).strip()
        dst_ip = str(flow.get("dst_ip", "")).strip()
        if not src_ip or not dst_ip:
            continue

        key = (src_ip, dst_ip)
        if key not in aggregated:
            aggregated[key] = {
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_ports": set(),
                "dst_ports": set(),
                "flow_count": 0,
            }

        data = aggregated[key]
        data["src_ports"].update(str(port) for port in flow.get("src_ports", []))
        data["dst_ports"].update(str(port) for port in flow.get("dst_ports", []))
        data["flow_count"] += int(flow.get("flow_count", 1) or 1)

    normalized = []
    for data in aggregated.values():
        normalized.append(
            {
                "src_ip": data["src_ip"],
                "dst_ip": data["dst_ip"],
                "src_ports": sorted_port_values(data["src_ports"]),
                "dst_ports": sorted_port_values(data["dst_ports"]),
                "flow_count": data["flow_count"],
            }
        )

    return sorted(normalized, key=lambda f: (f["src_ip"], f["dst_ip"]))


def build_model(topology):
    subnets = topology.get("subnets", [])
    routers = topology.get("routers", [])
    monitoring_switch = topology.get("monitoring_switch")
    probe = topology.get("probe") or {}
    flows = normalize_flows(topology.get("flows", []))

    host_to_subnet = {}
    host_to_subnet_type = {}
    host_to_switch = {}
    known_hosts = set()

    for subnet in subnets:
        network = str(subnet.get("network", "unknown"))
        subnet_type = str(subnet.get("type", "default"))
        switch_name = str(subnet.get("switch_name", network))
        for host in subnet.get("hosts", []):
            host = str(host)
            known_hosts.add(host)
            host_to_subnet[host] = network
            host_to_subnet_type[host] = subnet_type
            host_to_switch[host] = switch_name

    sources = {flow["src_ip"] for flow in flows}
    destinations = {flow["dst_ip"] for flow in flows}
    flow_hosts = sources | destinations
    unknown_hosts = flow_hosts - known_hosts

    outgoing = Counter()
    incoming = Counter()
    for flow in flows:
        count = int(flow.get("flow_count", 1) or 1)
        outgoing[flow["src_ip"]] += count
        incoming[flow["dst_ip"]] += count

    return {
        "subnets": subnets,
        "routers": routers,
        "monitoring_switch": monitoring_switch,
        "probe": probe,
        "flows": flows,
        "known_hosts": known_hosts,
        "unknown_hosts": unknown_hosts,
        "host_to_subnet": host_to_subnet,
        "host_to_subnet_type": host_to_subnet_type,
        "host_to_switch": host_to_switch,
        "sources": sources,
        "destinations": destinations,
        "outgoing": outgoing,
        "incoming": incoming,
        "statistics": topology.get("statistics", {}),
    }


def host_role(ip, model):
    is_source = ip in model["sources"]
    is_destination = ip in model["destinations"]

    if is_source and is_destination:
        return "client_server"
    if is_source:
        return "client"
    if is_destination:
        return "server"
    return "unknown"


def node_id(kind, value):
    return f"{kind}:{value}"


def dot_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def dot_node_id(kind, value):
    return dot_quote(node_id(kind, value))


def dot_attrs(**attrs):
    rendered = []
    for key, value in attrs.items():
        if value is None:
            continue
        rendered.append(f"{key}={dot_quote(value)}")
    return ", ".join(rendered)


def safe_cluster_name(value):
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(value))
    return f"cluster_{safe}"


def host_tooltip(ip, model):
    subnet = model["host_to_subnet"].get(ip, "non mappata")
    role = host_role(ip, model).replace("_", " + ")
    return (
        f"Host: {ip}\n"
        f"Subnet: {subnet}\n"
        f"Ruolo: {role}\n"
        f"Flussi uscenti: {model['outgoing'][ip]}\n"
        f"Flussi entranti: {model['incoming'][ip]}"
    )


def flow_tooltip(flow):
    return (
        f"{flow['src_ip']} -> {flow['dst_ip']}\n"
        f"Flussi: {flow['flow_count']}\n"
        f"Porte src: {compact_ports(flow.get('src_ports', []), limit=12)}\n"
        f"Porte dst: {compact_ports(flow.get('dst_ports', []), limit=12)}"
    )


def html_title(lines):
    return "<br>".join(html.escape(str(line)) for line in lines)


def flow_width(flow_count):
    return 1.0 + min(5.0, math.log10(max(1, int(flow_count))) * 1.8)


def resolve_svg_flow_mode(model, requested_mode, threshold):
    if requested_mode != "auto":
        return requested_mode
    if len(model["flows"]) > threshold:
        return "aggregate"
    return "full"


def flow_mode_label(flow_mode):
    return {
        "full": "flussi host-host",
        "aggregate": "flussi aggregati per subnet",
        "none": "solo topologia",
    }.get(flow_mode, flow_mode)


def aggregate_flows_for_svg(model):
    aggregated = {}

    for flow in model["flows"]:
        src_ip = flow["src_ip"]
        dst_ip = flow["dst_ip"]
        src_switch = model["host_to_switch"].get(src_ip)
        dst_switch = model["host_to_switch"].get(dst_ip)

        src_node = node_id("switch", src_switch) if src_switch else node_id("host", src_ip)
        dst_node = node_id("switch", dst_switch) if dst_switch else node_id("host", dst_ip)
        key = (src_node, dst_node)

        if key not in aggregated:
            aggregated[key] = {
                "src_node": src_node,
                "dst_node": dst_node,
                "flow_count": 0,
                "pairs": set(),
                "src_ports": set(),
                "dst_ports": set(),
            }

        data = aggregated[key]
        data["flow_count"] += int(flow.get("flow_count", 1) or 1)
        data["pairs"].add((src_ip, dst_ip))
        data["src_ports"].update(flow.get("src_ports", []))
        data["dst_ports"].update(flow.get("dst_ports", []))

    return sorted(
        aggregated.values(),
        key=lambda item: (-item["flow_count"], item["src_node"], item["dst_node"]),
    )


def aggregated_flow_tooltip(flow):
    sample_pairs = sorted(flow["pairs"])[:8]
    sample = "\n".join(f"- {src} -> {dst}" for src, dst in sample_pairs)
    remaining = len(flow["pairs"]) - len(sample_pairs)
    if remaining > 0:
        sample += f"\n- ... (+{remaining})"

    return (
        f"Flussi aggregati: {flow['flow_count']}\n"
        f"Coppie IP: {len(flow['pairs'])}\n"
        f"Porte src: {compact_ports(flow.get('src_ports', []), limit=12)}\n"
        f"Porte dst: {compact_ports(flow.get('dst_ports', []), limit=12)}\n"
        f"{sample}"
    )


def build_dot(model, graph_name, flow_mode="full"):
    stats = model["statistics"]
    label_parts = [graph_name]
    if stats:
        label_parts.append(
            " | ".join(
                [
                    f"IP: {stats.get('total_ips', '-')}",
                    f"Subnet client: {stats.get('client_subnets', '-')}",
                    f"Flussi: {stats.get('total_flows', len(model['flows']))}",
                ]
            )
        )
    if flow_mode != "full":
        label_parts.append(flow_mode_label(flow_mode))

    graph_label = "\n".join(label_parts)

    lines = [
        "digraph topology {",
        "  graph [",
        f"    label={dot_quote(graph_label)},",
        '    labelloc="t",',
        '    fontsize="20",',
        '    fontname="Helvetica",',
        '    rankdir="LR",',
        '    bgcolor="white",',
        '    overlap="false",',
        '    splines="true",',
        '    nodesep="0.45",',
        '    ranksep="1.0",',
        '    pad="0.25"',
        "  ];",
        '  node [fontname="Helvetica", fontsize="10", style="filled", margin="0.08,0.05"];',
        '  edge [fontname="Helvetica", fontsize="9", color="#6b7280"];',
        "",
    ]

    routers = model["routers"] or [{"id": "gateway_router", "type": "central_gateway"}]
    router_ids = {str(router.get("id", "gateway_router")) for router in routers}
    for router in routers:
        router_id = str(router.get("id", "gateway_router"))
        lines.append(
            "  "
            + dot_node_id("router", router_id)
            + " ["
            + dot_attrs(
                label=router_id,
                shape="diamond",
                fillcolor=ROUTER_COLOR["fill"],
                color=ROUTER_COLOR["border"],
                fontcolor="white",
                tooltip=str(router.get("purpose", router.get("type", "router"))),
            )
            + "];"
        )

    central_router_id = str(routers[0].get("id", "gateway_router"))
    declared_hosts = set()
    
    # Determina quali switch sono collegati al monitoring switch
    monitoring_switch_config = model.get("monitoring_switch")
    private_switch_names = set()
    if monitoring_switch_config:
        private_switch_names = set(monitoring_switch_config.get("connects_to", []))

    for index, subnet in enumerate(model["subnets"], start=1):
        network = str(subnet.get("network", f"subnet-{index}"))
        subnet_type = str(subnet.get("type", "default"))
        switch_name = str(subnet.get("switch_name", f"switch-{index}"))
        switch_color = SWITCH_COLORS.get(subnet_type, SWITCH_COLORS["default"])
        cluster_fill = "#eef7f1" if subnet_type == "client_subnet" else "#fff4e6"
        if subnet_type not in {"client_subnet", "internet"}:
            cluster_fill = "#f8fafc"

        lines.append(f"  subgraph {safe_cluster_name(network)} {{")
        lines.append(
            "    graph ["
            + dot_attrs(
                label=f"{network}\n{subnet_type}",
                style="rounded,filled",
                color=switch_color["border"],
                fillcolor=cluster_fill,
                fontname="Helvetica",
                fontsize="12",
            )
            + "];"
        )
        lines.append(
            "    "
            + dot_node_id("switch", switch_name)
            + " ["
            + dot_attrs(
                label=switch_name,
                shape="box",
                fillcolor=switch_color["fill"],
                color=switch_color["border"],
                fontcolor="white",
                tooltip=f"Switch: {switch_name}\nNetwork: {network}",
            )
            + "];"
        )

        for host in sorted(str(item) for item in subnet.get("hosts", [])):
            role = host_role(host, model)
            colors = HOST_COLORS.get(role, HOST_COLORS["unknown"])
            declared_hosts.add(host)
            lines.append(
                "    "
                + dot_node_id("host", host)
                + " ["
                + dot_attrs(
                    label=host,
                    shape="ellipse",
                    fillcolor=colors["fill"],
                    color=colors["border"],
                    fontcolor="#111827",
                    tooltip=host_tooltip(host, model),
                )
                + "];"
            )
            lines.append(
                "    "
                + dot_node_id("switch", switch_name)
                + " -> "
                + dot_node_id("host", host)
                + " ["
                + dot_attrs(dir="none", color=TOPOLOGY_EDGE_COLOR, penwidth="1.2", tooltip="link host-switch")
                + "];"
            )

        lines.append("  }")
        
        # Se lo switch è privato e c'è monitoring switch, non collegarlo al router
        # (verrà collegato al monitoring switch dopo)
        is_private_switch = switch_name in private_switch_names
        if not is_private_switch:
            # Switch internet o senza monitoring: collega direttamente al router
            lines.append(
                "  "
                + dot_node_id("router", central_router_id)
                + " -> "
                + dot_node_id("switch", switch_name)
                + " ["
                + dot_attrs(dir="none", color=TOPOLOGY_EDGE_COLOR, penwidth="1.8", tooltip="link router-switch")
                + "];"
            )
        lines.append("")

    if model["unknown_hosts"]:
        lines.append(f"  subgraph {safe_cluster_name('unknown_hosts')} {{")
        lines.append(
            "    graph ["
            + dot_attrs(
                label="Host non mappati",
                style="rounded,filled",
                color="#6b7280",
                fillcolor="#f8fafc",
                fontname="Helvetica",
                fontsize="12",
            )
            + "];"
        )
        for host in sorted(model["unknown_hosts"]):
            role = host_role(host, model)
            colors = HOST_COLORS.get(role, HOST_COLORS["unknown"])
            declared_hosts.add(host)
            lines.append(
                "    "
                + dot_node_id("host", host)
                + " ["
                + dot_attrs(
                    label=host,
                    shape="ellipse",
                    fillcolor=colors["fill"],
                    color=colors["border"],
                    tooltip=host_tooltip(host, model),
                )
                + "];"
            )
        lines.append("  }")
        lines.append("")
    
    # Crea il nodo monitoring switch se presente
    if monitoring_switch_config:
        monitoring_switch_name = monitoring_switch_config.get("name", "s_monitoring")
        monitoring_switch_color = {"fill": "#8b5cf6", "border": "#5b21b6"}  # Viola per distinguerlo
        
        lines.append(
            "  "
            + dot_node_id("switch", monitoring_switch_name)
            + " ["
            + dot_attrs(
                label=monitoring_switch_name + "\n(monitoring)",
                shape="box",
                fillcolor=monitoring_switch_color["fill"],
                color=monitoring_switch_color["border"],
                fontcolor="white",
                penwidth="2.0",
                tooltip=f"Monitoring Switch: {monitoring_switch_name}\n{monitoring_switch_config.get('purpose', '')}",
            )
            + "];"
        )
        
        # Collega monitoring switch al router
        lines.append(
            "  "
            + dot_node_id("router", central_router_id)
            + " -> "
            + dot_node_id("switch", monitoring_switch_name)
            + " ["
            + dot_attrs(dir="none", color=monitoring_switch_color["border"], penwidth="2.5", tooltip="link router-monitoring")
            + "];"
        )
        
        # Collega ogni switch privato al monitoring switch
        for priv_switch_name in private_switch_names:
            lines.append(
                "  "
                + dot_node_id("switch", priv_switch_name)
                + " -> "
                + dot_node_id("switch", monitoring_switch_name)
                + " ["
                + dot_attrs(dir="none", color=TOPOLOGY_EDGE_COLOR, penwidth="1.8", tooltip="link private-monitoring")
                + "];"
            )
        lines.append("")

    probe = model["probe"]
    if probe:
        probe_name = str(probe.get("name", "probe"))
        
        # Determina a cosa collegare il probe: usa mirror_switches se presente, altrimenti connection o router
        mirror_switches = probe.get("mirror_switches", [])
        if mirror_switches:
            # Collega al primo switch in mirror_switches
            probe_connection = str(mirror_switches[0])
            probe_connection_type = "switch"
        else:
            # Fallback alla vecchia logica
            probe_connection = str(probe.get("connection", central_router_id))
            probe_connection_type = "switch" if probe_connection in private_switch_names else "router"
            if probe_connection_type == "router" and probe_connection not in router_ids:
                probe_connection = central_router_id
        lines.append(
            "  "
            + dot_node_id("probe", probe_name)
            + " ["
            + dot_attrs(
                label=f"{probe_name}\n{probe.get('ip', '')}",
                shape="note",
                fillcolor=PROBE_COLOR["fill"],
                color=PROBE_COLOR["border"],
                fontcolor="#111827",
                tooltip=(
                    f"Probe: {probe_name}\n"
                    f"IP: {probe.get('ip', '-')}\n"
                    f"Capture: {probe.get('capture_file', '-')}"
                ),
            )
            + "];"
        )
        lines.append(
            "  "
            + dot_node_id(probe_connection_type, probe_connection)
            + " -> "
            + dot_node_id("probe", probe_name)
            + " ["
            + dot_attrs(dir="none", color=PROBE_COLOR["border"], penwidth="1.6", 
                       tooltip=f"probe mirror from {probe_connection}")
            + "];"
        )
        lines.append("")

    if flow_mode == "full":
        for flow in model["flows"]:
            src_ip = flow["src_ip"]
            dst_ip = flow["dst_ip"]
            if src_ip not in declared_hosts or dst_ip not in declared_hosts:
                continue

            count = int(flow.get("flow_count", 1) or 1)
            label = str(count) if count > 1 else ""
            lines.append(
                "  "
                + dot_node_id("host", src_ip)
                + " -> "
                + dot_node_id("host", dst_ip)
                + " ["
                + dot_attrs(
                    label=label,
                    color=FLOW_COLOR,
                    fontcolor=FLOW_COLOR,
                    penwidth=f"{flow_width(count):.2f}",
                    arrowsize="0.65",
                    style="dashed",
                    constraint="false",
                    tooltip=flow_tooltip(flow),
                )
                + "];"
            )
    elif flow_mode == "aggregate":
        for flow in aggregate_flows_for_svg(model):
            count = int(flow.get("flow_count", 1) or 1)
            lines.append(
                "  "
                + dot_quote(flow["src_node"])
                + " -> "
                + dot_quote(flow["dst_node"])
                + " ["
                + dot_attrs(
                    label=str(count),
                    color=FLOW_COLOR,
                    fontcolor=FLOW_COLOR,
                    penwidth=f"{flow_width(count):.2f}",
                    arrowsize="0.75",
                    style="dashed",
                    constraint="false",
                    tooltip=aggregated_flow_tooltip(flow),
                )
                + "];"
            )

    lines.append("}")
    return "\n".join(lines) + "\n"


def write_svg(dot_source, svg_path, dot_path=None):
    dot_bin = shutil.which("dot")
    if not dot_bin:
        raise SystemExit(
            "Errore: Graphviz non trovato. Installa il comando 'dot' oppure usa il container evaluator aggiornato."
        )

    if dot_path:
        dot_path.write_text(dot_source, encoding="utf-8")

    try:
        result = subprocess.run(
            [dot_bin, "-Tsvg"],
            input=dot_source,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or "errore sconosciuto"
        raise GraphvizRenderError(stderr)

    svg_path.write_text(result.stdout, encoding="utf-8")


def pyvis_color(colors):
    return {
        "background": colors["fill"],
        "border": colors["border"],
        "highlight": {"background": colors["fill"], "border": "#111827"},
    }


def add_pyvis_node(net, node, label, title, group, shape, colors, value=1):
    net.add_node(
        node,
        label=label,
        title=title,
        group=group,
        shape=shape,
        color=pyvis_color(colors),
        value=value,
        borderWidth=2,
        font={"face": "Arial", "size": 14, "color": "#111827"},
    )


def write_pyvis_html(model, html_path, graph_name, height):
    try:
        from pyvis.network import Network
    except ImportError:
        raise SystemExit(
            "Errore: PyVis non installato. Installa 'pyvis' oppure ricostruisci il container evaluator."
        )

    net = Network(
        height=height,
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#111827",
        cdn_resources="in_line",
    )
    net.heading = graph_name

    routers = model["routers"] or [{"id": "gateway_router", "type": "central_gateway"}]
    central_router_id = str(routers[0].get("id", "gateway_router"))
    router_ids = {str(router.get("id", "gateway_router")) for router in routers}
    
    # Determina quali switch sono collegati al monitoring switch
    monitoring_switch_config = model.get("monitoring_switch")
    private_switch_names = set()
    if monitoring_switch_config:
        private_switch_names = set(monitoring_switch_config.get("connects_to", []))

    for router in routers:
        router_id = str(router.get("id", "gateway_router"))
        add_pyvis_node(
            net,
            node_id("router", router_id),
            router_id,
            html_title(
                [
                    f"Router: {router_id}",
                    f"Tipo: {router.get('type', '-')}",
                    router.get("purpose", ""),
                ]
            ),
            "router",
            "diamond",
            ROUTER_COLOR,
            value=12,
        )

    for index, subnet in enumerate(model["subnets"], start=1):
        network = str(subnet.get("network", f"subnet-{index}"))
        subnet_type = str(subnet.get("type", "default"))
        switch_name = str(subnet.get("switch_name", f"switch-{index}"))
        switch_color = SWITCH_COLORS.get(subnet_type, SWITCH_COLORS["default"])

        add_pyvis_node(
            net,
            node_id("switch", switch_name),
            switch_name,
            html_title(
                [
                    f"Switch: {switch_name}",
                    f"Network: {network}",
                    f"Tipo: {subnet_type}",
                    f"Host: {len(subnet.get('hosts', []))}",
                ]
            ),
            "switch",
            "box",
            switch_color,
            value=max(8, len(subnet.get("hosts", []))),
        )
        
        # Se lo switch è privato e c'è monitoring switch, non collegarlo al router
        # (verrà collegato al monitoring switch dopo)
        is_private_switch = switch_name in private_switch_names
        if not is_private_switch:
            # Switch internet o senza monitoring: collega direttamente al router
            net.add_edge(
                node_id("router", central_router_id),
                node_id("switch", switch_name),
                title=html_title(["Link router-switch", network]),
                color=TOPOLOGY_EDGE_COLOR,
                width=2,
                arrows="",
            )

        for host in sorted(str(item) for item in subnet.get("hosts", [])):
            role = host_role(host, model)
            colors = HOST_COLORS.get(role, HOST_COLORS["unknown"])
            add_pyvis_node(
                net,
                node_id("host", host),
                host,
                html_title(host_tooltip(host, model).splitlines()),
                role,
                "dot",
                colors,
                value=max(4, model["outgoing"][host] + model["incoming"][host]),
            )
            net.add_edge(
                node_id("switch", switch_name),
                node_id("host", host),
                title=html_title(["Link host-switch", network]),
                color=TOPOLOGY_EDGE_COLOR,
                width=1,
                arrows="",
            )

    for host in sorted(model["unknown_hosts"]):
        role = host_role(host, model)
        colors = HOST_COLORS.get(role, HOST_COLORS["unknown"])
        add_pyvis_node(
            net,
            node_id("host", host),
            host,
            html_title(host_tooltip(host, model).splitlines()),
            role,
            "dot",
            colors,
            value=max(4, model["outgoing"][host] + model["incoming"][host]),
        )
    
    # Crea il nodo monitoring switch se presente
    if monitoring_switch_config:
        monitoring_switch_name = monitoring_switch_config.get("name", "s_monitoring")
        monitoring_switch_color = {"fill": "#8b5cf6", "border": "#5b21b6"}  # Viola per distinguerlo
        
        add_pyvis_node(
            net,
            node_id("switch", monitoring_switch_name),
            monitoring_switch_name + " (monitoring)",
            html_title(
                [
                    f"Monitoring Switch: {monitoring_switch_name}",
                    f"Tipo: {monitoring_switch_config.get('type', 'aggregation')}",
                    monitoring_switch_config.get('purpose', ''),
                    f"Collega {len(private_switch_names)} switch privati",
                ]
            ),
            "monitoring_switch",
            "box",
            monitoring_switch_color,
            value=15,
        )
        
        # Collega monitoring switch al router
        net.add_edge(
            node_id("router", central_router_id),
            node_id("switch", monitoring_switch_name),
            title=html_title(["Link router-monitoring switch"]),
            color=monitoring_switch_color["border"],
            width=3,
            arrows="",
        )
        
        # Collega ogni switch privato al monitoring switch
        for priv_switch_name in private_switch_names:
            net.add_edge(
                node_id("switch", priv_switch_name),
                node_id("switch", monitoring_switch_name),
                title=html_title(["Link private-monitoring"]),
                color=TOPOLOGY_EDGE_COLOR,
                width=2,
                arrows="",
            )

    probe = model["probe"]
    if probe:
        probe_name = str(probe.get("name", "probe"))
        
        # Determina a cosa collegare il probe: usa mirror_switches se presente, altrimenti connection o router
        mirror_switches = probe.get("mirror_switches", [])
        if mirror_switches:
            # Collega al primo switch in mirror_switches
            probe_connection = str(mirror_switches[0])
            probe_connection_type = "switch"
        else:
            # Fallback alla vecchia logica
            probe_connection = str(probe.get("connection", central_router_id))
            probe_connection_type = "switch" if probe_connection in private_switch_names else "router"
            if probe_connection_type == "router" and probe_connection not in router_ids:
                probe_connection = central_router_id
        add_pyvis_node(
            net,
            node_id("probe", probe_name),
            probe_name,
            html_title(
                [
                    f"Probe: {probe_name}",
                    f"IP: {probe.get('ip', '-')}",
                    f"Capture: {probe.get('capture_file', '-')}",
                ]
            ),
            "probe",
            "triangle",
            PROBE_COLOR,
            value=8,
        )
        net.add_edge(
            node_id(probe_connection_type, probe_connection),
            node_id("probe", probe_name),
            title=html_title([f"Probe mirror from {probe_connection}", probe.get("mode", "")]),
            color=PROBE_COLOR["border"],
            width=2,
            arrows="",
        )

    for flow in model["flows"]:
        count = int(flow.get("flow_count", 1) or 1)
        label = str(count) if count > 1 else ""
        net.add_edge(
            node_id("host", flow["src_ip"]),
            node_id("host", flow["dst_ip"]),
            label=label,
            title=html_title(flow_tooltip(flow).splitlines()),
            color=FLOW_COLOR,
            width=flow_width(count),
            arrows="to",
            dashes=True,
            smooth={"enabled": True, "type": "curvedCW", "roundness": 0.18},
        )

    options = {
        "configure": {"enabled": True, "filter": ["physics"]},
        "interaction": {
            "hover": True,
            "navigationButtons": True,
            "keyboard": True,
            "multiselect": True,
        },
        "nodes": {
            "scaling": {"min": 8, "max": 34},
            "font": {"face": "Arial", "size": 14},
        },
        "edges": {
            "smooth": {"enabled": True, "type": "dynamic"},
            "font": {"size": 11, "align": "middle"},
        },
        "physics": {
            "enabled": True,
            "barnesHut": {
                "gravitationalConstant": -18000,
                "centralGravity": 0.25,
                "springLength": 140,
                "springConstant": 0.035,
                "damping": 0.12,
            },
            "stabilization": {"enabled": True, "iterations": 250},
        },
    }
    net.set_options("var options = " + json.dumps(options))
    net.write_html(str(html_path), notebook=False, open_browser=False)
    inject_html_filters(html_path, graph_name)


def inject_html_filters(html_path, graph_name):
    html_source = html_path.read_text(encoding="utf-8")
    if "TOPOLOGY_VIEWER_FILTERS" in html_source:
        return

    graph_title = html.escape(str(graph_name))
    escaped_title_pattern = re.escape(graph_title)
    html_source = re.sub(
        rf"\s*<center>\s*<h1>\s*{escaped_title_pattern}\s*</h1>\s*</center>\s*",
        "\n",
        html_source,
        flags=re.IGNORECASE,
    )

    controls_css = """
        <!-- TOPOLOGY_VIEWER_FILTERS_CSS -->
        <style>
            .topology-title {
                margin: 14px 180px 8px 16px;
                font-family: Arial, sans-serif;
                font-size: 24px;
                font-weight: 600;
                color: #111827;
            }
            .topology-controls {
                position: fixed;
                top: 12px;
                right: 12px;
                z-index: 10000;
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 10px 12px;
                background: rgba(255, 255, 255, 0.94);
                border: 1px solid #d1d5db;
                border-radius: 6px;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.16);
                font-family: Arial, sans-serif;
                font-size: 13px;
                color: #111827;
            }
            .topology-controls label {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                white-space: nowrap;
                cursor: pointer;
            }
            .topology-controls input {
                margin: 0;
            }
            .topology-controls button {
                border: 1px solid #9ca3af;
                border-radius: 5px;
                background: #f9fafb;
                color: #111827;
                padding: 4px 8px;
                cursor: pointer;
                font-size: 12px;
            }
            .topology-controls button:hover {
                background: #f3f4f6;
            }
            @media (max-width: 720px) {
                .topology-title {
                    margin: 72px 10px 8px 10px;
                    font-size: 20px;
                }
                .topology-controls {
                    left: 10px;
                    right: 10px;
                    top: 10px;
                    flex-wrap: wrap;
                }
            }
        </style>
"""
    controls_html = """
        <!-- TOPOLOGY_VIEWER_FILTERS_HTML -->
        <h1 class="topology-title">__TOPOLOGY_TITLE__</h1>
        <div id="topology-controls" class="topology-controls" aria-label="Filtri topologia">
            <label><input type="checkbox" data-topology-filter="flows" checked> Flussi</label>
            <label><input type="checkbox" data-topology-filter="hosts" checked> Nodi</label>
            <label><input type="checkbox" data-topology-filter="switches" checked> Switch</label>
            <button type="button" data-topology-action="show-all">Mostra tutto</button>
        </div>
""".replace("__TOPOLOGY_TITLE__", graph_title)
    controls_js = """

                  // TOPOLOGY_VIEWER_FILTERS_JS
                  (function installTopologyFilters() {
                      var controls = document.getElementById("topology-controls");
                      if (!controls || !nodes || !edges || !network || !vis.DataSet) {
                          return;
                      }

                      var state = {
                          flows: true,
                          hosts: true,
                          switches: true
                      };

                      function startsWith(value, prefix) {
                          return String(value || "").indexOf(prefix) === 0;
                      }

                      function isHostNode(nodeOrId) {
                          var id = typeof nodeOrId === "string" ? nodeOrId : nodeOrId.id;
                          return startsWith(id, "host:");
                      }

                      function isSwitchNode(nodeOrId) {
                          var id = typeof nodeOrId === "string" ? nodeOrId : nodeOrId.id;
                          return startsWith(id, "switch:");
                      }

                      function isFlowEdge(edge) {
                          return edge.dashes === true ||
                              String(edge.color || "").toLowerCase() === "#e76f51" ||
                              (edge.arrows === "to" && isHostNode(edge.from) && isHostNode(edge.to));
                      }

                      function isNodeVisible(nodeOrId) {
                          if (!state.hosts && isHostNode(nodeOrId)) {
                              return false;
                          }
                          if (!state.switches && isSwitchNode(nodeOrId)) {
                              return false;
                          }
                          return true;
                      }

                      var originalNodeList = nodes.get();
                      var originalEdgeList = edges.get();
                      var originalEdgeIds = edges.getIds();

                      function hideProgressUi() {
                          ["loadingBar", "progressBar", "loadingText"].forEach(function(id) {
                              var element = document.getElementById(id);
                              if (element) {
                                  element.style.opacity = 0;
                                  element.style.display = "none";
                                  element.style.visibility = "hidden";
                              }
                          });
                          document.querySelectorAll(".progress, .progress-bar").forEach(function(element) {
                              element.style.display = "none";
                              element.style.visibility = "hidden";
                          });
                      }

                      function refreshGraph() {
                          var visibleNodeIds = {};
                          var nodeUpdates = originalNodeList.map(function(node) {
                              var visible = isNodeVisible(node);
                              if (visible) {
                                  visibleNodeIds[node.id] = true;
                              }
                              return {
                                  id: node.id,
                                  hidden: !visible
                              };
                          });
                          var edgeUpdates = originalEdgeList.map(function(edge, index) {
                              var visible = visibleNodeIds[edge.from] && visibleNodeIds[edge.to];
                              if (!state.flows && isFlowEdge(edge)) {
                                  visible = false;
                              }
                              return {
                                  id: edge.id !== undefined ? edge.id : originalEdgeIds[index],
                                  hidden: !visible
                              };
                          });

                          nodes.update(nodeUpdates);
                          edges.update(edgeUpdates);
                          network.stopSimulation();
                          network.redraw();
                          hideProgressUi();
                          setTimeout(hideProgressUi, 50);
                          setTimeout(hideProgressUi, 250);
                      }

                      network.on("stabilizationIterationsDone", hideProgressUi);
                      network.on("stabilized", hideProgressUi);
                      setTimeout(hideProgressUi, 0);

                      controls.querySelectorAll("[data-topology-filter]").forEach(function(input) {
                          input.addEventListener("change", function(event) {
                              state[event.target.getAttribute("data-topology-filter")] = event.target.checked;
                              refreshGraph();
                          });
                      });

                      var showAll = controls.querySelector("[data-topology-action='show-all']");
                      if (showAll) {
                          showAll.addEventListener("click", function() {
                              controls.querySelectorAll("[data-topology-filter]").forEach(function(input) {
                                  input.checked = true;
                                  state[input.getAttribute("data-topology-filter")] = true;
                              });
                              refreshGraph();
                          });
                      }
                  })();
"""

    if "</head>" in html_source:
        html_source = html_source.replace("</head>", controls_css + "\n    </head>", 1)
    else:
        html_source = controls_css + html_source

    if "<body>" in html_source:
        html_source = html_source.replace("<body>", "<body>" + controls_html, 1)
    else:
        html_source = controls_html + html_source

    marker = "network = new vis.Network(container, data, options);"
    if marker not in html_source:
        raise SystemExit("Errore: impossibile aggiungere i filtri all'HTML PyVis.")
    html_source = html_source.replace(marker, marker + controls_js, 1)

    html_path.write_text(html_source, encoding="utf-8")


def print_summary(paths, model, svg_flow_mode=None):
    stats = model["statistics"]
    print("Topologia caricata:")
    print(f"  - Subnet: {len(model['subnets'])}")
    print(f"  - Router: {len(model['routers']) or 1}")
    print(f"  - Host noti: {len(model['known_hosts'])}")
    print(f"  - Host non mappati: {len(model['unknown_hosts'])}")
    print(f"  - Flussi aggregati: {len(model['flows'])}")
    if svg_flow_mode:
        print(f"  - Flussi nello SVG: {flow_mode_label(svg_flow_mode)}")
    if stats:
        print(f"  - Flussi nel JSON: {stats.get('total_flows', '-')}")

    print("\nFile generati:")
    for path in paths:
        print(f"  - {path}")


def main():
    args = parse_args()
    if args.skip_svg and args.skip_html:
        raise SystemExit("Errore: --skip-svg e --skip-html non possono essere usati insieme.")

    input_path = Path(args.topology_json)
    topology = load_topology(input_path)
    model = build_model(topology)

    output_dir = infer_output_dir(input_path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    graph_name = args.name or input_path.stem
    svg_path = output_dir / f"{graph_name}.svg"
    html_path = output_dir / f"{graph_name}.html"
    dot_path = output_dir / f"{graph_name}.dot" if args.write_dot else None

    generated = []
    svg_flow_mode = None

    if not args.skip_svg:
        svg_flow_mode = resolve_svg_flow_mode(
            model,
            args.svg_flow_mode,
            args.svg_flow_threshold,
        )
        dot_source = build_dot(model, graph_name, flow_mode=svg_flow_mode)
        try:
            write_svg(dot_source, svg_path, dot_path=dot_path)
        except GraphvizRenderError as exc:
            if args.svg_flow_mode != "auto" or svg_flow_mode == "none":
                raise SystemExit(f"Errore durante il rendering Graphviz: {exc}")

            fallback_modes = ["aggregate", "none"] if svg_flow_mode == "full" else ["none"]
            for fallback_mode in fallback_modes:
                print(
                    "Avviso: Graphviz non ha renderizzato lo SVG in modalità "
                    f"'{svg_flow_mode}' ({exc}). Riprovo con '{fallback_mode}'.",
                    file=sys.stderr,
                )
                svg_flow_mode = fallback_mode
                dot_source = build_dot(model, graph_name, flow_mode=svg_flow_mode)
                try:
                    write_svg(dot_source, svg_path, dot_path=dot_path)
                    break
                except GraphvizRenderError as fallback_exc:
                    exc = fallback_exc
            else:
                raise SystemExit(f"Errore durante il rendering Graphviz: {exc}")

        if dot_path:
            generated.append(dot_path)
        generated.append(svg_path)

    if not args.skip_html:
        write_pyvis_html(model, html_path, graph_name, args.height)
        generated.append(html_path)

    print_summary(generated, model, svg_flow_mode=svg_flow_mode)


if __name__ == "__main__":
    main()
