#!/usr/bin/env bash
set -u -o pipefail

usage() {
  cat <<'EOF'
Uso:
  ./5.optimize_flow_simulation.sh <nome_test> [opzioni]

Esempi:
  ./5.optimize_flow_simulation.sh test5 --algorithm random --max-trials 30
  ./5.optimize_flow_simulation.sh test5 --algorithm optuna --max-trials 80 --max-hours 6

Opzioni:
  --algorithm random|optuna        Algoritmo di ottimizzazione. Default: random
  --max-trials N                   Numero massimo di trial. Default: 30
  --max-hours H                    Stop dopo H ore, controllato tra un trial e il successivo
  --seed N                         Seed. Default: 42
  --base-config PATH               Config base vista dal container optimizer. Default: /app/config/base_optimizer_config.json
  --output-config PATH             Config scritta e letta dal client. Default: /shared/flows_params/optimizer_config.json
  --search-space PATH              Search space visto dal container optimizer. Default: /app/traffic_optimizer/config/search_space.json
  --replicate-script PATH          Script host replica. Default: auto, preferisce ./2.replicate_slow.sh poi ./2.replicate_flow.sh
  --regenerate-script PATH         Script host rigenerazione. Default: ./3.regenerate_flows.sh
  --compare-script PATH            Script host confronto. Default: auto, preferisce ./4.compare_flows poi ./4.compare_flows.sh
  --no-build                       Non esegue docker compose build optimizer all'inizio
  --help                           Mostra questo aiuto

Stop sicuro:
  touch optimizer_state/<nome_test>/STOP
EOF
}

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

TEST_NAME="$1"
shift

ALGORITHM="random"
MAX_TRIALS="3"
MAX_HOURS=""
SEED="42"
BASE_CONFIG="/app/config/base_optimizer_config.json"
OUTPUT_CONFIG="/shared/flows_params/optimizer_config.json"
SEARCH_SPACE="/app/traffic_optimizer/config/search_space.json"
REPLICATE_SCRIPT="./2.replicate_flow.sh"
REGENERATE_SCRIPT="./3.regenerate_flows.sh"
COMPARE_SCRIPT="./4.compare_flows.sh"
BUILD_OPTIMIZER="1"

while [ $# -gt 0 ]; do
  case "$1" in
    --algorithm)
      ALGORITHM="${2:?manca valore per --algorithm}"; shift 2 ;;
    --max-trials)
      MAX_TRIALS="${2:?manca valore per --max-trials}"; shift 2 ;;
    --max-hours)
      MAX_HOURS="${2:?manca valore per --max-hours}"; shift 2 ;;
    --seed)
      SEED="${2:?manca valore per --seed}"; shift 2 ;;
    --base-config)
      BASE_CONFIG="${2:?manca valore per --base-config}"; shift 2 ;;
    --output-config)
      OUTPUT_CONFIG="${2:?manca valore per --output-config}"; shift 2 ;;
    --search-space)
      SEARCH_SPACE="${2:?manca valore per --search-space}"; shift 2 ;;
    --replicate-script)
      REPLICATE_SCRIPT="${2:?manca valore per --replicate-script}"; shift 2 ;;
    --regenerate-script)
      REGENERATE_SCRIPT="${2:?manca valore per --regenerate-script}"; shift 2 ;;
    --compare-script)
      COMPARE_SCRIPT="${2:?manca valore per --compare-script}"; shift 2 ;;
    --no-build)
      BUILD_OPTIMIZER="0"; shift ;;
    --help|-h)
      usage; exit 0 ;;
    *)
      echo "Opzione non riconosciuta: $1" >&2
      usage
      exit 1 ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"


if [ ! -x "$REPLICATE_SCRIPT" ]; then
  echo "Errore: script replica non eseguibile: $REPLICATE_SCRIPT" >&2
  exit 1
fi
if [ ! -x "$REGENERATE_SCRIPT" ]; then
  echo "Errore: script rigenerazione non eseguibile: $REGENERATE_SCRIPT" >&2
  exit 1
fi
if [ ! -x "$COMPARE_SCRIPT" ]; then
  echo "Errore: script confronto non eseguibile: $COMPARE_SCRIPT" >&2
  exit 1
fi

#mkdir -p optimizer_state shared/results shared/flows_params
STATE_DIR="optimizer_state/"
STOP_FILE="$STATE_DIR/STOP"
REPORT_PATH_HOST="results/$TEST_NAME/report_data.json"
REPORT_PATH_CONTAINER="results/$TEST_NAME/report_data.json"

