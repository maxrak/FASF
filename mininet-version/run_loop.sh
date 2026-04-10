#!/bin/bash

ITER=10

for i in $(seq 1 $ITER)
do
    echo "======================================"
    echo "🔁 ITERAZIONE $i"
    echo "======================================"

    # genera nuovi parametri
    docker compose run --rm optimizer

    # esegui pipeline completa
    bash run_pipeline.sh

    sleep 5
done