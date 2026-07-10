#!/usr/bin/env bash
set -euo pipefail

TEST_NAME="${1:-test5}"
ALGORITHM="${2:-random}"
BASE_CONFIG="${BASE_CONFIG:-optimizer_config_template.json}"
OUTPUT_CONFIG="${OUTPUT_CONFIG:-optimizer_config.json}"
MAX_TRIALS="${MAX_TRIALS:-30}"

python3 -m traffic_optimizer.optimize "$TEST_NAME" \
  --base-config "$BASE_CONFIG" \
  --output-config "$OUTPUT_CONFIG" \
  --search-space traffic_optimizer/config/search_space.json \
  --algorithm "$ALGORITHM" \
  --max-trials "$MAX_TRIALS" \
  --resume
