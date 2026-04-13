#!/bin/bash

# Script per aggregare tutti i file burst_dataset_*.csv in un unico file

# Funzione per stampare l'help
print_help() {
    echo "Usage: $0 <test_name>"
    echo ""
    echo "Aggrega tutti i file burst_dataset_*.csv in un unico file per il test specificato."
    echo ""
    echo "Argomenti:"
    echo "  test_name    Nome del test (es. test1)"
    echo ""
    echo "Output:"
    echo "  shared/results/burst_dataset_<test_name>_complete.csv"
    echo ""
    echo "Esempi:"
    echo "  $0 test1"
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
OUTPUT_FILE="shared/results/burst_dataset_${TEST_NAME}_complete.csv"

echo "📂 Aggregazione file burst per test: ${TEST_NAME}"
echo ""

# Trova tutti i file burst_dataset_*.csv
BURST_FILES=$(ls shared/results/burst_dataset_*.csv 2>/dev/null)

if [ -z "$BURST_FILES" ]; then
    echo "❌ Nessun file burst_dataset trovato in shared/results/"
    exit 1
fi

echo "📊 File trovati:"
echo "$BURST_FILES" | while read file; do
    echo "  - $file ($(wc -l < "$file") righe)"
done
echo ""

# Crea header dal primo file
FIRST_FILE=$(echo "$BURST_FILES" | head -1)
head -1 "$FIRST_FILE" > "$OUTPUT_FILE"

# Aggiungi tutte le righe di dati (salta header)
echo "$BURST_FILES" | while read file; do
    tail -n +2 "$file" >> "$OUTPUT_FILE"
done

TOTAL_ROWS=$(tail -n +2 "$OUTPUT_FILE" | wc -l)

echo "✅ File aggregato salvato: $OUTPUT_FILE"
echo "📈 Righe totali di dati: $TOTAL_ROWS"
echo ""
