# Test Application per Client/Server Implementations

Applicazione Python per testare automaticamente le diverse implementazioni di client e server nella cartella `implementations/`.

## Caratteristiche

- ✅ Testa tutte le implementazioni o una specifica
- ✅ Verifica esistenza file client.py e server.py
- ✅ Avvia server in background e verifica connettività
- ✅ Esegue client e verifica completamento
- ✅ Genera report dettagliato con statistiche
- ✅ Salva risultati in formato JSON
- ✅ Output colorato e intuitivo

## Requisiti

```bash
python3 (>= 3.7)
scapy
```

## Uso

### Testare tutte le implementazioni

```bash
python test_implementations.py
```

### Testare una implementazione specifica

```bash
python test_implementations.py tcp_simple
python test_implementations.py scapy_burst
python test_implementations.py flow_emulator
```

### Output verboso

```bash
python test_implementations.py --verbose
python test_implementations.py tcp_simple -v
```

### Elencare implementazioni disponibili

```bash
python test_implementations.py --list
```

## Output

L'applicazione produce:

1. **Output console** con colori:
   - 🟢 Verde = successo
   - 🔴 Rosso = errore
   - 🟡 Giallo = warning
   - 🔵 Cyan/Blu = info

2. **File JSON** (`test_results.json`) con:
   - Timestamp test
   - Risultati per implementazione
   - Stage completati
   - Output client
   - Statistiche aggregate

## Esempio Output

```
============================================================
Testing: tcp_simple
============================================================

[INFO] File client.py e server.py trovati
[SUCCESS] Server avviato con successo (PID: 12345)
[INFO] Avvio client (durata: 5s)...
[SUCCESS] Client completato con successo
[INFO] Fermo il server...

✓ tcp_simple: SUCCESSO

============================================================
RIEPILOGO TEST
============================================================

Totale: 3 | Passati: 2 | Falliti: 1

✓ scapy_burst        [files: ✓, server: ✓, client: ✓]
✗ flow_emulator      [files: ✓, server: ✓, client: ✗] - Client fallito
✓ tcp_simple         [files: ✓, server: ✓, client: ✓]

Risultati salvati in: test_results.json
```

## Struttura Test

Ogni test esegue 3 stage:

1. **Files Check**: Verifica esistenza client.py e server.py
2. **Server Start**: Avvia server e verifica porta aperta
3. **Client Run**: Esegue client e verifica successo

## Parametri Test

| Parametro | Valore | Descrizione |
|-----------|--------|-------------|
| Port | 9000 | Porta TCP di test |
| Duration | 5s | Durata traffico client |
| Host | 127.0.0.1 | Localhost per test |
| Timeout | 15s | Timeout max per client |

## Exit Codes

- `0`: Tutti i test passati
- `N`: N test falliti (1-N)
- `1`: Errore generico o interruzione

## Formato JSON Risultati

```json
{
  "timestamp": "2026-07-05 15:30:45",
  "total": 3,
  "passed": 2,
  "failed": 1,
  "results": [
    {
      "name": "tcp_simple",
      "success": true,
      "stages": {
        "files_check": true,
        "server_start": true,
        "client_run": true
      },
      "error": null,
      "client_output": "..."
    }
  ]
}
```

## Troubleshooting

### Porta già in uso

Se vedi "Address already in use", un test precedente potrebbe non aver chiuso il server:

```bash
# Trova processo su porta 9000
lsof -ti:9000 | xargs kill -9
```

### Permission denied

Su Linux potrebbero servire privilegi per Scapy:

```bash
sudo python test_implementations.py
```

### Client timeout

Se il client va in timeout:
- Verifica firewall
- Aumenta durata test modificando `test_duration` in `ImplementationTester`
- Controlla output verboso con `-v`

## Estendere

Per aggiungere nuovi test:

1. Eredita da `ImplementationTester`
2. Override metodi `run_client()` o `start_server()`
3. Aggiungi logica specifica

Esempio:

```python
class MyCustomTester(ImplementationTester):
    def run_client(self) -> Tuple[bool, str]:
        # Custom client logic
        return True, "Custom output"
```

## Note Implementazioni

### tcp_simple
- Client: client.py (dst_ip, dst_port, duration, pps)
- Server: server.py (port)
- Usa socket nativi Python

### scapy_burst
- Client: client.py (csv_file, src_ip, dst_ip, config)
- Server: server.py (--iface, --ip)
- Usa Scapy per burst ottimizzati

### flow_emulator
- Client: client.py (csv_file, src_ip, dst_ip, params)
- Server: server.py (--iface, --ip)
- Emulazione con controllo statistiche

## Licenza

Parte del progetto FLow-Stealth-attack
