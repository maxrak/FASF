# 🔐 FASF - Flow Stealth Attack Simulation Framework

> **Replica flussi di traffico da dati reali in ambienti di simulazione Mininet con precisione scientifica**

Un framework completo per generare, replicare e analizzare flussi di rete in una topologia simulata, misurandone l'accuratezza attraverso metriche statistiche (87 feature CICFlowMeter).

---

## ✨ Che Cos'è FASF?

FASF è un **framework di simulazione scientifica** che permette di:

- 📊 **Partire da dati reali**: CSV con flussi di rete (IP, porte, durata, byte, packet)
- 🎭 **Generare topologie**: Crea una rete simulata con Docker e Mininet
- 🔄 **Replicare flussi**: Esegue lo stesso traffico nella rete simulata
- 📈 **Misurare accuratezza**: Confronta flussi originali vs simulati (MAE, MRE, feature-by-feature)
- 🤖 **Ottimizzare parametri**: Usa Bayesian Optimization per minimizzare l'errore
- 📋 **Generare report**: Produce grafici, tabelle e metriche dettagliate

**Caso d'uso**: Verificare se una simulazione Mininet può riprodurre il traffico di attacchi di rete reali con sufficiente fedeltà.

---

## 🚀 Quick Start (5 minuti)

### Installazione

```bash
# Clona il repository
git clone https://github.com/maxrak/FLow-Stealth-attack.git
cd FLow-Stealth-attack

# Installa dipendenze (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y docker.io mininet openvswitch-switch

# Oppure su macOS (con Homebrew)
brew install docker docker-compose mininet

# Avvia Docker
sudo systemctl start docker
# o su macOS
open /Applications/Docker.app
```

### Esecuzione del Workflow Standard (4 step)

```bash
# 1. Genera topologia da CSV
./1.generate_topology.sh test6

# 2. Replica flussi in Mininet
./2.replicate_flow.sh test6

# 3. Estrai feature dalla simulazione
./3.regenerate_flows.sh test6

# 4. Confronta risultati
./4.compare_flows.sh test6

# Visualizza risultati
cat shared/results/test6/test6_keyfeatures.csv
open shared/results/test6/test6_keyfeatures.png  # macOS
xdg-open shared/results/test6/test6_keyfeatures.png  # Linux
```

---

## 📁 Struttura del Progetto

```
FASF/
├── README.md                          ← Sei qui!
├── doc/                               ← 📚 Documentazione HTML
│   ├── index.html                     (Indice principale)
│   ├── readme.html                    (Guida completa)
│   ├── quick-reference.html           (Comandi veloci)
│   └── architecture.html              (Diagrammi e architettura)
├── 1.generate_topology.sh             ← Step 1: Genera topologia
├── 2.replicate_flow.sh                ← Step 2: Replica flussi
├── 3.regenerate_flows.sh              ← Step 3: Estrai feature
├── 4.compare_flows.sh                 ← Step 4: Confronta
├── 5.optimize_flow_simulation.sh      ← Step 5: Ottimizza (opzionale)
├── 6.evaluate_optimization.sh         ← Step 6: Valuta (opzionale)
├── shared/
│   ├── dataset/                       (Dataset in input)
│   ├── results/                       (Risultati in output)
│   └── docker/                        (Container e immagini)
└── src/                               (Codice Python)
    ├── topology.py
    ├── replicator/
    ├── feature_extractor/
    ├── optimizer/
    └── utils/
```

---

## 📋 I 6 Step del Workflow

