# Implementazione: Scapy Burst

Questa implementazione utilizza Scapy per generare traffico a burst ottimizzato.

## Componenti

- **Client**: `client.py` (copia di `client_scapy_burst_optimized.py`)
  - Genera traffico basato su parametri di burst
  - Supporta configurazioni personalizzate tramite file `.config`
  - Ottimizzato per alte prestazioni

- **Server**: `server.py` (copia di `server_adv.py`)
  - Server avanzato basato su Scapy
  - Gestisce handshake TCP tramite iptables
  - Supporta sniffing su interfaccia specificata

## Utilizzo

```bash
python replay_topology.py topology.json 60 flows.csv 10 scapy_burst
```

## Note

Questa è l'implementazione di default utilizzata dal sistema.
