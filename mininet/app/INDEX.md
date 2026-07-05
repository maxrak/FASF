# Applicazione di Test - File Creati

## 📁 File Principali

### 1. `test_implementations.py` ⭐
**Main application - Test runner completo**

- Classe `ImplementationTester`: Testa singola implementazione
- Classe `TestRunner`: Gestisce tutti i test
- Features:
  - Test automatici di client/server
  - Verifica connettività
  - Report JSON e console
  - Output colorato
  - Exit code per CI/CD

**Uso:**
```bash
python3 test_implementations.py              # Testa tutte
python3 test_implementations.py tcp_simple   # Testa una
python3 test_implementations.py --list       # Lista disponibili
python3 test_implementations.py -v           # Verboso
```

---

### 2. `test_utils.py` 🔧
**Funzioni utilità helper**

Features:
- `check_port_available()`: Verifica porta libera
- `kill_process_on_port()`: Uccidi processo su porta
- `get_free_port()`: Trova porta libera
- `check_dependencies()`: Verifica dipendenze Python
- `install_missing_dependencies()`: Installa dipendenze
- `list_implementations()`: Lista implementazioni
- `print_implementations_table()`: Tabella formattata
- `cleanup_test_artifacts()`: Pulisci file test

**Uso:**
```bash
python3 test_utils.py check-deps              # Verifica dipendenze
python3 test_utils.py install-deps            # Installa dipendenze
python3 test_utils.py list-impls              # Lista implementazioni
python3 test_utils.py check-port --port 9000  # Verifica porta
python3 test_utils.py kill-port --port 9000   # Uccidi processo
python3 test_utils.py cleanup                 # Pulisci artefatti
```

---

### 3. `test_examples.py` 📚
**Esempi uso programmatico**

Esempi inclusi:
- `test_custom_parameters()`: Parametri personalizzati
- `test_selective_implementations()`: Test selettivo
- `analyze_results()`: Analisi risultati JSON
- `custom_test_logic()`: Logica personalizzata

**Uso:**
```bash
python3 test_examples.py  # Esegue tutti gli esempi
```

**Import:**
```python
from test_implementations import TestRunner, ImplementationTester

runner = TestRunner(verbose=True)
runner.test_all()
```

---

### 4. `test_demo.py` 🎨
**Demo completa di tutte le funzionalità**

Mostra:
1. Verifica dipendenze
2. Implementazioni disponibili
3. Check porte
4. Configurazione
5. Comandi disponibili
6. Workflow tipico
7. Features principali
8. Struttura file

**Uso:**
```bash
python3 test_demo.py  # Demo completa
```

---

### 5. `quick_test_implementations.sh` 🚀
**Script bash per quick start**

Features:
- Verifica Python3 installato
- Check dipendenze automatico
- Propone installazione se mancanti
- Esegue test
- Report colorato

**Uso:**
```bash
./quick_test_implementations.sh                # Test tutte
./quick_test_implementations.sh tcp_simple     # Test una
./quick_test_implementations.sh -v             # Verboso
```

---

### 6. `test_config.json` ⚙️
**File configurazione parametri test**

Sezioni:
- `test_config`: Porta, durata, timeout, host
- `implementations`: Configurazione per implementazione
- `output`: Configurazione output (verbose, JSON, colori)
- `advanced`: Opzioni avanzate (parallel, retry)

**Esempio:**
```json
{
  "test_config": {
    "port": 9000,
    "duration": 5,
    "timeout_multiplier": 2.0,
    "localhost": "127.0.0.1"
  },
  "implementations": {
    "tcp_simple": {
      "enabled": true,
      "description": "Socket TCP nativi Python"
    }
  }
}
```

---

## 📖 Documentazione

### 7. `TEST_README.md`
**README compatto - Quick reference**

- Quick start comandi
- Features principali
- Troubleshooting
- Output esempi
- 1-2 pagine, veloce consultazione

---

### 8. `TEST_APP_README.md`
**Documentazione completa dettagliata**

- Descrizione completa caratteristiche
- Uso dettagliato
- Parametri configurazione
- Formato JSON risultati
- Troubleshooting approfondito
- Estendibilità
- 5+ pagine, riferimento completo