| Step | Script | Input | Cosa Fa | Output | Tempo |
|------|--------|-------|---------|--------|-------|
| 1️⃣ | `1.generate_topology.sh` | CSV flows | Crea topologia JSON e Docker setup | `topology.json`, `docker-compose.yml` | 1-2 min |
| 2️⃣ | `2.replicate_flow.sh` | Topologia | Esegue flussi in Mininet | `traffic.pcap` | 5-30 min |
| 3️⃣ | `3.regenerate_flows.sh` | PCAP | Estrae 87 feature con CICFlowMeter | `regenerated_flows.csv` | 2-5 min |
| 4️⃣ | `4.compare_flows.sh` | CSV originale + rigenerate | Calcola errori e metriche | `keyfeatures.csv`, grafici PNG | 1 min |
| 5️⃣ | `5.optimize_flow_simulation.sh` | Risultati + parametri | Bayesian Optimization (iterativo) | `optimization_log.json` | 30+ min |
| 6️⃣ | `6.evaluate_optimization.sh` | Optimization results | Genera report finale | `optimization_report.html` | 2 min |

**Workflow minimo**: 1 → 2 → 3 → 4 (40-45 minuti)  
**Workflow completo**: 1 → 2 → 3 → 4 → 5 → 6 (90+ minuti con ottimizzazione)

---

## 📚 Documentazione

### 🎯 Come Iniziare

Ci sono **3 livelli di documentazione**:

| Se sei... | Leggi... | Perché |
|-----------|----------|--------|
| **Nuovo** | [doc/index.html](doc/index.html) | Indice + guida per navigare |
| **Impaziente** | [doc/quick-reference.html](doc/quick-reference.html) | Comandi esatti, copia-incolla |
| **Curioso** | [doc/readme.html](doc/readme.html) | Guida completa con esempi |
| **Tecnico** | [doc/architecture.html](doc/architecture.html) | Diagrammi, dettagli, CICFlowMeter |

### 📖 Contenuti della Documentazione

- ✅ Descrizione dettagliata di **ogni script** (cosa fa, come usarlo, parametri, output)
- ✅ **3 workflow diversi** (basic, advanced, optimization)
- ✅ **Formati dati**: CSV input, JSON topology, PCAP binary, CSV output
- ✅ **Metriche**: Come si calcolano MAE, MRE, feature-specific error
- ✅ **Troubleshooting**: Errori comuni e soluzioni
- ✅ **Diagrammi**: Workflow pipeline, data transformations, architecture
- ✅ **87 Feature CICFlowMeter**: Cosa rappresentano, come vengono calcolate
- ✅ **Bayesian Optimization**: Come migliora i parametri

---

## 💻 Prerequisiti

### Sistemi Supportati
- **Linux**: Ubuntu 20.04+ / Debian 11+
- **macOS**: 10.15+ (con Docker Desktop)
- **Windows**: WSL2 + Docker Desktop

### Requisiti Software
- Docker / Docker Desktop
- Python 3.8+
- Mininet (incluso in Docker)
- CICFlowMeter (incluso in Docker)
- Pandoc (per documentazione HTML)

### Spazio Disco Necessario
- **Minimo**: 5 GB (base + piccoli dataset)
- **Consigliato**: 20+ GB (per optimize con molte iterazioni)
- **Temp files**: ~2 GB durante l'esecuzione (in `shared/results/tmp/`)

---

## 🎯 Casi d'Uso

### 1. **Test Singolo Dataset**
```bash
./1.generate_topology.sh mydata
./2.replicate_flow.sh mydata
./3.regenerate_flows.sh mydata
./4.compare_flows.sh mydata
# Risultati in shared/results/mydata/
```

### 2. **Test Multipli Dataset**
```bash
for dataset in test1 test2 test3; do
  ./1.generate_topology.sh $dataset
  ./2.replicate_flow.sh $dataset
  ./3.regenerate_flows.sh $dataset
  ./4.compare_flows.sh $dataset
done
```

### 3. **Ottimizzazione Parametri**
```bash
# Run una volta il workflow standard
./1.generate_topology.sh mydata
./2.replicate_flow.sh mydata
./3.regenerate_flows.sh mydata
./4.compare_flows.sh mydata

# Poi ottimizza iterativamente
./5.optimize_flow_simulation.sh mydata 10  # 10 trial
./6.evaluate_optimization.sh mydata
```

---

## 📊 Output Atteso

