# ✅ RISOLTO: Perché target.csv Non Produce Dati

## Il Problema

Usando `features/target.csv`, replay_topology.py genera **pcap vuoti (24 bytes = solo header)**.

## La Causa

**Gli IP in target.csv non matchano con la topologia!**

```csv
# target.csv ha IP reali da dataset:
192.168.3.131 → 63.215.202.48
192.168.3.131 → 65.55.239.163
72.14.213.147 → 192.168.3.131
...

# La topologia Mininet ha IP diversi:
10.0.2.15, 10.0.2.2          (subnet 1)
172.16.0.1, 172.16.255.1     (subnet 2)
174.36.30.111                (subnet 3)
...
```

`client_scapy_burst_optimized.py` **filtra** i flussi cercando esattamente gli IP passati (`ip_client`, `ip_server`):

```python
# In client_scapy_burst_optimized.py linea 167-170:
flows = df[
    ((df["Source IP"] == ip_client) & (df["Destination IP"] == ip_server)) |
    ((df["Source IP"] == ip_server) & (df["Destination IP"] == ip_client))
]
```

**Risultato**: Cerca flussi 10.0.2.15 → 10.0.2.2 in un CSV che ha 192.168.3.131 → 63.215.202.48  
→ 0 match → 0 flussi generati → pcap vuoto!

## La Soluzione

### Script convert_target_csv.py

Converte `target.csv` **sostituendo** IP reali con IP della topologia, **mantenendo** tutte le statistiche:
- Packet size, IAT, duration, ecc. → invariati
- Solo Source IP e Destination IP → mappati a IP topologia

```bash
python3 convert_target_csv.py \
  features/target.csv \              # Input: CSV con IP reali
  features/target_converted.csv \    # Output: CSV con IP topologia
  shared/network_topology.json \     # Topologia di riferimento
  100 \                              # Max flussi (ometti per tutti)
  3                                  # Max sottoreti (CRITICO!)
```

### ⚠️ Parametro max_subnets CRITICO

**DEVE matchare** il numero di sottoreti passato a `replay_topology.py`!

```bash
# ❌ SBAGLIATO:
convert_target_csv.py ... 5    # Usa IP da 5 sottoreti (230 IP)
replay_topology.py ... 3       # Crea solo 3 sottoreti (5 host)
→ CSV ha IP che non esistono in Mininet → pcap vuoto

# ✅ CORRETTO:
convert_target_csv.py ... 3    # Usa IP da 3 sottoreti (5 host)
replay_topology.py ... 3       # Crea 3 sottoreti (5 host)
→ Tutti gli IP matchano → traffico generato!
```

## Uso Completo

### 1. Converti CSV

```bash
cd /Users/massimilianorak/Development/FLow-Stealth-attack/mininet-version

# Test con 50 flussi, 3 sottoreti
python3 convert_target_csv.py \
  features/target.csv \
  features/target_converted.csv \
  shared/network_topology.json \
  50 \
  3

# Output:
# [+] Usando IP da 3 sottoreti
# [+] IP disponibili nella topologia: 5
#     ['10.0.2.15', '10.0.2.2', '172.16.0.1', '172.16.255.1', '174.36.30.111']
# [+] Mappatura IP:
#     192.168.3.131 → 172.16.0.1
#     63.215.202.48 → 10.0.2.2
#     ...
# ✅ CSV convertito salvato in: features/target_converted.csv
#    Flussi totali: 50
#    Coppie IP uniche: 15
```

### 2. Verifica IP Convertiti

```bash
head -3 features/target_converted.csv

# Deve mostrare solo IP: 10.0.2.15, 10.0.2.2, 172.16.0.1, 172.16.255.1, 174.36.30.111
```

### 3. Esegui Replay (STESSO max_subnets!)

```bash
docker compose run --rm mininet python3 /app/replay_topology.py \
  /shared/network_topology.json \
  30 \
  /features/target_converted.csv \
  3    # ← STESSO numero della conversione!
```

### 4. Verifica Risultato

```bash
# Dimensione pcap
ls -lh pcap/capture.pcap
# Output atteso: > 24 bytes (es. 12K, 50K, ecc.)

# Pacchetti catturati
tcpdump -r pcap/capture.pcap -nn 2>&1 | tail -3
# Output atteso: traffico TCP tra IP della topologia

# Conta pacchetti
tcpdump -r pcap/capture.pcap 2>&1 | wc -l
# Output atteso: > 1 (es. 129, 500, ecc.)
```

## Risultati Test

### Test 1: 50 flussi, 3 sottoreti, 30 secondi

```bash
python3 convert_target_csv.py features/target.csv features/target_converted.csv shared/network_topology.json 50 3
docker compose run --rm mininet python3 /app/replay_topology.py /shared/network_topology.json 30 /features/target_converted.csv 3
```

