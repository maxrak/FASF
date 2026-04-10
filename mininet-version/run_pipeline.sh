#!/bin/bash

set -e  # stop su errore

echo "======================================"
echo "🚀 CICFlowMeter Pipeline START"
echo "======================================"

# ---------------------------
# CONFIG
# ---------------------------
PCAP_FILE="pcap/capture.pcap"
FEATURE_FILE="features/reconstructed.csv"
TARGET_FILE="features/target.csv"

# ---------------------------
# 1. CLEAN OUTPUT
# # ---------------------------
# echo "[1/6] 🧹 Pulizia output..."

# rm -f pcap/*.pcap || true
# rm -f features/*.csv || true
# rm -f results/*.txt || true

# mkdir -p pcap features results

# ---------------------------
# 2. CHECK INPUT
# ---------------------------
if [ ! -f "$TARGET_FILE" ]; then
    echo "[ERRORE] target.csv non trovato in features/"
    exit 1
fi

echo "[2/6] ✅ Target trovato"

# ---------------------------
# 3. RUN MININET (genera traffico + PCAP)
# ---------------------------
echo "[3/6] 🌐 Avvio Mininet experiment..."

docker compose run --rm mininet

if [ ! -f "$PCAP_FILE" ]; then
    echo "[ERRORE] PCAP non generato"
    exit 1
fi

echo "[+] PCAP generato: $PCAP_FILE"

# ---------------------------
# 4. RUN CICFLOWMETER
# ---------------------------
echo "[4/6] 📊 Estrazione feature con CICFlowMeter..."

docker compose run --rm cicflowmeter ./cicflowmeter.sh /pcap/capture.pcap /features/reconstructed.csv

if [ ! -f "$FEATURE_FILE" ]; then
    echo "[ERRORE] Feature non generate"
    exit 1
fi

echo "[+] Feature generate: $FEATURE_FILE"

# ---------------------------
# 5. RUN EVALUATOR
# ---------------------------
echo "[5/6] 🧪 Valutazione..."

docker compose run --rm evaluator

if [ -f "results/loss.txt" ]; then
    echo "[+] Risultati:"
    cat results/loss.txt
else
    echo "[!] Nessun risultato prodotto"
fi

# ---------------------------
# 6. DONE
# ---------------------------
echo "======================================"
echo "✅ Pipeline completata"
echo "======================================"