Dopo `./4.compare_flows.sh mydata`, troverai:

```
shared/results/mydata/
├── mydata_keyfeatures.csv          ← Errori per ogni feature
├── mydata_keyfeatures.png          ← Grafico errori
├── mydata_comparison.json          ← Statistiche dettagliate
├── mydata_flow_details.csv         ← Errori per singolo flusso
└── mydata_error_summary.txt        ← Riepilogo risultati
```

### Interpretare i Risultati

**`mydata_keyfeatures.csv`** contiene errori MAE e MRE per ogni feature:
- MAE (Mean Absolute Error): Differenza media assoluta
- MRE (Mean Relative Error %): Errore relativo percentuale

**`mydata_comparison.json`** ha statistiche complete:
```json
{
  "overall_mae": 12.34,
  "overall_mre": 8.5,
  "features": {
    "duration": {"mae": 0.5, "mre": 2.1},
    "total_fwd_packets": {"mae": 5.2, "mre": 15.3},
    ...
  }
}
```

---

## 🐛 Troubleshooting

### Docker non si avvia
```bash
# Linux
sudo systemctl start docker
sudo usermod -aG docker $USER

# macOS
open /Applications/Docker.app
```

### Errore: "Permission denied" su file results
```bash
sudo chown -R $USER:$USER shared/results/
```

### Simulazione troppo lenta
- Riduci il numero di flussi nel CSV input
- Usa `--timeout 60` in `2.replicate_flow.sh`
- Disabilita feature non necessarie

### Errore: "No such file or directory: topology.json"
```bash
# Assicurati di aver eseguito step 1 prima di step 2
ls shared/results/mydata/topology.json
```

