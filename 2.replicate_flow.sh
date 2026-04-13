#!/bin/bash

docker compose run --rm mininet python3 /app/replay_topology.py topologies/$1.json 60 flows/$1 20