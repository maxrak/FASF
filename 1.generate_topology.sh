#!/bin/bash

# Script per generare la topologia di rete da un file CSV di flussi

# Funzione per stampare l'help
print_help() {
    echo "Usage: $0 <csv_filename>"
    echo ""
    echo "Genera una topologia di rete JSON da un file CSV di flussi."
    echo ""
    echo "Argomenti:"
    echo "  csv_filename    Nome del file CSV da analizzare (senza percorso)"
    echo "                  Il file deve trovarsi in input_flows/"
    echo ""
    echo "Output:"
    echo "  Il file di topologia verrà salvato in topologies/<csv_filename>.json"
    echo ""
    echo "Esempi:"
    echo "  $0 test1.csv"
    echo "  $0 flows_data.csv"
    echo ""
    exit 1
}

# Controlla se è stato fornito un argomento
if [ $# -eq 0 ]; then
    echo "❌ Errore: Nessun file CSV specificato"
    echo ""
    print_help
fi

# Controlla se è stato richiesto l'help
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    print_help
fi

CSV_FILE="$1"

echo "📂 Analisi del file: input_flows/$CSV_FILE"
echo "📝 Output: topologies/$CSV_FILE.json"
echo ""

docker compose run --rm evaluator python analyze_flows.py input_flows/$CSV_FILE.csv topologies/$CSV_FILE.json
docker compose run --rm evaluator python generate_initial_params.py input_flows/$CSV_FILE.csv flows_params/
docker compose run --rm evaluator python topology_viewer.py topologies/test3.json