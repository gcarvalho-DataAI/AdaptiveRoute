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

## Running from VS Code

The repository ships launch configurations and tasks so the common paths are one click away.

### Launch configurations (Run and Debug)

| Configuration | What it starts |
|---|---|
| `AdaptiveRoute: Agentic API` | Uvicorn on `127.0.0.1:8090` under the debugger, reading `.env`. |
| `AdaptiveRoute: Agentic Demo (.env)` | The CLI replanning demo with a sample message. |
| `AdaptiveRoute: LoRA Policy API` | Serves the trained adapter on port 8010. Requires the GPU stack. |
| `AdaptiveRoute: Docker Full Stack` | Runs `docker_up.sh`, waits for the frontend, then opens the browser. |
| `Frontend: Local Dev Server` | `npm run dev` in `frontend/`. Requires npm on the host. |

Compound configurations combine these: `AdaptiveRoute: Backend + Agentic API` starts the local LLM
backend alongside the API, and `AdaptiveRoute: Local Full Stack` adds the frontend dev server.

### Tasks (Run Task)

| Task | Purpose |
|---|---|
| `docker: up` / `docker: down` | Start and stop the default stack. |
| `docker: logs` | Follow `api`, `frontend`, `mongo` and `postgres`. |
| `docker: up gpu` | Start the GPU profile for in-process LoRA loading. |
| `docker: smoke test` | Run `smoke_docker_stack.sh` against the running stack. |
| `osrm: start routing profile` | Prepare OSRM data and start the `osrm` service. |
| `osrm: stop routing profile` / `osrm: logs` | Stop it, or follow its logs. |
| `tests: pytest` | Run the full suite. |
| `rag: ingest docs` / `rag: query` | Index the documentation and query it. |
| `local: free api port` | Stop the API container and fail loudly if port 8090 is still held. |

`local: free api port` exists because the debugger and the Docker `api` container both bind 8090.
Run it before `AdaptiveRoute: Agentic API` if the stack is up.

Note that the launch configurations and several tasks assume a POSIX shell and Linux tooling
(`xdg-open`, `ss`, `rg`). On Windows they need adjustment or WSL.

## OSRM Routing Profile

The map service can use OSRM for road-distance matrices and road-snapped route geometry.

Prepare NYC data:

```bash
./scripts/prepare_osrm_nyc.sh
```

This downloads the New York extract and runs `osrm-extract`, `osrm-partition` and `osrm-customize` in
throwaway containers. It is the slow step, and it is idempotent: if `data/osrm/new-york-latest.osrm`
already exists the script exits immediately, and the download resumes if interrupted.

From VS Code, the task `osrm: start routing profile` runs the same preparation and then starts the
`osrm` service. Companion tasks `osrm: stop routing profile` and `osrm: logs` are also available.

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

### Two things that catch people out

**Starting the container is not enough.** The `osrm` service and the API's routing backend are
separate switches. `osrm: start routing profile` brings the container up, but the API only calls it
when `ADAPTIVEROUTE_MAP_ROUTER_BACKEND=osrm`. The shipped `.env.docker.example` sets `fallback`, so
after starting OSRM you must also set the variable and recreate the API container — otherwise the
container runs unused.

**The fallback is silent.** If OSRM is unreachable, or the backend is left on `fallback`, the system
does not fail: it computes haversine distances and draws straight lines between stops. Nothing in
the logs announces it. The reliable check is the map legend in the frontend, which shows `osrm` when
road routing is active, or the geometry itself — real routes follow streets, fallback geometry does
not.

The default `./scripts/docker_up.sh` does **not** start OSRM. The service is declared under
`profiles: ["routing"]` in `docker-compose.yml`, and Compose silently omits profiled services unless
the profile is requested. To include it in the normal startup path:

```bash
COMPOSE_PROFILES=routing ADAPTIVEROUTE_MAP_ROUTER_BACKEND=osrm ./scripts/docker_up.sh
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
