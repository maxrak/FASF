#!/bin/bash
# Script per testare il probe in replay_topology.py

echo "🔍 Test del nodo probe in Mininet"
echo "================================="
echo ""

# Crea un piccolo test topology validator
cat > /tmp/test_probe_validator.py << 'PYEOF'
import sys
sys.path.insert(0, '/app')
from replay_topology import load_topology

print("✅ Caricamento topologia...")
topology = load_topology('/shared/test_topology_small.json')

print(f"✅ Architettura: {topology['architecture']}")
print(f"✅ Subnets: {len(topology['subnets'])}")
print(f"✅ Probe presente: {'probe' in topology}")

if 'probe' in topology:
    probe = topology['probe']
    print(f"\n🔍 CONFIGURAZIONE PROBE:")
    print(f"  - Nome: {probe['name']}")
    print(f"  - IP: {probe['ip']}")
    print(f"  - Interface: {probe['interface']}")
    print(f"  - Capture file: {probe['capture_file']}")
    print(f"  - Connessione: {probe['connection']}")
    print("\n✅ Probe configurato correttamente!")
else:
    print("\n❌ Probe non trovato nella topologia!")
    sys.exit(1)
PYEOF

# Esegui il test nel container
docker compose run --rm mininet python3 /tmp/test_probe_validator.py
