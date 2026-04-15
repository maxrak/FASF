#!/bin/bash
# Pipeline completa: Analisi → Topologia → Replay → Capture
#
# Uso:
#   ./run_full_pipeline.sh [csv_file] [duration] [max_subnets] [implementation]
#
# Parametri (tutti opzionali):
#   csv_file       : file CSV con i flussi (default: features/target.csv)
#   duration       : durata replay in secondi (default: 60)
#   max_subnets    : numero massimo di subnet (default: 10)
#   implementation : tipo client/server (default: scapy_burst)
#                    Valori: scapy_burst, tcp_simple, flow_emulator
#
# Esempi:
#   ./run_full_pipeline.sh                                    # Tutti i default
#   ./run_full_pipeline.sh myflows.csv                        # Custom CSV
#   ./run_full_pipeline.sh myflows.csv 120                    # CSV + duration
#   ./run_full_pipeline.sh myflows.csv 120 20 tcp_simple      # Tutti i parametri

set -e  # Exit on error

echo "🚀 PIPELINE COMPLETA: Flow Analysis → Network Replay → Packet Capture"
echo "======================================================================"
echo ""

# Parametri configurabili
CSV_FILE="${1:-features/target.csv}"
DURATION="${2:-60}"
MAX_SUBNETS="${3:-10}"
IMPLEMENTATION="${4:-scapy_burst}"  # Default: scapy_burst

echo "📋 Configurazione:"
echo "  - File CSV: $CSV_FILE"
echo "  - Durata replay: $DURATION secondi"
echo "  - Max subnet: $MAX_SUBNETS"
echo "  - Implementazione: $IMPLEMENTATION"
echo ""

# Step 1: Genera topologia dal CSV
echo "1️⃣  Genera topologia dal CSV..."
python app/analyze_flows.py "$CSV_FILE" network_topology.json
echo ""

# Step 2: Copia in shared
echo "2️⃣  Copia topologia in /shared..."
cp network_topology.json shared/
ls -lh shared/network_topology.json
echo ""

# Step 3: Cleanup Mininet
echo "3️⃣  Pulizia rete Mininet precedente..."
docker compose run --rm mininet bash -c "mn -c 2>/dev/null || true"
echo ""

# Step 4: Esegui replay con probe
echo "4️⃣  Esegui replay in Mininet con probe..."
echo "    (Durata: $DURATION secondi, Max subnet: $MAX_SUBNETS, Implementazione: $IMPLEMENTATION)"
docker compose run --rm mininet python3 /app/replay_topology.py \
    /shared/network_topology.json \
    "$DURATION" \
    /features/target.csv \
    "$MAX_SUBNETS" \
    "$IMPLEMENTATION"
echo ""

# Step 5: Verifica pcap generato
echo "5️⃣  Verifica file pcap generato..."
if [ -f "pcap/capture.pcap" ]; then
    SIZE=$(ls -lh pcap/capture.pcap | awk '{print $5}')
    PACKETS=$(tcpdump -r pcap/capture.pcap 2>/dev/null | wc -l || echo "N/A")
    echo "✅ File pcap generato con successo!"
    echo "  - File: pcap/capture.pcap"
    echo "  - Dimensione: $SIZE"
    echo "  - Pacchetti: $PACKETS"
    echo ""
    echo "🔍 Anteprima primi 10 pacchetti:"
    tcpdump -r pcap/capture.pcap -n -c 10 2>/dev/null || echo "  (tcpdump non disponibile per anteprima)"
else
    echo "❌ File pcap non trovato!"
    exit 1
fi

echo ""
echo "======================================================================"
echo "✅ PIPELINE COMPLETATA!"
echo ""
echo "📂 File generati:"
echo "  - network_topology.json (configurazione rete)"
echo "  - shared/network_topology.json (copia per container)"
echo "  - pcap/capture.pcap (packet capture)"
echo ""
echo "🔧 Prossimi passi:"
echo "  1. Analizza il pcap con CICFlowMeter:"
echo "     docker compose run --rm cicflowmeter bash"
echo "     ./cicflowmeter.sh /pcap /features"
echo ""
echo "  2. Confronta i flow originali con quelli catturati"
echo ""
