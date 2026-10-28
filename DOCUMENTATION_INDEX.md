# 📚 FASF Documentation Index

Guida completa ai documenti di documentazione del framework FASF.

---

## 🎯 Per Iniziare (Nuovi Utenti)

Se sei nuovo al progetto, leggi in questo ordine:

1. **[README.md](README.md)** - Leggi prima!
   - Overview del framework
   - Architecture generale
   - Quick start guide
   - Descrizione di ogni script
   - Requirements e setup

2. **[WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md)** - Secondo
   - I 6 step workflow con comandi esatti
   - Quick commands per casi comuni
   - File locations
   - Success criteria
   - Debug commands

3. **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** - Per capire visivamente
   - Diagrammi ASCII del workflow
   - Data transformations tra step
   - Come vengono calcolate le feature
   - Optimization loop dettagliato
   - Error flow troubleshooting

---

## 📖 Per Comprendere gli Script

Consulta [README.md](README.md) sezione "Workflow Scripts" per:

- **[1.generate_topology.sh](1.generate_topology.sh)**
  - Genera topologia di rete da CSV
  - Input: CSV file
  - Output: Topology JSON

- **[2.replicate_flow.sh](2.replicate_flow.sh)**
  - Esegue simulazione Mininet
  - Genera traffico e cattura PCAP
  - Support 6 implementazioni diverse
  - Output: PCAP file

- **[3.regenerate_flows.sh](3.regenerate_flows.sh)**
  - Estrae feature con CICFlowMeter
  - Output: Regenerated CSV

- **[4.compare_flows.sh](4.compare_flows.sh)**
  - Confronta original vs regenerated
  - Calcola metriche di errore
  - Output: Report JSON

- **[5.optimize_flow_simulation.sh](5.optimize_flow_simulation.sh)**
  - Bayesian Optimization di parametri
  - Output: Trials JSONL

- **[6.evaluate_optimization.sh](6.evaluate_optimization.sh)**
  - Genera report e grafici
  - Output: PNG charts, CSV dati

---

## 🔧 Per Eseguire il Workflow

### Workflow Standard
Vedi [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md):
- Standard Workflow section (Step 1-4)
- Vedi comando esatto per ogni step

### Workflow con Ottimizzazione
Vedi [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md):
- Standard Workflow section
- + Step 5 (Optimization)
- + Step 6 (Evaluation)

### Test Veloci
Vedi [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md):
- Quick Commands section
- Test single/multiple implementations
- Batch testing

---

## 🔍 Per Debuggare

### Errori comuni
Vedi [README.md](README.md) sezione "Troubleshooting"

### Errori dettagliati
Vedi [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) sezione "Error Flow"

### Debug commands
Vedi [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md):
- Debug Commands section
- Analisi JSON
- Ricerca flussi specifici

---

## 📊 Per Capire i Dati

### Formato Input/Output
Vedi [README.md](README.md) sezione "File Format Specifications":
- Input CSV (87 features)
- Topology JSON
- Report JSON

### Data Transformations
Vedi [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md):
- Data Flow Transformation section
- Come cambiano i dati tra step

### Feature Calculation
Vedi [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md):
- Feature Calculation Detail section
- Come CICFlowMeter calcola 87 feature

---

## 🎓 Per Capire l'Architettura

### Visione Generale
Vedi [README.md](README.md):
- Architecture section (diagramma principale)
- How It Works section (spiegazione step-by-step)

### Dettagli Implementativi
Vedi [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md):
- Complete Workflow Pipeline
- Data Flow Transformation
- Feature Calculation Detail
- Optimization Loop Detail
- File Organization

---

## 📋 Report e Bug Fixes Recenti

### Fix: FIN Flag Count Error Calculation
Vedi:
- [BUG_FIN_FLAG_CALCULATION.md](BUG_FIN_FLAG_CALCULATION.md) - Analisi del bug
- [FIN_FLAG_COUNT_FIX_SUMMARY.md](FIN_FLAG_COUNT_FIX_SUMMARY.md) - Soluzione applicata

**Cosa è successo**:
- Errore relativo sull'FIN Flag Count era 100% (sbagliato)
- Causa: Formula division by zero quando original=0
- Fix: Nuova gestione per caso original=0
- Risultato: Errore corretto a 43.18%

---

## 📁 Struttura Directory

