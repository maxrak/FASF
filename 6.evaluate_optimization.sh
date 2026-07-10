#!/bin/bash

# Funzione per stampare l'help
print_help() {
    echo "Usage: $0 <test_name>"
    echo ""
    echo "Fornisce una valutazione del processo di Ottimizzazione della simulazione."
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
OPTIMIZATION_STATE="optimizer_state/${TEST_NAME}/trials.jsonl"
OUTPUT_DIR="results/${TEST_NAME}"

# # Verifica che il file ORIGINALE esista
# if [ ! -f "/shared/${OPTIMIZATION_STATE}" ]; then
#     echo "❌ Errore: /shared/${OPTIMIZATION_STATE} non trovato"
#     echo ""
#     echo "Verifica che i trials siano stati eseguiti"
#     exit 1
# fi

# # Verifica che la cartella result per il test esista
# if [ ! -d shared/${OUTPUT_DIR} ]; then
#   mkdir -p shared/${OUTPUT_DIR}
# fi


echo "📂 Test Optimized: ${TEST_NAME}"
echo "📂 Optimization Evaluation Report in dir: ${OUTPUT_DIR}"

docker compose run --rm evaluator python plot_optimization.py /app/${OPTIMIZATION_STATE} --out-dir /app/${OUTPUT_DIR}