**Risultato**:
- ✅ Flussi avviati: 4
- ✅ Pacchetti catturati: **129**
- ✅ Dimensione pcap: **12KB**
- ✅ Traffico: 10.0.2.2 ↔ 10.0.2.15 bidirezionale
- ✅ TCP handshake: SYN, SYN-ACK, ACK
- ✅ Data transfer: payload 5-83 bytes
- ✅ Solo IPv4

## Parametri Script Conversione

```bash
python3 convert_target_csv.py <input> <output> [topology] [max_flows] [max_subnets]
```

| Parametro | Descrizione | Default | Esempio |
|-----------|-------------|---------|---------|
| input | CSV originale con IP reali | - | features/target.csv |
| output | CSV convertito con IP topologia | - | features/target_converted.csv |
| topology | File topologia JSON | shared/network_topology.json | - |
| max_flows | Numero massimo flussi da convertire | tutti | 100 |
| **max_subnets** | **Numero sottoreti da usare** | tutti | **3** ← DEVE matchare replay! |

## Troubleshooting

### Pcap ancora vuoto (24 bytes)

```bash
# 1. Verifica max_subnets uguale
# In convert_target_csv.py output:
[+] Usando IP da 3 sottoreti
[+] IP disponibili nella topologia: 5

# In replay_topology.py output:
*** Creazione di 3 sottoreti (su 8 totali)
*** Creazione host (tutti connessi a s0)
  - Host h1: 10.0.2.15 (connesso a s0)
  - Host h2: 10.0.2.2 (connesso a s0)
  - Host h3: 172.16.0.1 (connesso a s0)
  - Host h4: 172.16.255.1 (connesso a s0)
  - Host h5: 174.36.30.111 (connesso a s0)

# ✅ Devono avere lo stesso numero di sottoreti e host!

# 2. Verifica IP nel CSV convertito
head -5 features/target_converted.csv

# ✅ Deve contenere SOLO IP creati in Mininet:
#    10.0.2.15, 10.0.2.2, 172.16.0.1, 172.16.255.1, 174.36.30.111

# 3. Controlla log replay
docker compose run --rm mininet python3 /app/replay_topology.py ... | grep "Traffico da"

# ✅ Deve mostrare "- Traffico da X a Y" (non solo "! Host non trovato")
```

### "! Host non trovato" in replay_topology.py

Significa che alcuni flussi nel CSV hanno IP che **non esistono** come host in Mininet.

**Cause**:
1. `max_subnets` diverso in conversione vs replay
2. CSV convertito ha ancora IP sbagliati

**Fix**:
```bash
# Riconverti con max_subnets corretto
python3 convert_target_csv.py \
  features/target.csv \
  features/target_converted.csv \
  shared/network_topology.json \
  100 \
  3    # ← Usa lo stesso valore di replay_topology.py!

# Verifica IP convertiti
python3 -c "
import pandas as pd
df = pd.read_csv('features/target_converted.csv')
ips = set(df['Src IP'].unique()) | set(df['Dst IP'].unique())
print(f'IP unici nel CSV: {sorted(ips)}')
"

# Output atteso: solo 5 IP (quelli creati in Mininet con max_subnets=3)
```

### Pochi flussi generati

Se vedi "*** 0 flussi di traffico avviati" o "*** 1 flussi":

1. **Aumenta max_flows** nella conversione:
   ```bash
   python3 convert_target_csv.py ... 200 3  # Più flussi
   ```

2. **Aumenta durata** esecuzione:
   ```bash
   replay_topology.py ... 60 ...  # 60 secondi invece di 30
   ```

3. **Controlla statistiche CSV**:
   ```bash
   # Coppie IP uniche
   python3 -c "
   import pandas as pd
   from collections import defaultdict
   df = pd.read_csv('features/target_converted.csv')
   counts = defaultdict(int)
   for _, row in df.iterrows():
       counts[(row['Src IP'], row['Dst IP'])] += 1
   for (src, dst), count in sorted(counts.items(), key=lambda x: -x[1])[:10]:
       print(f'{src} → {dst}: {count} flussi')
   "
   ```

## Comando Finale Garantito

```bash
cd /Users/massimilianorak/Development/FLow-Stealth-attack/mininet-version

# 1. Converti target.csv (100 flussi, 3 sottoreti)
python3 convert_target_csv.py \
  features/target.csv \
  features/target_converted.csv \
  shared/network_topology.json \
  100 \
  3

# 2. Verifica IP
head -3 features/target_converted.csv | cut -d',' -f2,4

# 3. Esegui replay (30 secondi, 3 sottoreti)
docker compose run --rm mininet python3 /app/replay_topology.py \
  /shared/network_topology.json \
  30 \
  /features/target_converted.csv \
  3

# 4. Verifica risultato
ls -lh pcap/capture.pcap
tcpdump -r pcap/capture.pcap -nn -c 20
```

✅ **Sistema completo e funzionante con target.csv!**