compose_optimizer() {
  docker compose run --rm -T \
    optimizer \
    python3 -m traffic_optimizer.host_step "$@"
}

if [ "$BUILD_OPTIMIZER" = "1" ]; then
  echo "[build] docker compose build optimizer"
  docker compose build optimizer
fi

START_EPOCH="$(date +%s)"

printf '\n==============================================\n'
printf ' Flow Simulation Optimizer - host orchestrated\n'
printf '==============================================\n'
printf 'Test             : %s\n' "$TEST_NAME"
printf 'Algorithm        : %s\n' "$ALGORITHM"
printf 'Max trials       : %s\n' "$MAX_TRIALS"
printf 'Max hours        : %s\n' "${MAX_HOURS:-none}"
printf 'Replicate script : %s\n' "$REPLICATE_SCRIPT"
printf 'Regenerate script: %s\n' "$REGENERATE_SCRIPT"
printf 'Compare script   : %s\n' "$COMPARE_SCRIPT"
printf 'Stop file        : %s\n' "$STOP_FILE"
printf '\n'

while true; do
  if [ -f "$STOP_FILE" ]; then
    echo "[stop] trovato stop-file: $STOP_FILE"
    exit 0
  fi

  if [ -n "$MAX_HOURS" ]; then
    NOW="$(date +%s)"
    ELAPSED=$((NOW - START_EPOCH))
    LIMIT="$(awk -v h="$MAX_HOURS" 'BEGIN { printf "%d", h * 3600 }')"
    if [ "$ELAPSED" -ge "$LIMIT" ]; then
      echo "[stop] limite max-hours raggiunto"
      exit 0
    fi
  fi

  echo "[propose] richiesta nuova configurazione"
  compose_optimizer propose "$TEST_NAME" \
    --algorithm "$ALGORITHM" \
    --base-config "$BASE_CONFIG" \
    --output-config "$OUTPUT_CONFIG" \
    --search-space "$SEARCH_SPACE" \
    --state-root "$STATE_DIR" \
    --seed "$SEED" \
    --max-trials "$MAX_TRIALS"
  PROPOSE_RC=$?

  if [ "$PROPOSE_RC" -eq 20 ] || [ "$PROPOSE_RC" -eq 21 ]; then
    echo "[done] optimizer fermato: codice $PROPOSE_RC"
    exit 0
  fi
  if [ "$PROPOSE_RC" -eq 22 ]; then
    echo "[pending] esiste gia un trial pending; rieseguo pipeline e poi observe"
  elif [ "$PROPOSE_RC" -ne 0 ]; then
    echo "[error] propose fallito con codice $PROPOSE_RC" >&2
    exit "$PROPOSE_RC"
  fi

  echo "[pipeline] pulizia report precedente: $REPORT_PATH_HOST"
  rm -f "$REPORT_PATH_HOST"

  PIPELINE_RC=0

  echo "[pipeline] $REPLICATE_SCRIPT $TEST_NAME"
  "$REPLICATE_SCRIPT" "$TEST_NAME" optimizable || PIPELINE_RC=$?

  if [ "$PIPELINE_RC" -eq 0 ]; then
    echo "[pipeline] $REGENERATE_SCRIPT $TEST_NAME"
    "$REGENERATE_SCRIPT" "$TEST_NAME" || PIPELINE_RC=$?
  fi

  if [ "$PIPELINE_RC" -eq 0 ]; then
    echo "[pipeline] $COMPARE_SCRIPT $TEST_NAME"
    "$COMPARE_SCRIPT" "$TEST_NAME" || PIPELINE_RC=$?
  fi

  if [ "$PIPELINE_RC" -ne 0 ]; then
    echo "[warn] pipeline fallita con codice $PIPELINE_RC; salvo comunque il trial come fallito se il report manca"
  fi

  echo "[observe] lettura report e aggiornamento stato"
  compose_optimizer observe "$TEST_NAME" \
    --report-path "$REPORT_PATH_CONTAINER" \
    --state-root "$STATE_DIR" \
    --seed "$SEED"
  OBSERVE_RC=$?

  if [ "$OBSERVE_RC" -ne 0 ]; then
    echo "[warn] observe ha restituito codice $OBSERVE_RC"
    if [ "$PIPELINE_RC" -ne 0 ]; then
      echo "[error] interrompo: pipeline fallita e trial marcato fallito"
      exit "$PIPELINE_RC"
    fi
  fi

  echo
  compose_optimizer status "$TEST_NAME" --state-root "$STATE_DIR" --seed "$SEED" || true
  echo

done
