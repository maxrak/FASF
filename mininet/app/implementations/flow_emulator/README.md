# Implementazione: Flow Emulator

Questa implementazione emula flussi di rete con controllo preciso dei parametri.

## Componenti

- **Client**: `client.py` (copia di `flow_emulator.py`)
  - Emulatore di flussi con distribuzioni statistiche
  - Supporto per parametri personalizzati via JSON
  - Controllo su packet size, inter-arrival time, idle time

- **Server**: `server.py` (copia di `server_adv.py`)
  - Server basato su Scapy
  - Gestione handshake TCP
  - Compatibile con l'emulatore di flussi

## Utilizzo

```bash
python replay_topology.py topology.json 60 flows.csv 10 flow_emulator
```

## Note

Questa implementazione è utile per test che richiedono un controllo preciso sui parametri statistici del traffico.
Supporta distribuzioni log-normal per packet size e esponenziale per inter-arrival time.
