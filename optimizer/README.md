# Traffic Optimizer

Ottimizzatore modulare per adattare `optimizer_config.json` del client in base al confronto tra flussi reali e flussi rigenerati.

Pipeline eseguita per ogni trial:

```bash
./2.replicate_slow.sh <nome_test>
./3.regenerate_flows.sh <nome_test>
./4.compare_flows <nome_test>
```

Il confronto deve produrre un JSON in:

```text
shared/results/<nome_test>/report_data.json
```

## Installazione

Python 3.9+.

```bash
pip install -r requirements.txt
```

Optuna e' opzionale ma richiesto per `--algorithm optuna`.

## Uso base

Esegui dal root del tuo progetto, dove si trovano gli script `2.replicate_slow.sh`, `3.regenerate_flows.sh`, `4.compare_flows` e la cartella `shared/`.

```bash
python3 -m traffic_optimizer.optimize test5 \
  --base-config optimizer_config_template.json \
  --output-config optimizer_config.json \
  --search-space traffic_optimizer/config/search_space.json \
  --algorithm random \
  --max-trials 30 \
  --resume
```

Con Optuna/TPE:

```bash
python3 -m traffic_optimizer.optimize test5 \
  --base-config optimizer_config_template.json \
  --output-config optimizer_config.json \
  --search-space traffic_optimizer/config/search_space.json \
  --algorithm optuna \
  --max-trials 50 \
  --resume
```

## Stop sicuro

Durante l'esecuzione puoi fermare il ciclo creando uno stop-file:

```bash
touch optimizer_state/test5/STOP
```

L'ottimizzatore finisce il trial corrente, salva lo stato e si ferma.

## Output

Per ogni test crea:

```text
optimizer_state/<test>/
  trials.jsonl
  checkpoint.json
  best_config.json
  best_report_data.json
  optuna.db
  STOP
```

## Algoritmi inclusi

- `random`: Random Search intelligente, con campionamento logaritmico per parametri positivi, mutazione intorno al best corrente e qualche candidato esplorativo.
- `optuna`: Optuna/TPE, con storage SQLite riprendibile.

## Personalizzazione

Modifica `traffic_optimizer/config/search_space.json` per aggiungere/togliere parametri senza cambiare codice.
