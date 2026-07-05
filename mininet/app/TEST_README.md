# Test Application per Implementations

🚀 **Applicazione Python completa per testare automaticamente implementazioni client/server**

## Quick Start

```bash
# Test tutte le implementazioni
python3 test_implementations.py

# Test una specifica
python3 test_implementations.py tcp_simple

# Lista implementazioni disponibili
python3 test_implementations.py --list

# Output verboso
python3 test_implementations.py -v
```

## File Creati

| File | Descrizione |
|------|-------------|
| `test_implementations.py` | ⭐ Main application - test runner completo |
| `test_utils.py` | 🔧 Funzioni utilità (check deps, ports, etc.) |
| `test_examples.py` | 📚 Esempi uso programmatico |
| `quick_test_implementations.sh` | 🚀 Script bash quick start |
| `test_config.json` | ⚙️ Configurazione parametri test |
| `TEST_APP_README.md` | 📖 Documentazione completa dettagliata |
| `QUICK_START.py` | ⚡ Guida rapida con esempi |

## Caratteristiche

✅ Test automatici di tutte le implementazioni  
✅ Verifica connettività server/client  
✅ Report dettagliato JSON + console  
✅ Output colorato e intuitivo  
✅ Uso programmatico o CLI  
✅ Parametri configurabili  
✅ Utilità per gestione dipendenze/porte  

## Implementazioni Testate

- **tcp_simple**: Socket TCP nativi Python
- **scapy_burst**: Burst ottimizzati con Scapy  
- **flow_emulator**: Emulazione con controllo statistiche

## Uso Avanzato

```python
# Import
from test_implementations import TestRunner, ImplementationTester

# Test tutte
runner = TestRunner(verbose=True)
runner.test_all()
runner.print_summary()

# Test singola con parametri custom
from pathlib import Path
tester = ImplementationTester("tcp_simple", Path("implementations/tcp_simple"))
tester.test_port = 8888
tester.test_duration = 10
result = tester.run_test()
```

## Utilità CLI

```bash
# Verifica dipendenze
python3 test_utils.py check-deps

# Installa dipendenze mancanti
python3 test_utils.py install-deps

# Lista implementazioni
python3 test_utils.py list-impls

# Verifica porta libera
python3 test_utils.py check-port --port 9000

# Uccidi processo su porta
python3 test_utils.py kill-port --port 9000

# Cleanup artefatti
python3 test_utils.py cleanup
```

## Output

```
============================================================
Testing: tcp_simple
============================================================

[INFO] File client.py e server.py trovati
[SUCCESS] Server avviato con successo (PID: 12345)
[INFO] Avvio client (durata: 5s)...
[SUCCESS] Client completato con successo

✓ tcp_simple: SUCCESSO

============================================================
RIEPILOGO TEST
============================================================

Totale: 3 | Passati: 3 | Falliti: 0

✓ flow_emulator      [files: ✓, server: ✓, client: ✓]
✓ scapy_burst        [files: ✓, server: ✓, client: ✓]
✓ tcp_simple         [files: ✓, server: ✓, client: ✓]

Risultati salvati in: test_results.json
```

## Troubleshooting

**Porta già in uso?**
```bash
python3 test_utils.py kill-port --port 9000
```

**Dipendenze mancanti?**
```bash
python3 test_utils.py install-deps --auto
```

**Permission denied (Scapy)?**
```bash
sudo python3 test_implementations.py  # Linux/Mac
```

## Documentazione

- 📖 **Dettagliata**: `TEST_APP_README.md`
- ⚡ **Quick Start**: `QUICK_START.py` 
- 📚 **Esempi**: `test_examples.py`

## Note

- Porta default: 9000
- Durata test: 5 secondi
- Timeout: 15 secondi
- Host: 127.0.0.1 (localhost)

Tutti i parametri sono configurabili in `test_config.json`

---

**Creato per**: FLow-Stealth-attack project  
**Scopo**: Testare implementazioni client/server in modo automatico e affidabile
