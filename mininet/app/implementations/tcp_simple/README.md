# Implementazione: TCP Simple

Questa implementazione utilizza socket TCP standard di Python.

## Componenti

- **Client**: `client.py` (copia di `client_replay.py`)
  - Client TCP semplificato
  - Replay di traffico basato su CSV
  - Connessioni TCP native

- **Server**: `server.py` (copia di `server_tcp_simple.py`)
  - Server TCP semplice
  - Gestione connessioni multiple
  - Implementazione leggera

## Utilizzo

```bash
python replay_topology.py topology.json 60 flows.csv 10 tcp_simple
```

## Note

Implementazione più semplice e leggera rispetto a scapy_burst, utile per test base.