Per altri problemi, vedi [doc/readme.html](doc/readme.html#troubleshooting)

---

## 📞 Help e Supporto

Ogni script ha un help integrato:
```bash
./1.generate_topology.sh --help
./2.replicate_flow.sh --help
# etc.
```

Per debug dettagliato, vedi i log:
```bash
tail -f shared/results/mydata/mydata.log
```

---

## 📝 Formato Dataset Input

Il CSV input deve avere una riga per flusso con queste colonne:

```csv
src_ip,src_port,dst_ip,dst_port,protocol,duration,total_fwd_packets,total_bwd_packets,totlen_fwd_packets,totlen_bwd_packets,min_fwd_packet_length,max_fwd_packet_length,min_bwd_packet_length,max_bwd_packet_length,...
192.168.1.1,5000,192.168.1.2,80,TCP,10.5,45,23,2048,1024,44,512,52,256,...
```

Total: **87 colonne** (standard CICFlowMeter)

Vedi [doc/readme.html](doc/readme.html#file-format) per il elenco completo delle colonne.

---

## 🔑 Concetti Chiave

### 🎯 4-Tuple Flow Identification
I flussi sono identificati univocamente dal **4-tuple**:
- `src_ip` + `src_port` + `dst_ip` + `dst_port`

**Importante**: Due flussi con le stesse IP ma porte diverse sono **flussi completamente diversi**!

### 📊 87 CICFlowMeter Features
Il framework estrae 87 feature statistiche da ogni flusso PCAP:
- Temporali: `duration`, `active_time`, `idle_time`
- Volume: `total_fwd_packets`, `total_bwd_packets`, byte lengths
- TCP Flags: `fwd_urg_flags`, `fwd_fin_flags`, `fwd_syn_flags`, `fwd_rst_flags`, `fwd_ack_flags`, etc.
- Statistiche: `avg_packet_length`, `std_packet_length`, throughput, retransmission ratio

Vedi [doc/architecture.html#feature-calculation](doc/architecture.html#feature-calculation) per i dettagli.

### 🤖 Bayesian Optimization
Step 5 ottimizza **4 parametri di simulazione**:
1. `timeout`: Tempo di attesa per flussi idle
2. `pkt_interval_delay`: Ritardo tra pacchetti
3. `payload_size_distribution`: Distribuzione grandezza payload
4. `tcp_window_size`: Finestra TCP

L'optimizer minimizza lo score globale di errore attraverso **iterazioni intelligenti**.

---

## 🔄 Workflow Visuale

```
                   📊 CSV Input Dataset
                           ↓
                  [1.generate_topology.sh]
                           ↓
              📋 Topology JSON + Docker Setup
                           ↓
                  [2.replicate_flow.sh]
                           ↓
                    🔄 Mininet Simulation
                           ↓
                      🌐 traffic.pcap
                           ↓
                  [3.regenerate_flows.sh]
                           ↓
                   📊 Regenerated CSV (87 features)
                           ↓
                  [4.compare_flows.sh]
                           ↓
              📈 Error Metrics + Graphs
                           ↓
                  [5.optimize_flow_simulation.sh] ⚙️ OPTIONAL
                           ↓
                  Bayesian Optimization Loop
                           ↓
                  [6.evaluate_optimization.sh] ⚙️ OPTIONAL
                           ↓
                    📋 Final Report
```

---

## 🎓 Letture Consigliate

1. **Se sei nuovo**: Leggi [doc/index.html](doc/index.html) → [doc/quick-reference.html](doc/quick-reference.html)
2. **Se devi eseguire subito**: Copia i comandi da [doc/quick-reference.html](doc/quick-reference.html)
3. **Se vuoi capire**: Leggi [doc/readme.html](doc/readme.html)
4. **Se vuoi fare deep dive**: Studia [doc/architecture.html](doc/architecture.html)

---

## 📦 Dipendenze Installate Automaticamente

- **Python packages**: pandas, numpy, scikit-learn, scipy, scikit-optimize, matplotlib, seaborn, pyyaml
- **Docker images**: mininet, cicflowmeter, custom-replicator
- **Linux packages**: docker, openvswitch, python3-dev

---

## ⚡ Performance Tips

| Scenario | Suggerimento |
|----------|-------------|
| Dataset piccolo (<100 flussi) | Tutto dovrebbe funzionare in <45 min |
| Dataset medio (100-500 flussi) | 45 min - 2 ore |
| Dataset grande (1000+ flussi) | 2+ ore, considera ottimizzazione batch |
| Optimization lento | Riduci i trial (default 10), aumenta `--timeout` |
| RAM limitata | Usa `--max-flows 500` in step 2 |

---

## 📜 Recent Fixes & Improvements

✅ **FIN Flag Count Error Fix** (v2.0)
- Corretto bug nel calcolo dell'errore quando feature_originale = 0
- Errore FIN passato da 100% a 43.18% (realistico)

✅ **Intermediate Files Organization** (v2.0)
- File temporanei (bidir_dataset, burst_dataset, etc.) ora in `shared/results/tmp/`

✅ **4-Tuple Flow Identification** (v1.5)
- Corretta gestione flussi con stessa IP pair ma porte diverse

---

## 🤝 Contribuire

Se trovi bug o hai suggerimenti, apri un'issue o fai una pull request!

---

## 📄 Licenza

[Vedi LICENSE file nel repository]

---

## 📞 Contatti & Link Utili

- 📧 **Issues**: [Apri una GitHub issue](https://github.com/maxrak/FLow-Stealth-attack/issues)
- 📚 **Documentazione Completa**: Vedi cartella `/doc/`
- 🔗 **Repository**: https://github.com/maxrak/FLow-Stealth-attack

---

## 🎉 Pronto a Iniziare?

1. **Installa**: Vedi sezione [Installazione](#installazione)
2. **Esegui**: Segui [Quick Start](#quick-start-5-minuti)
3. **Leggi**: Apri [doc/index.html](doc/index.html) per la documentazione completa
4. **Debugga**: Usa [doc/quick-reference.html](doc/quick-reference.html#debug-commands) per troubleshooting

**Buona simulazione! 🚀**

---

*Last Updated: October 28, 2024*  
*FASF v2.0 - Flow Stealth Attack Simulation Framework*
