#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env.docker ]]; then
  cp .env.docker.example .env.docker
fi

if ! ./scripts/docker_compose_cmd.sh up -d --build; then
  echo "docker compose up failed; cleaning stale AdaptiveRoute API containers and retrying." >&2
  mapfile -t STALE_API_CONTAINERS < <(
    docker ps -a --format '{{.ID}} {{.Names}}' \
      | awk '$2 == "adaptiveroute_api_1" || $2 ~ /_adaptiveroute_api_1$/ {print $1}'
  )
  if [[ ${#STALE_API_CONTAINERS[@]} -gt 0 ]]; then
    docker container rm --force "${STALE_API_CONTAINERS[@]}"
  fi
  ./scripts/docker_compose_cmd.sh up -d --build
fi
