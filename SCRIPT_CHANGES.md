# Modifiche agli Script Bash

## Script Modificati

Sono stati aggiornati gli script bash per supportare il parametro `implementation` che permette di scegliere quale coppia client/server utilizzare.

### 1. `2.replicate_flow.sh`

**Modifiche:**
- Aggiunto parametro opzionale `[implementation]` (default: `scapy_burst`)
- Aggiunto help con controllo degli argomenti
- Aggiunta visualizzazione della configurazione prima dell'esecuzione

**Uso:**
```bash
./2.replicate_flow.sh <flow_name> [implementation]

# Esempi:
./2.replicate_flow.sh test2                    # Default: scapy_burst
./2.replicate_flow.sh test2 tcp_simple         # Usa tcp_simple
./2.replicate_flow.sh smallFlows flow_emulator # Usa flow_emulator
```

**Parametri:**
- `flow_name`: nome del flusso (richiesto)
- `implementation`: scapy_burst | tcp_simple | flow_emulator (opzionale, default: scapy_burst)

**Duration**: 30 secondi

---

### 2. `replicate_flow.sh`

**Modifiche:** Identiche a `2.replicate_flow.sh`

**Uso:**
```bash
./replicate_flow.sh <flow_name> [implementation]
```

**Duration**: 60 secondi

---

### 3. `run_full_pipeline.sh`

**Modifiche:**
- Aggiunto quarto parametro opzionale `[implementation]` (default: `scapy_burst`)
- Aggiornato help nella sezione commenti iniziali
- Aggiunta visualizzazione dell'implementazione nella configurazione

**Uso:**
```bash
./run_full_pipeline.sh [csv_file] [duration] [max_subnets] [implementation]

# Esempi:
./run_full_pipeline.sh                                    # Tutti i default
./run_full_pipeline.sh myflows.csv                        # Custom CSV
./run_full_pipeline.sh myflows.csv 120                    # CSV + duration
./run_full_pipeline.sh myflows.csv 120 20 tcp_simple      # Tutti i parametri
```

**Parametri:**
- `csv_file`: file CSV con i flussi (default: features/target.csv)
- `duration`: durata in secondi (default: 60)
- `max_subnets`: numero massimo di subnet (default: 10)
- `implementation`: tipo client/server (default: scapy_burst)

---

## Implementazioni Disponibili

Tutti gli script supportano ora queste implementazioni:

| Implementazione | Client | Server | Descrizione |
|----------------|--------|--------|-------------|
| **scapy_burst** (default) | client_scapy_burst_optimized.py | server_adv.py | Traffico a burst ottimizzato con Scapy |
| **tcp_simple** | client_replay.py | server_tcp_simple.py | Socket TCP nativi, implementazione leggera |
| **flow_emulator** | flow_emulator.py | server_adv.py | Emulazione con controllo parametri statistici |

---

## Retrocompatibilità

✅ **Completamente retrocompatibile**

Tutti gli script continuano a funzionare come prima se non si specifica il parametro `implementation`:

```bash
# Questi comandi funzionano come prima (usano scapy_burst di default)
./2.replicate_flow.sh test2
./replicate_flow.sh smallFlows
./run_full_pipeline.sh myflows.csv 60 10
```

---

## Validazione

Per verificare che gli script funzionino correttamente:

```bash
# Test help
./2.replicate_flow.sh
./replicate_flow.sh

# Test con default (scapy_burst)
./2.replicate_flow.sh test2

# Test con implementazione alternativa
./2.replicate_flow.sh test2 tcp_simple
./replicate_flow.sh test2 flow_emulator

# Test pipeline completa
./run_full_pipeline.sh myflows.csv 30 5 tcp_simple
```

---

## Note Tecniche

1. **Passaggio Parametri**: Gli script passano il parametro `implementation` come quinto argomento a `replay_topology.py`

2. **Valore Default**: Se non specificato, viene usato `scapy_burst` tramite espansione bash:
   ```bash
   IMPLEMENTATION=${2:-scapy_burst}
   ```

3. **Validazione**: La validazione dell'esistenza dell'implementazione viene fatta da `replay_topology.py`, non dagli script bash

4. **Logging**: I log includeranno il nome dell'implementazione:
   - Server: `/tmp/server_{implementation}_{ip}.log`
   - Client: `/tmp/client_{implementation}_{src_ip}_{dst_ip}.log`

---

## Script Non Modificati

Questi script non sono stati modificati perché non usano direttamente `replay_topology.py`:

- `1.generate_topology.sh` - Genera topologia da CSV
- `3.regenerate_flows.sh` - Rigenera flows da PCAP
- `run_pipeline.sh` - Usa configurazione di default interna
- `run_loop.sh` - Wrapper per ottimizzazione iterativa
- `aggregate_bursts.sh` - Utility per aggregazione burst

---

## Esempi Completi

### Workflow Standard
```bash
# 1. Genera topologia
./1.generate_topology.sh test2.csv

# 2. Replica flussi (30s, default scapy_burst)
./2.replicate_flow.sh test2

# 3. Rigenera CSV da PCAP
./3.regenerate_flows.sh test2
```

### Workflow con Implementazione Alternativa
```bash
# 1. Genera topologia
./1.generate_topology.sh myflows.csv

# 2. Replica con tcp_simple
./2.replicate_flow.sh myflows tcp_simple

# 3. Rigenera CSV
./3.regenerate_flows.sh myflows
```

### Pipeline Completa Custom
```bash
./run_full_pipeline.sh features/custom.csv 120 15 flow_emulator
```
