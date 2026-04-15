#!/bin/bash

# Test veloce che mostra solo i comandi docker senza eseguirli
# Usa set -n per il dry-run

echo "=== Verifica Passaggio Parametri ==="
echo ""

echo "Test 1: Default (scapy_burst)"
echo -n "Comando: "
bash -x 2.replicate_flow.sh test2 2>&1 | grep "docker compose run" | head -1 | sed 's/^+ //' 2>/dev/null &
pid1=$!

echo ""
echo "Test 2: Con tcp_simple"
echo -n "Comando: "
bash -x 2.replicate_flow.sh test2 tcp_simple 2>&1 | grep "docker compose run" | head -1 | sed 's/^+ //' 2>/dev/null &
pid2=$!

echo ""
echo "Test 3: Con flow_emulator"
echo -n "Comando: "
bash -x 2.replicate_flow.sh test2 flow_emulator 2>&1 | grep "docker compose run" | head -1 | sed 's/^+ //' 2>/dev/null &
pid3=$!

# Aspetta massimo 3 secondi
sleep 3
kill $pid1 $pid2 $pid3 2>/dev/null

echo ""
echo "=== Test Completato ==="