```
FASF/
├── README.md                        ← LEGGI PRIMA!
├── WORKFLOW_QUICK_REFERENCE.md      ← Per eseguire comandi
├── ARCHITECTURE_DIAGRAM.md          ← Per capire visivamente
├── DOCUMENTATION_INDEX.md           ← Questo file
│
├── BUG_FIN_FLAG_CALCULATION.md      ← Analisi bug FIN Flag Count
├── FIN_FLAG_COUNT_FIX_SUMMARY.md    ← Fix applicato
│
├── 1.generate_topology.sh           ← Script workflow
├── 2.replicate_flow.sh
├── 3.regenerate_flows.sh
├── 4.compare_flows.sh
├── 5.optimize_flow_simulation.sh
├── 6.evaluate_optimization.sh
│
├── aggregate_bursts.sh              ← Script utility
├── compare_fin_flags.sh
│
├── docker-compose.yml               ← Docker configuration
│
├── mininet/                         ← Simulazione di rete
├── optimizer/                       ← Ottimizzazione Bayesian
├── evaluator/                       ← Valutazione e report
├── cicflowmeter/                    ← Estrazione feature
│
└── shared/                          ← Dati
    ├── input_flows/                 ← CSV originali
    ├── topologies/                  ← JSON topologie
    ├── pcap/                        ← File PCAP
    ├── output_flows/                ← CSV rigenerati
    ├── results/                     ← Report e grafici
    └── results/tmp/                 ← File intermedi
```

---

## 🚀 Workflow Consigliato per Diversi Usi

### Per Nuovi Utenti
1. Leggi [README.md](README.md)
2. Prova [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md) "Test Single Implementation"
3. Consulta [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) per capire

### Per Produzione
1. Prepara file CSV
2. Esegui workflow standard (Step 1-4)
3. Esegui optimization (Step 5 - opzionale, lungo)
4. Valuta risultati (Step 6)
5. Analizza report JSON

### Per Testing Implementazioni
1. [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md): "Test Multiple Implementations"
2. Confronta metriche
3. Scegli migliore

### Per Debug
1. [README.md](README.md): Troubleshooting section
2. [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md): Debug Commands
3. [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md): Error Flow

---

## 💡 Tipiche Domande e Risposte

### Q: Come eseguo il framework?
**A**: Vedi [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md) "Standard Workflow"

### Q: Quali script eseguo e in che ordine?
**A**: Vedi [README.md](README.md) "Workflow Scripts" sezione 🔹 1 through 6

### Q: Che cosa fa ogni script?
**A**: Vedi [README.md](README.md) sezione "Workflow Scripts" per ogni script dettagliato

### Q: Dove trovano i file generati?
**A**: Vedi [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md) "File Locations"

### Q: Come capisco se è andato bene?
**A**: Vedi [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md) "Success Criteria"

### Q: Come risolvo gli errori?
**A**: 
1. Vedi [README.md](README.md) "Troubleshooting"
2. Oppure [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md) "Common Issues"
3. Oppure [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) "Error Flow"

### Q: Come capisco cosa fa il framework?
**A**: 
1. Vedi [README.md](README.md) "Architecture"
2. Poi [README.md](README.md) "How It Works"
3. Poi [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) per visuali

### Q: Perché l'errore relativo è così alto?
**A**: Vedi [BUG_FIN_FLAG_CALCULATION.md](BUG_FIN_FLAG_CALCULATION.md) e [FIN_FLAG_COUNT_FIX_SUMMARY.md](FIN_FLAG_COUNT_FIX_SUMMARY.md)

---

## 📞 Support

- **Errori durante esecuzione**: [README.md](README.md) Troubleshooting
- **Non capisco il workflow**: [WORKFLOW_QUICK_REFERENCE.md](WORKFLOW_QUICK_REFERENCE.md)
- **Non capisco l'architettura**: [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)
- **Bug nei metriche**: [BUG_FIN_FLAG_CALCULATION.md](BUG_FIN_FLAG_CALCULATION.md)

---

## 🔄 Versione Documentazione

- **Data**: 2026-10-28
- **Versione Framework**: 2.0 (Architecture Redesign)
- **Stato Documentazione**: Completa e coerente
- **Ultimo Aggiornamento**:
  - README.md: Completo con descrizione di ogni script
  - WORKFLOW_QUICK_REFERENCE.md: Quick commands e debug
  - ARCHITECTURE_DIAGRAM.md: Diagrammi e dettagli
  - DOCUMENTATION_INDEX.md: Questo file di indice

---

**Buona lettura! 📖**

Se hai domande, consulta i documenti qui sopra nel loro ordine consigliato!
