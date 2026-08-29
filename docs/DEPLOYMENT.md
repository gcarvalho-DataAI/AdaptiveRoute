# Deployment Guide

AdaptiveRoute is designed to run locally with Docker for demonstration and evaluation. The default stack is lightweight and solver-backed. GPU/model-serving options are available but intentionally separate.

## Local Python Setup

```bash
uv sync
uv run pytest
```

Run the API locally:

```bash
uv run uvicorn adaptiveroute.api.app:app --host 127.0.0.1 --port 8090
```

## Docker Stack

Copy the Docker environment example:

```bash
cp .env.docker.example .env.docker
```

Start the default stack:

```bash
./scripts/docker_up.sh
```

The default stack exposes:

| Service | URL / Port | Purpose |
|---|---|---|
| frontend | `http://127.0.0.1:5173` | React operational console. |
| api | `http://127.0.0.1:8090` | FastAPI backend. |
| mongo | `127.0.0.1:27018` | Operational and memory persistence. |
| postgres | `127.0.0.1:5433` | pgvector RAG storage. |

Stop the stack:

```bash
./scripts/docker_down.sh
```

Follow logs:

```bash
./scripts/docker_compose_cmd.sh logs -f api frontend mongo postgres
```

## OSRM Routing Profile

The map service can use OSRM for road-distance matrices and road-snapped route geometry.

Prepare NYC data:

```bash
./scripts/prepare_osrm_nyc.sh
```

From VS Code, you can also use the task `osrm: start routing profile` from the task palette. It runs the same preparation and starts the routing profile automatically.

Start with the routing profile:

```bash
ADAPTIVEROUTE_MAP_ROUTER_BACKEND=osrm \
./scripts/docker_compose_cmd.sh --profile routing up -d --build
```

Relevant variables:

```text
ADAPTIVEROUTE_MAP_ROUTER_BACKEND=osrm
ADAPTIVEROUTE_OSRM_BASE_URL=http://osrm:5000
ADAPTIVEROUTE_OSRM_TIMEOUT_SECONDS=8
```

If OSRM is unavailable, the system can use fallback geometry and haversine distances.

## Local LLM API

The backend expects OpenAI-compatible endpoints when using LLM-based orchestration, route Q&A or the trained routing policy API.

Typical local serving shape:

```text
http://127.0.0.1:8000/v1
  /models
  /chat/completions
```

When the API runs inside Docker, use:

```text
http://host.docker.internal:8000/v1
```

Important variables:

```text
ADAPTIVEROUTE_ORCHESTRATOR_BACKEND=api
ADAPTIVEROUTE_ORCHESTRATOR_BASE_URL=http://host.docker.internal:8000/v1
ADAPTIVEROUTE_ORCHESTRATOR_API_KEY=local
ADAPTIVEROUTE_ORCHESTRATOR_MODEL=chat-local

ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=api
ADAPTIVEROUTE_ROUTING_POLICY_BASE_URL=http://host.docker.internal:8000/v1
ADAPTIVEROUTE_ROUTING_POLICY_API_KEY=local
ADAPTIVEROUTE_ROUTING_POLICY_MODEL=adaptiveroute-routing-policy
```

## GPU / Local LoRA Profile

The GPU profile is intended for loading the trained LoRA adapter directly in the API container.

Copy the GPU environment example:

```bash
cp .env.docker.gpu.example .env.docker.gpu
```

Start:

```bash
./scripts/docker_up_gpu.sh
```

Requirements:

- NVIDIA GPU;
- NVIDIA Container Toolkit;
- trained adapter available under `outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5`;
- model dependencies installed through the training dependency group.

Relevant variables:

```text
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=local
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_ADAPTER_PATH=outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_4BIT=true
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_BF16=true
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_LOAD_AT_STARTUP=false
```

## Demo Credentials

Admin:

```text
admin@adaptiveroute.com
12345678
```

Drivers use credentials created in the driver wizard. Passwords are stored as bcrypt hashes and driver login returns a signed JWT for driver-scoped actions.

## Health Check

```bash
curl -sS http://127.0.0.1:8090/health
```

Expected:

```json
{"status":"ok"}
```

## Frontend Build Validation

When host `npm` is unavailable, validate from the frontend container:

```bash
docker exec adaptiveroute_frontend_1 npm run build -- --outDir /tmp/adaptiveroute-frontend-build-check --emptyOutDir
```

## Data and Artifacts

The following paths are intentionally not committed:

- `.env`;
- `.env.docker`;
- `.env.docker.gpu`;
- `.venv/`;
- `data/`;
- `outputs/`;
- training/evaluation logs;
- `frontend/node_modules/`;
- `frontend/dist/`.

This prevents accidental commits of local secrets, generated datasets, OSRM files and model weights.
