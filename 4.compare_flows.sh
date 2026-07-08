#!/bin/bash

# Funzione per stampare l'help
print_help() {
    echo "Usage: $0 <test_name>"
    echo ""
    echo "Confronta i flussi CSV di input con quelli rigenerati."
    echo ""
    echo "Argomenti:"
    echo "  test_name    Nome del test (es. test1, mytest)"
    echo "               Il file PCAP deve essere: shared/pcap/<test_name>.pcap"
    echo ""
    echo "Output:"
    echo "  Il file CSV verrà salvato in: shared/results/report_<test_name>.csv"
    echo ""
    echo "Esempi:"
    echo "  $0 test1"
    echo "  $0 myexperiment"
    echo ""
    exit 1
}

# Controlla se è stato fornito un argomento
if [ $# -eq 0 ]; then
    echo "❌ Errore: Nessun nome test specificato"
    echo ""
    print_help
fi

# Controlla se è stato richiesto l'help
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    print_help
fi

TEST_NAME="$1"
ORIG_FILE="input_flows/${TEST_NAME}.csv"
REGEN_FILE="output_flows/regenerated_${TEST_NAME}_clean.csv"
REPORT_DIR="results/${TEST_NAME}/"

# Verifica che il file ORIGINALE esista
if [ ! -f "shared/${ORIG_FILE}" ]; then
    echo "❌ Errore: File shared/${ORIG_FILE} non trovato"
    echo ""
    echo "Verifica che sia disponibile il file dei flussi originale"
    echo ""
    echo "File PCAP disponibili:"
    ls -lh shared/input_flows/*.csv 2>/dev/null || echo "  Nessun file CSV trovato"
    exit 1
fi

# Verifica che il file RIGENERATO esista
if [ ! -f "shared/${REGEN_FILE}" ]; then
    echo "❌ Errore: File shared/${REGEN_FILE} non trovato"
    echo ""
    echo "Verifica che siano avvenuti i seguenti passi:"
    echo "      1: generazione della topologia: ./1.generate_topology.sh ${TEST_NAME}
    echo "      1: generazione della topologia: ./2.replicate_flows.sh ${TEST_NAME}
    echo "      1: generazione della topologia: ./3.regenerate_flows.sh ${TEST_NAME}
    echo ""
    echo "File Flows regenerateddisponibili:"
    ls -lh shared/output_flows/*.csv 2>/dev/null || echo "  Nessun file CSV trovato"
    exit 1
fi

if [ ! -f "shared/${REGEN_FILE}" ]; then
    echo "❌ Errore: File shared/${REGEN_FILE} non trovato"
    echo ""
    echo "Verifica che siano avvenuti i seguenti passi:"
    echo "      1: generazione della topologia: ./1.generate_topology.sh ${TEST_NAME}
    echo "      1: generazione della topologia: ./2.replicate_flows.sh ${TEST_NAME}
    echo "      1: generazione della topologia: ./3.regenerate_flows.sh ${TEST_NAME}
    echo ""
    echo "File Flows regenerateddisponibili:"
    ls -lh shared/output_flows/*.csv 2>/dev/null || echo "  Nessun file CSV trovato"
    exit 1
fi

# Verifica che la cartella result per il test esista
if [ ! -d shared/${REPORT_DIR} ]; then
  mkdir -p shared/${REPORT_DIR}
fi

echo "📂 File INPUT FLow: shared/${ORIG_FILE}"
echo "📝 File Output FLow: shared/${REGEN_FILE}.csv"
echo "📂 Folder Output Comparison result: shared/${REPORT_DIR}"

docker compose run --rm evaluator python flow_compare_tool.py ${ORIG_FILE} ${REGEN_FILE} -o ${REPORT_DIR}