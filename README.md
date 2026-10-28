# 🚀 FASF - Flow Stealth Attack Simulation Framework

[![Docker](https://img.shields.io/badge/docker-ready-blue)]()
[![Mininet](https://img.shields.io/badge/network-mininet-orange)]()
[![Python](https://img.shields.io/badge/python-3.10+-green)]()
[![License](https://img.shields.io/badge/license-research-lightgrey)]()

---

## 📑 Table of Contents

1. [Overview](#-overview)
2. [Architecture](#-architecture)
3. [Project Structure](#-project-structure)
4. [Requirements](#-requirements)
5. [Quick Start Guide](#-quick-start-guide)
6. [Workflow Scripts](#-workflow-scripts)
7. [How It Works](#-how-it-works)
8. [Outputs](#-outputs)
9. [Advanced Usage](#-advanced-usage)
10. [Troubleshooting](#-troubleshooting)

---

## 🧠 Overview

**FASF** (Flow Stealth Attack Simulation Framework) è un framework completo per la simulazione e l'analisi di traffico di rete. 

**Funzionalità Principali**:
- 📊 **Generazione di topologie di rete** da file CSV di flussi
- 🔄 **Replicazione del traffico** usando Mininet e Docker
- 📈 **Estrazione di feature di flusso** con CICFlowMeter
- 🤖 **Ottimizzazione di parametri di simulazione** tramite Bayesian Optimization
- 📉 **Valutazione e confronto** di metriche di accuratezza

**Scopo**: Simulare attacchi di rete stealth generando traffico che riproduce flussi originali catturati in PCAP.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FASF Workflow                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input CSV (original flows)                                 │
│         ↓                                                    │
│  [1] Generate Topology → topology JSON                      │
│         ↓                                                    │
│  [2] Replicate Flows → Mininet simulation → PCAP           │
│         ↓                                                    │
│  [3] Regenerate Flows → CICFlowMeter → CSV features        │
│         ↓                                                    │
│  [4] Compare Flows → Flow comparison report                │
│         ↓                                                    │
│  [5] Optimize Simulation → Bayesian Optimization           │
│         ↓                                                    │
│  [6] Evaluate Results → Error metrics & charts             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
FASF/
├── 1.generate_topology.sh          ← Genera topologia di rete
├── 2.replicate_flow.sh              ← Esegue simulazione Mininet
├── 3.regenerate_flows.sh            ← Estrae feature con CICFlowMeter
├── 4.compare_flows.sh               ← Confronta flussi original vs regenerated
├── 5.optimize_flow_simulation.sh    ← Ottimizza parametri
├── 6.evaluate_optimization.sh       ← Valuta risultati
│
├── aggregate_bursts.sh              ← Aggrega file burst (utility)
├── compare_fin_flags.sh             ← Confronta flag FIN (debug tool)
│
├── docker-compose.yml               ← Configurazione Docker
│
├── mininet/                         ← Simulatore di rete
│   └── app/
│       ├── replay_topology.py       ← Orchestratore principale
│       ├── generate_initial_params.py
│       └── implementations/         ← Moduli di traffic generation
│           ├── scapy_burst/
│           ├── tcp_burst/
│           ├── flow_emulator/
│           └── ...
│
├── optimizer/                       ← Ottimizzatore Bayesian
│   └── app/
│       ├── traffic_optimizer.py
│       └── ...
│
├── evaluator/                       ← Valutazione e report
│   └── app/
│       ├── flow_compare_data.py     ← Calcola metriche di errore
│       ├── plot_key_feature_errors.py
│       ├── plot_optimization.py
│       └── ...
│
├── cicflowmeter/                    ← Estrazione di feature di flusso
│   └── CICFlowMeter binary
│
└── shared/
    ├── input_flows/                 ← File CSV originali
    │   ├── test1.csv
    │   ├── test2.csv
    │   └── ...
    ├── output_flows/                ← File CSV rigenerati
    │   ├── regenerated_test1_clean.csv
    │   └── ...
    ├── results/                     ← Output e report
    │   ├── test1/
    │   │   ├── report_data.json
    │   │   ├── report.html
    │   │   ├── test1_keyfeatures.png
    │   │   ├── test1_keyfeatures.csv
    │   │   └── ...
    │   └── ...
    ├── tmp/                         ← File intermedi
    │   ├── bidir_dataset_*.csv
    │   ├── burst_dataset_*.csv
    │   ├── flows_adapted_*.csv
    │   └── server_*.log
    │
    ├── pcap/                        ← File PCAP catturati
    │   ├── test1.pcap
    │   └── ...
    │
    └── topologies/                  ← Topologie generate
        ├── test1.csv.json
        └── ...
```

---

## ⚙️ Requirements

- **Docker + Docker Compose** (versione 20.10+)
- **Linux** (macOS supportato parzialmente)
- **RAM** ≥ 8GB (4GB minimo)
- **Spazio disco** ≥ 20GB
- **Python** 3.10+ (per script di supporto)

**Installazione Dipendenze**:

```bash
# Ubuntu/Debian
sudo apt-get install docker.io docker-compose python3 python3-pip

# macOS
brew install docker python@3.11

# Installa dipendenze Python locali
pip install numpy pandas scipy matplotlib
```

---

## 🚀 Quick Start Guide

### Opzione 1: Workflow Completo (Automatico)

```bash
# 1. Preparare un file CSV di test
cp shared/input_flows/test6.csv shared/input_flows/mytest.csv

# 2. Eseguire l'intero workflow
bash 1.generate_topology.sh mytest
bash 2.replicate_flow.sh mytest
bash 3.regenerate_flows.sh mytest
bash 4.compare_flows.sh mytest
```

### Opzione 2: Workflow con Ottimizzazione

```bash
# Esegui i primi 4 step, poi ottimizza
bash 1.generate_topology.sh mytest
bash 2.replicate_flow.sh mytest
bash 3.regenerate_flows.sh mytest
bash 4.compare_flows.sh mytest
bash 5.optimize_flow_simulation.sh mytest   # (Opzionale, lungo ~1h)
bash 6.evaluate_optimization.sh mytest
```

### Opzione 3: Solo Confronto e Valutazione

Se hai già il PCAP catturato:

```bash
bash 3.regenerate_flows.sh mytest
bash 4.compare_flows.sh mytest
bash 6.evaluate_optimization.sh mytest
```

---

## 📜 Workflow Scripts

### 🔹 1.generate_topology.sh
**Scopo**: Generare la topologia di rete da un file CSV di flussi

**Uso**:
```bash
./1.generate_topology.sh <test_name>
```

**Parametri**:
- `<test_name>`: Nome del file CSV (senza estensione)
  - Es: `test6` → legge `shared/input_flows/test6.csv`

**Output**:
- `shared/topologies/test6.csv.json` - Topologia di rete in formato JSON

**Dettagli**:
- Analizza il file CSV per identificare host, switch e connessioni
- Genera una topologia Mininet compatibile
- Estrae parametri di timing (timeout, dimensioni pacchetti, etc.)

**Esempio**:
```bash
./1.generate_topology.sh test6
# Output: 📂 Analisi del file: input_flows/test6.csv
#         📝 Output: topologies/test6.csv.json
```

---

### 🔹 2.replicate_flow.sh
**Scopo**: Eseguire la simulazione del traffico con Mininet e catturare il PCAP

**Uso**:
```bash
./2.replicate_flow.sh <test_name> [implementation]
```

**Parametri**:
- `<test_name>`: Nome del test (es: `test6`)
- `[implementation]` (opzionale, default: `scapy_burst`):
  - `scapy_burst` - Usa Scapy per generare pacchetti
  - `tcp_burst` - Usa socket TCP raw
  - `tcp_simple` - Implementazione TCP semplificata
  - `bidirectional` - Simula flussi bidirezionali
  - `flow_emulator` - Emulatore generico di flussi
  - `optimizable` / `optimizable2` - Versioni ottimizzabili

**Output**:
- `shared/pcap/test6.pcap` - File PCAP catturato
- `shared/results/tmp/server_*.log` - Log del server di simulazione

**Dettagli**:
- Legge la topologia generata dal passo 1
- Avvia container Docker con Mininet
- Genera traffico seguendo i parametri del CSV
- Cattura il traffico in formato PCAP
- Dura tipicamente 10-30 secondi per test

**Esempio**:
```bash
./2.replicate_flow.sh test6 scapy_burst
# Output: Mininet running...
#         PCAP capture: shared/pcap/test6.pcap
```

**Note**:
- Richiede Docker e spazio su disco disponibile
- Il tempo di esecuzione dipende dalla durata dei flussi nel CSV

---

### 🔹 3.regenerate_flows.sh
**Scopo**: Estrarre le feature di flusso dal PCAP usando CICFlowMeter

**Uso**:
```bash
./3.regenerate_flows.sh <test_name>
```

**Parametri**:
- `<test_name>`: Nome del test

**Output**:
- `shared/output_flows/regenerated_test6_clean.csv` - Feature estratte dal PCAP

**Dettagli**:
- Legge il file PCAP generato dal passo 2
- Esegue CICFlowMeter per estrarre 87 feature di flusso
- Pulisce i dati rimuovendo intestazioni e flussi non validi
- Produce un CSV con stesso formato dell'input

**Esempio**:
```bash
./3.regenerate_flows.sh test6
# Output: Processing PCAP...
#         Generated: shared/output_flows/regenerated_test6_clean.csv
```

---

### 🔹 4.compare_flows.sh
**Scopo**: Confrontare i flussi originali con i flussi rigenerati e calcolare metriche di errore

**Uso**:
```bash
./4.compare_flows.sh <test_name>
```

**Parametri**:
- `<test_name>`: Nome del test

**Output**:
- `shared/results/test6/report_data.json` - Report strutturato con metriche
- `shared/results/test6/report.html` - Report HTML interattivo

**Dettagli**:
- Esegue il matching tra flussi originali e rigenerati
- Calcola per ogni flusso e ogni feature:
  - Errore assoluto (MAE)
  - Errore relativo (%)
  - Errore con segno
- Genera statistiche aggregate per feature
- Identifica flussi mancanti e extra

**Metriche Calcolate**:
- **Mean Absolute Error (MAE)**: Differenza media in valore assoluto
- **Mean Relative Error (%)**: Differenza percentuale
- **Feature Groups**: TCP flags, timing, packet sizes, throughput, etc.

**Esempio**:
```bash
./4.compare_flows.sh test6
# Output: ✅ Dati elaborati. Generato: results/test6/report_data.json
#         ✅ Report HTML statico generato con successo
```

---

### 🔹 5.optimize_flow_simulation.sh
**Scopo**: Ottimizzare i parametri di simulazione usando Bayesian Optimization

**Uso**:
```bash
./5.optimize_flow_simulation.sh <test_name> [max_trials]
```

**Parametri**:
- `<test_name>`: Nome del test
- `[max_trials]` (opzionale, default: 3): Numero massimo di trial

**Output**:
- `optimizer_state/<test_name>/trials.jsonl` - Cronologia dei trial
- `shared/results/test6/optimization_progress.png` - Grafico del progresso
- `shared/results/test6/optimization_summary.json` - Sommario risultati

**Dettagli**:
- Esegue ottimizzazione Bayesian tramite biblioteca Python `optuna`
- Varia parametri come timeout, velocità trasmissione, dimensioni pacchetti
- Per ogni trial esegue steps 2-4 (replicate, regenerate, compare)
- Calcola score di fitness basato su errore medio
- Trova i parametri che minimizzano l'errore

**Parametri Ottimizzati**:
- Timeout simulazione
- Flow inter-packet timing
- Packet size distribution
- TCP window size
- Retransmission timing

**Tempo di Esecuzione**: 
- ~5-10 minuti per trial
- 3 trial = ~20-30 minuti
- Consigliato: 10-20 trial per risultati migliori

**Esempio**:
```bash
./5.optimize_flow_simulation.sh test6 5
# Output: Trial 1/5 → Score: 15.32
#         Trial 2/5 → Score: 14.87
#         Trial 3/5 → Score: 14.92
#         Trial 4/5 → Score: 14.56 ← BEST
#         Trial 5/5 → Score: 14.98
#         Optimization complete!
```

---

### 🔹 6.evaluate_optimization.sh
**Scopo**: Generare report di valutazione e grafici delle metriche

**Uso**:
```bash
./6.evaluate_optimization.sh <test_name>
```

**Parametri**:
- `<test_name>`: Nome del test

**Output**:
- `shared/results/test6/test6_keyfeatures.png` - Grafico a barre delle feature principali
- `shared/results/test6/test6_keyfeatures.csv` - CSV con errori per feature
- `shared/results/test6/optimization_*.png` - Grafici di ottimizzazione

**Dettagli**:
- Legge il report_data.json generato dal passo 4
- Seleziona le 24 feature chiave dell'objective function
- Calcola l'errore relativo medio per feature
- Genera visualizzazioni grafiche
- Esporta dati in CSV per analisi esterna

**Feature Principali Monitorate**:
- Flow Duration, Flow Bytes/s
- Fwd/Bwd Packet Length (Max, Min, Std)
- TCP Flags Count (FIN, SYN, RST, ACK)
- Active/Idle Time
- Retransmission Count
- Down/Up Ratio

**Soglia di Errore Accettabile**: < 20%

**Esempio**:
```bash
./6.evaluate_optimization.sh test6
# Output: Saved figure: results/test6/test6_keyfeatures.png
#         Saved data:   results/test6/test6_keyfeatures.csv
```

---

## 🛠️ Utility Scripts

### aggregate_bursts.sh
**Scopo**: Aggregare tutti i file burst_dataset_*.csv in un unico file

**Uso**:
```bash
./aggregate_bursts.sh <test_name>
```

**Output**:
- `shared/results/burst_dataset_<test_name>_complete.csv`

---

### compare_fin_flags.sh
**Scopo**: Debug tool per confrontare i flag FIN tra file originale e rigenerato

**Uso**:
```bash
./compare_fin_flags.sh
```

**Output**: Tabella con confronto dei FIN flag count

---

## 🔄 How It Works

### Passo 1: Generazione Topologia
```
Input: test6.csv (87 feature, N flussi)
  ↓
Analizza IP sorgente/destinazione
  ↓
Crea grafo di connettività
  ↓
Output: test6.csv.json (topologia Mininet)
```

### Passo 2: Replica Traffico
```
Input: test6.csv.json (topologia)
  ↓
Avvia Mininet container
  ↓
Per ogni flusso del CSV:
  - Crea host sorgente/destinazione
  - Configura routing
  - Genera traffico (TCP/UDP)
  - Replica timing e dimensioni pacchetti
  ↓
Probe cattura PCAP
  ↓
Output: test6.pcap
```

### Passo 3: Estrazione Feature
```
Input: test6.pcap
  ↓
CICFlowMeter analizza pacchetti
  ↓
Per ogni flusso:
  - Calcola 87 feature (duration, size, rate, flags, etc.)
  - Aggrega statistiche
  ↓
Output: regenerated_test6_clean.csv
```

### Passo 4: Confronto Flussi
```
Input: test6.csv + regenerated_test6_clean.csv
  ↓
Matching flussi (4-tuple: src_ip, src_port, dst_ip, dst_port)
  ↓
Per ogni feature:
  - Calcola MAE (errore assoluto)
  - Calcola errore relativo (%)
  ↓
Output: report_data.json
```

### Passo 5: Ottimizzazione
```
Input: report_data.json (score iniziale)
  ↓
Bayesian Optimization loop (N trial):
  1. Suggerisci nuovi parametri
  2. Esegui replica con nuovi parametri (passi 2-4)
  3. Calcola nuovo score
  4. Aggiorna modello bayesian
  ↓
Output: trial_*.json + miglior parametri
```

### Passo 6: Valutazione
```
Input: report_data.json
  ↓
Seleziona 24 feature chiave
  ↓
Calcola errore relativo per feature
  ↓
Genera grafici + CSV
  ↓
Output: test6_keyfeatures.png, test6_keyfeatures.csv
```

---

## 📊 Outputs

### Report Data (`report_data.json`)
Contiene:
- `metadata`: Conteggi di flussi matched/missing/extra
- `summary`: Aggregazione errori per feature
- `flow_details`: Dettagli errore per ogni flusso/feature
- `missing_flows`: Flussi presenti solo nel CSV originale
- `extra_flows`: Flussi presenti solo nel PCAP rigenerato

### Key Features CSV (`test6_keyfeatures.csv`)
Formato:
```
feature,label,mean_relative_error_pct,missing_or_null
"FIN Flag Count","FIN count",43.18,false
"SYN Flag Count","SYN count",37.50,false
...
```

### Report HTML (`report.html`)
Interfaccia interattiva per:
- Visualizzare flussi matched/missing
- Esplorare dettagli errore per feature
- Scaricare dati di debug

---

## 🔬 Advanced Usage

### Eseguire una Simulazione Custom

```bash
# Creare file CSV custom
cat > shared/input_flows/myflow.csv << 'EOF'
Src IP,Src Port,Dst IP,Dst Port,Protocol,Duration,... (87 feature totali)
192.168.1.100,1234,8.8.8.8,80,TCP,5.2,...
EOF

# Eseguire workflow
bash 1.generate_topology.sh myflow
bash 2.replicate_flow.sh myflow tcp_simple
bash 3.regenerate_flows.sh myflow
bash 4.compare_flows.sh myflow
bash 6.evaluate_optimization.sh myflow
```

### Usare Implementazione Custom

```bash
# Creare nuovo modulo in mininet/app/implementations/my_impl/
# Implementare client.py e server.py
# Eseguire con:
bash 2.replicate_flow.sh test6 my_impl
```

### Analizzare Report JSON

```bash
# Leggere report
python3 << 'EOF'
import json

with open('shared/results/test6/report_data.json') as f:
    report = json.load(f)

# Statistiche metadata
print(f"Flussi matched: {report['metadata']['matched_count']}")
print(f"Flussi missing: {report['metadata']['missing_count']}")

# Errori per feature
for item in report['summary']:
    feature = item['feature']
    error = item['mean_relative_error_pct']
    print(f"{feature}: {error:.2f}%")
EOF
```

---

## 🐛 Troubleshooting

### Errore: Docker non trovato
```bash
# Installare Docker
sudo apt-get install docker.io docker-compose

# Avviare il servizio
sudo systemctl start docker

# Aggiungere user al gruppo docker
sudo usermod -aG docker $USER
newgrp docker
```

### Errore: "Memoria insufficiente"
```bash
# Aumentare RAM disponibile a Docker
# In Docker Desktop settings: Resources → Memory → 8GB+

# Oppure ridurre numero di flussi nel CSV
```

### Errore: "PCAP file not found"
```bash
# Verificare che passo 2 (replicate) sia completato
ls -la shared/pcap/test6.pcap

# Se manca, re-eseguire:
bash 2.replicate_flow.sh test6
```

### Errore: "CICFlowMeter timeout"
```bash
# Aumentare timeout in 3.regenerate_flows.sh
# Oppure ridurre dimensione del PCAP
```

### Come debuggare un Flusso Specifico
```bash
# Visualizzare il flusso nel report JSON
python3 << 'EOF'
import json

with open('shared/results/test6/report_data.json') as f:
    report = json.load(f)

# Cercare flusso specifico
target = "192.168.1.100:1234→8.8.8.8:80"

for detail in report['flow_details']:
    flow_key = f"{detail['Src IP']}:{detail['Src Port']}→{detail['Dst IP']}:{detail['Dst Port']}"
    if flow_key == target:
        feature = detail['feature']
        orig = detail['original_value']
        sim = detail['simulated_value']
        error = detail['relative_error_pct']
        print(f"{feature}: {orig} → {sim} (error: {error:.2f}%)")
EOF
```

---

## 📝 File Format Specifications

### Input CSV (shared/input_flows/test6.csv)
- **Formato**: CSV con header
- **Colonne**: 87 feature di CICFlowMeter
- **Identificazione Flusso**: Src IP, Src Port, Dst IP, Dst Port
- **Tipo Dati**: Numerico, stringhe IP
- **Righe**: Una per flusso

**Colonne Critiche**:
- `Src IP`, `Src Port`, `Dst IP`, `Dst Port` - Identificazione flusso
- `Protocol` - TCP/UDP
- `Duration` - Tempo di simulazione (secondi)
- `Total Fwd Packet` - Numero pacchetti in avanti
- `Total Length of Fwd Packet` - Byte totali inviati
- `FIN Flag Count` - Numero di flag FIN
- ... (altre 80 feature)

### Topology JSON (shared/topologies/test6.csv.json)
```json
{
  "hosts": [
    {"name": "h1", "ip": "192.168.1.100"},
    ...
  ],
  "links": [
    {"h1": "s1", "h2": "s1"},
    ...
  ],
  "flows": [...]
}
```

### Report JSON (shared/results/test6/report_data.json)
Struttura gerarchica con:
- Metadata (conteggi)
- Summary aggregato per feature
- Detail per flow/feature
- Missing/Extra flows

---

## 🎯 Workflow Recommendations

### Per Nuovi Utenti
```bash
# Start semplice con dataset piccolo
bash 1.generate_topology.sh test1
bash 2.replicate_flow.sh test1
bash 3.regenerate_flows.sh test1
bash 4.compare_flows.sh test1
bash 6.evaluate_optimization.sh test1
```

### Per Produzione
```bash
# Workflow completo con ottimizzazione
for test in test1 test2 test3; do
  bash 1.generate_topology.sh $test
  bash 2.replicate_flow.sh $test scapy_burst
  bash 3.regenerate_flows.sh $test
  bash 4.compare_flows.sh $test
  bash 5.optimize_flow_simulation.sh $test 10  # 10 trial
  bash 6.evaluate_optimization.sh $test
done
```

### Per Testing di Implementazioni
```bash
# Testare diversi moduli di traffic generation
for impl in scapy_burst tcp_simple flow_emulator; do
  bash 2.replicate_flow.sh test6 $impl
  bash 3.regenerate_flows.sh test6
  bash 4.compare_flows.sh test6
  echo "Implementation $impl: $(grep 'mean_relative_error' shared/results/test6/test6_keyfeatures.csv | head -1)"
done
```

---

## 📌 Recent Fixes & Improvements

### Fix: FIN Flag Count Error Calculation
- **Issue**: Errore relativo = 100% per FIN Flag Count
- **Cause**: Formula div-by-zero quando original=0
- **Fix**: Gestire caso di original=0 separatamente
- **Result**: Errore corretto a 43.18% (valutazione realistica)
- **Commit**: 39ef8fa, 273d3d7

### Fix: Duplicate 4-Tuple Handling
- **Issue**: Flussi duplicati con stesso IP pair ma port/timing diversi
- **Fix**: Usare 4-tuple completa (src_ip, src_port, dst_ip, dst_port)
- **Result**: Corretta replicazione di 45 flow in test6 (vs 39 prima)
- **Commit**: 7d36259

---

## 📌 Support & Documentation

- **Bug Reports**: Apri issue in questo repo
- **Feature Requests**: Discussioni nella sezione Projects
- **Documentation**: Vedi `doc/` per approfondimenti tecnici
- **Examples**: `shared/input_flows/test*.csv` per esempi di formato

---

## 📄 License

Research project - Università

---

## ✍️ Authors

- Massimiliano Rak
- Copilot AI (Documentation & Code Review)

---

**Last Updated**: 2026-10-28
**Version**: 2.0 (Architecture Redesign)
