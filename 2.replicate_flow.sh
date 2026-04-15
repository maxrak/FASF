#!/bin/bash

# Script per replicare i flussi di rete usando Mininet
#
# Uso:
#   ./2.replicate_flow.sh <flow_name> [implementation]
#
# Parametri:
#   flow_name       : nome del file di flusso (senza estensione)
#   implementation  : tipo di client/server da usare (opzionale, default: scapy_burst)
#                     Valori possibili: scapy_burst, tcp_simple, flow_emulator
#
# Esempi:
#   ./2.replicate_flow.sh test2                    # Usa scapy_burst (default)
#   ./2.replicate_flow.sh test2 tcp_simple         # Usa tcp_simple
#   ./2.replicate_flow.sh smallFlows flow_emulator # Usa flow_emulator

# Verifica che sia stato passato almeno il nome del flusso
if [ -z "$1" ]; then
    echo "Errore: specificare il nome del flusso"
    echo "Uso: ./2.replicate_flow.sh <flow_name> [implementation]"
    echo ""
    echo "Implementazioni disponibili:"
    echo "  - scapy_burst (default): client_scapy_burst_optimized.py + server_adv.py"
    echo "  - tcp_simple: client_replay.py + server_tcp_simple.py"
    echo "  - flow_emulator: flow_emulator.py + server_adv.py"
    exit 1
fi

FLOW_NAME=$1
IMPLEMENTATION=${2:-scapy_burst}  # Default: scapy_burst se non specificato

echo "=== Replica Flusso ==="
echo "Flusso: $FLOW_NAME"
echo "Implementazione: $IMPLEMENTATION"
echo "======================="

docker compose run --rm mininet python3 /app/replay_topology.py \
    topologies/$FLOW_NAME.json \
    30 \
    flows/$FLOW_NAME.csv \
    20 \
    $IMPLEMENTATION