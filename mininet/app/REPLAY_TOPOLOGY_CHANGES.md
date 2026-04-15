# Guida alle Modifiche di replay_topology.py

## Modifiche Apportate

Il file `replay_topology.py` è stato modificato per supportare diverse implementazioni di client/server in modo parametrizzabile.

## Novità

### 1. Struttura Organizzata delle Implementazioni

Tutte le coppie client/server sono ora organizzate in sottocartelle nella directory `implementations/`:

```
implementations/
├── README.md
├── scapy_burst/
│   ├── client.py
│   ├── server.py
│   └── README.md
├── tcp_simple/
│   ├── client.py
│   ├── server.py
│   └── README.md
└── flow_emulator/
    ├── client.py
    ├── server.py
    └── README.md
```

### 2. Parametro Implementation

È stato aggiunto un nuovo parametro opzionale alla linea di comando per specificare quale implementazione usare:

```bash
python replay_topology.py <topology.json> [duration] [flows_csv] [max_subnets] [implementation]
```

**Default**: `scapy_burst` (comportamento originale)

### 3. Esempi di Utilizzo

#### Uso Default (scapy_burst)
```bash
python replay_topology.py topology.json 60 flows.csv
```

#### Usa tcp_simple
```bash
python replay_topology.py topology.json 60 flows.csv 10 tcp_simple
```

#### Usa flow_emulator
```bash
python replay_topology.py topology.json 60 flows.csv 10 flow_emulator
```

#### Modalità Interattiva con implementazione specifica
```bash
python replay_topology.py topology.json 0 flows.csv 10 tcp_simple
```

## Modifiche alle Funzioni

### `start_servers(net, host_map, implementation='scapy_burst')`
- Ora accetta il parametro `implementation`
- Carica il server dalla sottocartella appropriata: `/app/implementations/{implementation}/server.py`
- Log migliorati con indicazione dell'implementazione in uso

### `start_traffic_flows(..., implementation='scapy_burst')`
- Ora accetta il parametro `implementation`
- Carica il client dalla sottocartella appropriata: `/app/implementations/{implementation}/client.py`
- Log migliorati con indicazione dell'implementazione in uso

### `run_topology_replay(..., implementation='scapy_burst')`
- Nuovo parametro `implementation` con default `scapy_burst`
- Propaga il parametro alle funzioni `start_servers()` e `start_traffic_flows()`

### `main()`
- Parsing del quinto argomento come nome dell'implementazione
- Help aggiornato con esempi delle diverse implementazioni
- Elenco delle implementazioni disponibili

## Retrocompatibilità

Le modifiche sono completamente retrocompatibili:
- I file originali rimangono nella cartella `/app` (non utilizzati dalla nuova versione)
- Il comportamento di default è identico a prima (`scapy_burst`)
- Gli script esistenti continuano a funzionare senza modifiche

## File di Log

I file di log ora includono il nome dell'implementazione:

**Server**: `/tmp/server_{implementation}_{ip}.log`  
**Client**: `/tmp/client_{implementation}_{src_ip}_{dst_ip}.log`

Esempio:
- `/tmp/server_scapy_burst_192_168_1_10.log`
- `/tmp/client_tcp_simple_192_168_1_10_192_168_1_20.log`

## Test

Per verificare che tutto funzioni:

```bash
# Verifica sintassi Python
python3 -m py_compile replay_topology.py

# Mostra help con nuove opzioni
python replay_topology.py

# Test con implementazione di default
python replay_topology.py topology.json 30 flows.csv 5

# Test con implementazione alternativa
python replay_topology.py topology.json 30 flows.csv 5 tcp_simple
```

## Note Importanti

1. **Nomi Standardizzati**: Tutte le implementazioni usano `client.py` e `server.py` come nomi dei file
2. **Interfaccia Uniforme**: Tutti i client devono accettare: `csv_file src_ip dst_ip [config_file]`
3. **Interfaccia Server**: Tutti i server devono accettare: `--iface <interface> --ip <ip>`
4. **Estensibilità**: Nuove implementazioni possono essere aggiunte semplicemente creando una nuova sottocartella

## Vantaggi

- ✅ Modularità: facile aggiungere/rimuovere implementazioni
- ✅ Organizzazione: ogni implementazione è isolata
- ✅ Documentazione: ogni implementazione ha il suo README
- ✅ Testing: facile testare diverse implementazioni senza modificare codice
- ✅ Manutenibilità: modifiche a un'implementazione non influenzano le altre
