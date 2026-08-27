#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env.docker.gpu ]]; then
  cp .env.docker.gpu.example .env.docker.gpu
fi

if ! ./scripts/docker_compose_cmd.sh --profile gpu up -d --build api-gpu mongo postgres frontend; then
  echo "docker compose up failed; cleaning stale AdaptiveRoute GPU API containers and retrying." >&2
  mapfile -t STALE_API_CONTAINERS < <(
    docker ps -a --format '{{.ID}} {{.Names}}' \
      | awk '$2 == "adaptiveroute_api-gpu_1" || $2 ~ /_adaptiveroute_api-gpu_1$/ {print $1}'
  )
  if [[ ${#STALE_API_CONTAINERS[@]} -gt 0 ]]; then
    docker container rm --force "${STALE_API_CONTAINERS[@]}"
  fi
  ./scripts/docker_compose_cmd.sh --profile gpu up -d --build api-gpu mongo postgres frontend
fi
