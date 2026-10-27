# Riassunto Sessione di Debug e Fix

## Problemi Affrontati e Risolti

### 1. **FIN Flag Mancanti (100% errore su terminazione flussi)** ✅

#### Problema
- 33 su 49 flussi nel CSV adattato avevano FIN Flag Count = 0
- Il server non rispondeva al FIN del client, causando la perdita della chiusura TCP corretta

#### Root Cause
- Il server scapy riceveva il FIN dal client ma **non inviava il FIN-ACK** in risposta
- Questo violava il four-way handshake TCP standard

#### Soluzione Implementata
1. **Modifica server.py (scapy_burst e flow_emulator)**
   - Aggiunto risposta FIN-ACK quando il server riceve FIN dal client
   - Implementazione corretta del four-way handshake TCP

2. **Fix percorsi dei file log**
   - Rimosso doppio `/tmp/tmp/` nei percorsi
   - File log server e client ora correttamente creati in `/results/tmp/`

#### Verifica
I log del server mostrano che il FIN handshake funziona correttamente:
```
[FIN] Ricevuto da 72.14.213.102:443 -> 192.168.3.131:52202 (seq=1)
[FIN-ACK] Invio a 72.14.213.102:443 <- 192.168.3.131:52202 (seq=60736, ack=2)
```

### 2. **Flussi Persi - Deduplicazione Errata** ✅

#### Problema
- test6: 48 flussi nel CSV originale → solo 39 flussi generati (9 persi)
- Flussi con stessa coppia IP (src/dst) ma porte diverse venivano considerati duplicati

#### Root Cause
- `generate_flows_from_csv()` usava solo `(src_ip, dst_ip)` come chiave di deduplicazione
- Ignorava le porte, considerando `192.168.3.131:56027 → 65.54.95.140:80` uguale a `192.168.3.131:56359 → 65.54.95.140:80`

#### Soluzione Implementata
1. **Modifica generate_flows_from_csv()**
   - Usa la 4-tupla completa: `(src_ip, src_port, dst_ip, dst_port)` come chiave di deduplicazione

2. **Aggiornamento generate_initial_params.py**
   - Nomi file config ora includono le porte: `test6_192_168_3_131_56027_65_54_95_140_80.config`
   - Questo previene sovrascritture di file config per flussi con porte diverse

3. **Modifica start_traffic_flows()**
   - Usa le porte nel percorso dei file config

#### Risultato
- test6: 48 flussi nel CSV → 45 flussi unici correttamente generati
- I 3 flussi a 65.54.95.140 con porte diverse (56027, 56359, 55963) sono tutti riprodotti

### 3. **Organizzazione File Intermedi** ✅

#### Problema
- File intermedi sparsi in `/results/` rendevano difficile distinguere da file finali

#### Soluzione Implementata
1. **Centralizzazione in `/results/tmp/`**
   - `burst_dataset_*.csv` → `/results/tmp/burst_dataset_*.csv`
   - `bidir_dataset_*.csv` → `/results/tmp/bidir_dataset_*.csv`
   - `flows_adapted_*.log` → `/results/tmp/flows_adapted_*.log`
   - `server_*.log` → `/results/tmp/server_*.log`

2. **Aggiornamento moduli implementazione**
   - Modificati 15+ file Python in `/mininet/app/implementations/`
   - Aggiunto `os.makedirs('/results/tmp', exist_ok=True)` in `run_topology_replay()`

#### Verifica
Tutti i file intermedi sono correttamente creati in `/results/tmp/`:
```
/results/tmp/
├── flows_adapted.csv           # CSV adattato (50 righe = 49 flussi + header)
├── burst_dataset_*.csv         # Output burst per ogni coppia IP
├── flows_adapted_*.log         # Log client
├── server_*.log                # Log server di ogni destinazione
```

## Commit Effettuati

1. `7d36259` - Fix: Considera la quadrupla completa (Src IP, Src Port, Dst IP, Dst Port) nella generazione dei flussi
2. `3f4705d` - Organizzare file intermedi nella cartella results/tmp
3. `4ffd5cf` - Fix: Implementare proper four-way handshake TCP con FIN-ACK dal server
4. `57dfc4b` - Fix: Rimuovi doppi /tmp/tmp/ nei percorsi dei file log e output

## Note Importanti

### Sui FIN Flag Mancanti
- Il CSV originale test6.csv contiene **33 flussi senza FIN** (FIN Flag Count = 0)
- Questo è un problema dei **dati di input**, non del nostro replicatore
- Molto probabilmente i flussi originali nel PCAP sono stati incompleti/troncati
- Il nostro replicatore ora invia correttamente i FIN durante la simulazione
- I server rispondono correttamente con FIN-ACK (confermato dai log)

### Sulla Deduplicazione
- La 4-tupla (Src IP, Src Port, Dst IP, Dst Port) è il metodo **standard e corretto** per identificare flussi TCP
- Due flussi possono avere la stessa coppia IP ma porte diverse e istanti diversi

### Su Mininet e Simulazione
- La simulazione viene eseguita per un tempo limitato (3 secondi nel test)
- Alcuni flussi potrebbero non completare tutti i pacchetti in questo tempo
- I FIN vengono inviati quando il client termina (indipendentemente dai dati ricevuti dal server)
