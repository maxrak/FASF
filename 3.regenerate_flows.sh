#!/bin/bash

# Funzione per stampare l'help
print_help() {
    echo "Usage: $0 <test_name>"
    echo ""
    echo "Rigenera i flussi CSV da un file PCAP catturato durante il test."
    echo ""
    echo "Argomenti:"
    echo "  test_name    Nome del test (es. test1, mytest)"
    echo "               Il file PCAP deve essere: shared/pcap/<test_name>.pcap"
    echo ""
    echo "Output:"
    echo "  Il file CSV verrà salvato in: shared/output_flows/regenerated_<test_name>.csv"
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
PCAP_FILE="pcap/${TEST_NAME}.pcap"
OUTPUT_FILE="flows/regenerated_${TEST_NAME}.csv"

# Verifica che il file pcap esista
if [ ! -f "shared/${PCAP_FILE}" ]; then
    echo "❌ Errore: File shared/${PCAP_FILE} non trovato"
    echo ""
    echo "Verifica che il test sia stato eseguito con: ./replicate_flow.sh ${TEST_NAME}"
    echo ""
    echo "File PCAP disponibili:"
    ls -lh shared/pcap/*.pcap 2>/dev/null || echo "  Nessun file PCAP trovato"
    exit 1
fi

echo "📂 File PCAP: shared/${PCAP_FILE}"
echo "📝 Output CSV: shared/output_flows/regenerated_${TEST_NAME}.csv"
echo ""

docker compose run --rm cicflowmeter bash ./cicflowmeter.sh "${PCAP_FILE}" "${OUTPUT_FILE}" 