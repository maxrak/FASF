#!/bin/bash
# Quick test script per verificare le implementazioni client/server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Test Implementations - Quick Start"
echo "=========================================="
echo ""

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Controlla se Python è disponibile
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 non trovato!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python3 trovato${NC}"

# Controlla dipendenze
echo "Verifico dipendenze..."

if python3 -c "import scapy" 2>/dev/null; then
    echo -e "${GREEN}✓ Scapy installato${NC}"
else
    echo -e "${YELLOW}⚠ Scapy non trovato${NC}"
    echo "Vuoi installarlo? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        pip3 install scapy
    fi
fi

echo ""
echo "=========================================="
echo "Eseguo test..."
echo "=========================================="
echo ""

# Esegui test
python3 test_implementations.py "$@"

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "✓ Tutti i test sono passati!"
    echo -e "==========================================${NC}"
else
    echo -e "${RED}=========================================="
    echo "✗ Alcuni test sono falliti"
    echo -e "==========================================${NC}"
    echo "Vedi test_results.json per dettagli"
fi

exit $exit_code
