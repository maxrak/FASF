# Implementazioni Client/Server

Questa directory contiene le diverse implementazioni di client e server utilizzabili per la generazione di traffico nella topologia di rete.

## Struttura

Ogni sottocartella rappresenta un'implementazione completa e contiene:
- `client.py`: script client per la generazione del traffico
- `server.py`: script server per ricevere il traffico
- `README.md`: documentazione specifica dell'implementazione

## Implementazioni Disponibili

### 1. scapy_burst (default)
- **Client**: `client_scapy_burst_optimized.py`
- **Server**: `server_adv.py`
- **Caratteristiche**: Generazione traffico a burst ottimizzato con Scapy
- **Uso**: Implementazione di default, alte prestazioni

### 2. tcp_simple
- **Client**: `client_replay.py`
- **Server**: `server_tcp_simple.py`
- **Caratteristiche**: Socket TCP nativi
- **Uso**: Implementazione leggera e semplice

### 3. flow_emulator
- **Client**: `flow_emulator.py`
- **Server**: `server_adv.py`
- **Caratteristiche**: Emulazione con controllo parametri statistici
- **Uso**: Test con controllo preciso delle distribuzioni

## Come Usare

Per specificare l'implementazione da usare, passare il nome come ultimo parametro a `replay_topology.py`:

```bash
# Usa scapy_burst (default)
python replay_topology.py topology.json 60 flows.csv

# Usa tcp_simple
python replay_topology.py topology.json 60 flows.csv 10 tcp_simple

# Usa flow_emulator
python replay_topology.py topology.json 60 flows.csv 10 flow_emulator
```

## Aggiungere Nuove Implementazioni

Per aggiungere una nuova implementazione:

1. Creare una nuova sottocartella con nome descrittivo
2. Aggiungere `client.py` e `server.py`
3. Assicurarsi che accettino i parametri standard:
   - Client: `csv_file src_ip dst_ip [config_file]`
   - Server: `--iface <interface> --ip <ip>`
4. Creare un `README.md` con la documentazione
5. Usare il nome della cartella come parametro in `replay_topology.py`

## Note

- I file originali rimangono nella cartella `/app` principale per retrocompatibilità
- Le implementazioni nelle sottocartelle sono copie standardizzate
- Il nome del file è sempre `client.py` e `server.py` per uniformità