---

### 9. `QUICK_START.py`
**Guida rapida con esempi**

Sezioni:
- Installazione e setup
- Uso rapido
- Uso programmatico
- Personalizzazione
- Struttura file
- Troubleshooting
- Esempi avanzati
- Integrazione CI/CD
- Best practices

**Uso:**
```bash
python3 QUICK_START.py  # Mostra guida
```

---

### 10. `INDEX.md` (questo file)
**Indice completo di tutti i file**

---

## 📊 Output Generati

### `test_results.json`
**File JSON con risultati test** (generato automaticamente)

Struttura:
```json
{
  "timestamp": "2026-07-05 15:30:45",
  "total": 3,
  "passed": 2,
  "failed": 1,
  "results": [
    {
      "name": "tcp_simple",
      "success": true,
      "stages": {
        "files_check": true,
        "server_start": true,
        "client_run": true
      },
      "error": null,
      "client_output": "..."
    }
  ]
}
```

---

## 🗂️ Struttura Directory

```
mininet/app/
├── test_implementations.py          ⭐ Main application
├── test_utils.py                    🔧 Utility functions
├── test_examples.py                 📚 Programmatic examples
├── test_demo.py                     🎨 Feature demonstration
├── quick_test_implementations.sh    🚀 Bash quick start
├── test_config.json                 ⚙️ Configuration file
├── TEST_README.md                   📖 Quick reference
├── TEST_APP_README.md               📖 Complete documentation
├── QUICK_START.py                   ⚡ Quick start guide
├── INDEX.md                         📑 This file
├── test_results.json                📊 Generated results (auto)
└── implementations/                 📁 Implementations to test
    ├── tcp_simple/
    │   ├── client.py
    │   ├── server.py
    │   └── README.md
    ├── scapy_burst/
    │   ├── client.py
    │   ├── server.py
    │   └── README.md
    └── flow_emulator/
        ├── client.py
        ├── server.py
        └── README.md
```

---

## 🎯 Quick Reference

### Test Comandi Base
```bash
# Lista implementazioni
python3 test_implementations.py --list

# Test singola
python3 test_implementations.py tcp_simple -v

# Test tutte
python3 test_implementations.py

# Script bash (auto check deps)
./quick_test_implementations.sh
```

### Utility Comandi
```bash
# Check dipendenze
python3 test_utils.py check-deps

# Lista implementazioni (tabella)
python3 test_utils.py list-impls

# Verifica porta
python3 test_utils.py check-port --port 9000

# Cleanup
python3 test_utils.py cleanup
```

### Demo e Esempi
```bash
# Demo completa
python3 test_demo.py

# Esempi programmatici
python3 test_examples.py

# Guida quick start
python3 QUICK_START.py
```

---

## 📝 Note

- **Dipendenze principali**: scapy, pandas, numpy
- **Dipendenza opzionale**: psutil (per kill process)
- **Porta default**: 9000
- **Durata test**: 5 secondi
- **Host**: 127.0.0.1 (localhost)

---

## 🔗 Navigazione Documentazione

| Per... | Leggi... |
|--------|----------|
| Quick start | TEST_README.md |
| Documentazione completa | TEST_APP_README.md |
| Guida rapida esempi | QUICK_START.py |
| Panoramica file | INDEX.md (questo) |
| Demo funzionalità | Esegui test_demo.py |
| Esempi codice | Esegui test_examples.py |

---

## ✅ Checklist Inizio

- [ ] Leggi TEST_README.md
- [ ] Esegui `python3 test_demo.py` per vedere features
- [ ] Verifica dipendenze: `python3 test_utils.py check-deps`
- [ ] Lista implementazioni: `python3 test_implementations.py --list`
- [ ] Primo test: `python3 test_implementations.py tcp_simple -v`
- [ ] Test completo: `python3 test_implementations.py`
- [ ] Analizza risultati: `cat test_results.json`

---

**Creato per**: FLow-Stealth-attack project  
**Data**: 2026-07-05  
**Versione**: 1.0
