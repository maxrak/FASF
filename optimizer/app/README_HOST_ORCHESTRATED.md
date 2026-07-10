# Architettura host-orchestrated

In questa versione l'optimizer container **non lancia Docker Compose**. Il ciclo viene orchestrato dallo script host `5.optimize_flow_simulation.sh`:

1. `docker compose run optimizer python3 -m traffic_optimizer.host_step propose ...`
2. host esegue `./2.replicate_flow.sh <test>` oppure `./2.replicate_slow.sh <test>`
3. host esegue `./3.regenerate_flows.sh <test>`
4. host esegue `./4.compare_flows.sh <test>` oppure `./4.compare_flows <test>`
5. `docker compose run optimizer python3 -m traffic_optimizer.host_step observe ...`

Il Docker socket non serve piu dentro il container optimizer.

## Volumi consigliati nel docker-compose.yml

```yaml
optimizer:
  build: ./optimizer
  volumes:
    - ./optimizer/app:/app
    - ./shared:/shared
    - ./optimizer_state:/optimizer_state
    - ./shared/results:/results
```

## Stop sicuro

Per fermare dopo il trial corrente:

```bash
touch optimizer_state/test5/STOP
```

Per riprendere, rimuovi il file STOP e rilancia lo script.
