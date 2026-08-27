#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OSRM_DIR="$ROOT_DIR/data/osrm"
PBF_FILE="$OSRM_DIR/new-york-latest.osm.pbf"
OSRM_FILE="$OSRM_DIR/new-york-latest.osrm"
PBF_URL="${ADAPTIVEROUTE_OSRM_PBF_URL:-https://download.bbbike.org/osm/bbbike/NewYork/NewYork.osm.pbf}"

mkdir -p "$OSRM_DIR"

if [[ ! -f "$PBF_FILE" ]]; then
  echo "Downloading New York OSM extract..."
  curl -L --fail --continue-at - --output "$PBF_FILE.partial" "$PBF_URL"
  mv "$PBF_FILE.partial" "$PBF_FILE"
fi

if [[ -f "$OSRM_FILE" ]]; then
  echo "OSRM data already exists at $OSRM_FILE"
  exit 0
fi

echo "Extracting OSRM graph..."
docker run --rm -t -v "$OSRM_DIR:/data" osrm/osrm-backend:latest \
  osrm-extract -p /opt/car.lua /data/new-york-latest.osm.pbf

echo "Partitioning OSRM graph..."
docker run --rm -t -v "$OSRM_DIR:/data" osrm/osrm-backend:latest \
  osrm-partition /data/new-york-latest.osrm

echo "Customizing OSRM graph..."
docker run --rm -t -v "$OSRM_DIR:/data" osrm/osrm-backend:latest \
  osrm-customize /data/new-york-latest.osrm

echo "OSRM NYC data ready at $OSRM_DIR"
