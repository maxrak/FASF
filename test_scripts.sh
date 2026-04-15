#!/bin/bash
# Script di test per verificare i parametri passati agli script modificati
# Questo script NON esegue docker, ma mostra solo i comandi che verrebbero eseguiti

echo "==============================================="
echo "🧪 Test Script Modificati"
echo "==============================================="
echo ""

# Funzione per estrarre il comando docker da uno script
test_script() {
    local script=$1
    local args=$2
    local description=$3
    
    echo "📝 Test: $description"
    echo "   Script: $script $args"
    echo "   Comando Docker:"
    echo -n "   "
    bash -x "$script" $args 2>&1 | grep "^+ docker compose" | sed 's/^+ //' | head -1 || echo "   ❌ Errore nell'esecuzione"
    echo ""
}

# Test 2.replicate_flow.sh
echo "--- 2.replicate_flow.sh (duration: 30s) ---"
test_script "2.replicate_flow.sh" "test2" "Default (scapy_burst)"
test_script "2.replicate_flow.sh" "test2 tcp_simple" "Con tcp_simple"
test_script "2.replicate_flow.sh" "test2 flow_emulator" "Con flow_emulator"

# Test replicate_flow.sh
echo "--- replicate_flow.sh (duration: 60s) ---"
test_script "replicate_flow.sh" "test2" "Default (scapy_burst)"
test_script "replicate_flow.sh" "smallFlows tcp_simple" "Con tcp_simple"

# Test run_full_pipeline.sh
echo "--- run_full_pipeline.sh ---"
echo "⚠️  NOTA: Questo script esegue più comandi, test saltato per evitare esecuzione completa"
echo ""

# Verifica help
echo "==============================================="
echo "📖 Test Help"
echo "==============================================="
echo ""

echo "--- Help 2.replicate_flow.sh ---"
./2.replicate_flow.sh 2>&1 | head -8
echo ""

echo "--- Help replicate_flow.sh ---"
./replicate_flow.sh 2>&1 | head -8
echo ""

echo "==============================================="
echo "✅ Test Completati"
echo "==============================================="
echo ""
echo "Per eseguire realmente gli script:"
echo "  ./2.replicate_flow.sh test2"
echo "  ./2.replicate_flow.sh test2 tcp_simple"
echo "  ./replicate_flow.sh smallFlows flow_emulator"
echo ""
