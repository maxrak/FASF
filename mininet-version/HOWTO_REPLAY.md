# 🚀 Come Eseguire il Replay con Probe

## Metodo 1: Script Automatico (Consigliato)

```bash
cd /Users/massimilianorak/Development/FLow-Stealth-attack/mininet-version

# Esecuzione con parametri di default (60 secondi, 5 subnet)
./run_full_pipeline.sh

# Esecuzione personalizzata
./run_full_pipeline.sh features/target.csv 30 10
```

**Parametri:**
- `$1`: File CSV (default: `features/target.csv`)
- `$2`: Durata in secondi (default: `60`)
- `$3`: Max subnet (default: `5`)

---

## Metodo 2: Comandi Manuali

### Passo 1: Genera la topologia

```bash
python app/analyze_flows.py features/target.csv
```

**Output:**
- Statistiche IP sorgente/destinazione
- File `network_topology.json` con configurazione rete e probe

### Passo 2: Copia in /shared

```bash
cp network_topology.json shared/
```

### Passo 3: Pulizia Mininet (se necessario)

```bash
docker compose run --rm mininet mn -c
```

### Passo 4: Esegui replay con probe

```bash
# Test rapido (10 secondi, 3 subnet)
docker compose run --rm mininet python3 /app/replay_topology.py \
    /shared/network_topology.json 10 /features/target.csv 3

# Esecuzione standard (60 secondi, 5 subnet)
docker compose run --rm mininet python3 /app/replay_topology.py \
    /shared/network_topology.json 60 /features/target.csv 5

# Esecuzione completa (120 secondi, tutte le subnet)
docker compose run --rm mininet python3 /app/replay_topology.py \
    /shared/network_topology.json 120 /features/target.csv 20

# Modalità interattiva (CLI Mininet)
docker compose run --rm mininet python3 /app/replay_topology.py \
    /shared/network_topology.json 0
```

### Passo 5: Verifica il pcap

```bash
# Verifica dimensione
ls -lh pcap/capture.pcap

# Conta pacchetti
tcpdump -r pcap/capture.pcap | wc -l

# Visualizza primi 20 pacchetti
tcpdump -r pcap/capture.pcap -n -c 20

# Anteprima con dettagli
tcpdump -r pcap/capture.pcap -n -v | head -50
```

---

## Architettura della Rete

```
┌──────────────────────────────────────────────────┐
│         Switch Centrale (s0 - Gateway)           │
│            ↑                                     │
│            │ Probe connesso qui                  │
│            │ (cattura tutto il traffico)         │
└─────┬──────┴───────┬──────────┬─────────┬────────┘
      │              │          │         │
   ┌──▼──┐        ┌──▼──┐    ┌──▼──┐  ┌──▼──┐
   │ s1  │        │ s2  │    │ s3  │  │ ... │
   │10.0 │        │172  │    │174  │  │     │
   └──┬──┘        └──┬──┘    └──┬──┘  └─────┘
      │              │           │
   ┌──▼──┐        ┌──▼──┐    ┌──▼──┐
   │ h1  │        │ h3  │    │ h5  │
   │ h2  │        │ h4  │    │     │
   └─────┘        └─────┘    └─────┘
   Clients        Clients    Clients
```

**Nodo Probe:**
- IP: `10.255.255.254/24`
- Connesso a: Switch Gateway (s0)
- Interfaccia: `probe-eth0`
- Comando: `tcpdump -i probe-eth0 -w /pcap/capture.pcap`
- Output: `/pcap/capture.pcap`

---

## Analisi del PCAP con CICFlowMeter

```bash
# Avvia container CICFlowMeter
docker compose run --rm cicflowmeter bash

# Analizza il pcap
./cicflowmeter.sh /pcap /features

# Verifica CSV generato
ls -lh /features/*.csv
```

---

## Troubleshooting

### Errore: "RTNETLINK answers: File exists"

**Soluzione:** Pulisci la rete Mininet

```bash
docker compose run --rm mininet mn -c
```

### Errore: "Unable to derive default datapath ID"

**Causa:** Nome switch non canonico

**Soluzione:** Gli switch devono chiamarsi `s0`, `s1`, `s2`, ecc. (già corretto)

### Il pcap è vuoto o molto piccolo

**Possibili cause:**
1. Durata troppo breve → Aumenta il parametro durata
2. Poche subnet → Aumenta max_subnets
3. Client/server non comunicano → Verifica log container

**Debugging:**

```bash
# Esegui in modalità interattiva per debugging
docker compose run --rm mininet python3 /app/replay_topology.py \
    /shared/network_topology.json 0

# Nel CLI Mininet:
mininet> nodes            # Mostra tutti i nodi
mininet> net              # Mostra topologia
mininet> pingall          # Test connettività
mininet> probe ifconfig   # Verifica IP probe
mininet> probe tcpdump -i probe-eth0 -c 10  # Cattura 10 pacchetti
```

---

## Output Esempio

```
*** Caricamento topologia da /shared/network_topology.json
*** Topologia: 222 host, 7 subnet client, 229 flussi
*** Creazione rete Mininet
*** Switch centrale (gateway) creato: s0
*** Creazione di 5 sottoreti (su 8 totali)
*** Creazione switch per sottoreti
  - Switch s1 per 10.0.0.0/8 (connesso a s0)
  - Switch s2 per 172.16.0.0/16 (connesso a s0)
  ...
*** Creazione host
  - Host h1: 10.0.2.15
  - Host h2: 10.0.2.2
  ...
*** Creazione nodo probe per packet capture
  - Probe probe: 10.255.255.254/24 (connesso a s0)
*** Avvio rete
*** Configurazione switch in modalità standalone
*** Avvio packet capture sul probe
  - File: /pcap/capture.pcap
  - Interface: probe-eth0
  - Packet capture avviata
*** Avvio server su tutti gli host
*** Avvio generazione traffico
  - Traffico da 10.0.2.15 a 72.14.213.101
  ...
*** Esecuzione per 60 secondi
*** Cattura traffico completata
*** Arresto packet capture
*** Arresto rete
```

---

## File Generati

| File | Descrizione |
|------|-------------|
| `network_topology.json` | Configurazione topologia di rete |
| `shared/network_topology.json` | Copia per container Docker |
| `pcap/capture.pcap` | Packet capture del traffico |
| `/tmp/flows_adapted.csv` | CSV adattato (dentro container) |

---

## Parametri replay_topology.py

```
python3 /app/replay_topology.py <topology.json> [duration] [flows_csv] [max_subnets]
```

- **topology.json**: File JSON con topologia di rete (REQUIRED)
- **duration**: Durata in secondi (default: 60, 0 = modalità interattiva)
- **flows_csv**: File CSV con flussi originali (default: `/features/target.csv`)
- **max_subnets**: Numero massimo di subnet da creare (default: 10)

---

## Note Importanti

1. ⚠️ **Limitazione subnet**: Con troppe subnet (>20) Mininet potrebbe andare in timeout per il limite di interfacce di rete
2. 🔍 **Il probe cattura TUTTO**: Essendo connesso allo switch gateway vede tutto il traffico tra subnet
3. 📦 **Volume pcap/**: È condiviso tra host e container, il pcap è accessibile da entrambi
4. ⏱️ **Tempo di avvio**: OVS richiede 1-2 secondi per avviarsi completamente
5. 🧹 **Cleanup**: Sempre fare `mn -c` tra esecuzioni successive per evitare conflitti
