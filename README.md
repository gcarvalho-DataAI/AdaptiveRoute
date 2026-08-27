# AdaptiveRoute

AdaptiveRoute is a small routing replanning engine for last-mile logistics. The first milestone is a deterministic CVRP core: a synthetic scenario is solved by Pyomo + HiGHS, converted into route plans, and checked by an independent validator.

## Setup

```bash
uv sync
```

## Run The Demo

```bash
uv run python scripts/solve_demo.py
```

## Run Tests

```bash
uv run pytest
```

## Generate Synthetic Scenarios

```bash
uv run python scripts/generate_scenarios.py --n 10 --num-customers 8
```

## Build SFT Dataset

```bash
uv run python scripts/build_sft_dataset.py --n 100 --num-customers 8 --out-dir data/training
uv run python scripts/build_sft_dataset.py --n 100 --num-customers 8 --out-dir data/training_compact --format compact
uv run python scripts/build_sft_dataset_chunked.py --n 1000 --chunk-size 100 --num-customers 8 --out-dir data/training_compact --format compact
uv run python scripts/build_sft_dataset_chunked.py --n 20000 --chunk-size 100 --num-customers 8 --out-dir data/training_compact_20k --format compact --resume
```

The generated dataset is reproducible by seed and intentionally ignored by git. Each row contains a base scenario, the base optimal plan, an operational event, a validated replanned route, and metadata.

## Replan Demo

```bash
uv run python scripts/replan_demo.py
```

## Counterfactual Demo

```bash
uv run python scripts/evaluate_counterfactual.py
```

## Trace Demo

```bash
uv run python scripts/trace_demo.py
```

## Natural Language Harness Demo

```bash
uv run python scripts/harness_demo.py "Customer C3 cannot receive now."
uv run python scripts/harness_demo.py "There was an accident between C7 and C6. Avoid that road."
```

## Agentic Replanning Demo

```bash
uv run python scripts/agentic_replan_demo.py "There was an accident between C7 and C6. Avoid that road."
uv run python scripts/agentic_replan_demo.py "Customer C3 cannot receive now."
```

The agentic workflow is implemented with LangGraph. It extracts the event, solves the base scenario, applies the mutation, generates a candidate route, validates it, attempts conservative repair, and falls back to Pyomo + HiGHS when needed.

Workflow nodes are implemented as subclasses of `RoutingWorkflowAgent`. This keeps the LangGraph wiring thin while giving each agent a clear responsibility and a shared execution contract for trace/error handling.

By default, the workflow uses deterministic rule-based event extraction. To use an OpenAI-compatible orchestrator model for event extraction:

```bash
uv run python scripts/agentic_replan_demo.py \
  --llm-orchestrator \
  --base-url http://127.0.0.1:8000/v1 \
  --api-key local \
  --model auto \
  "The road between C7 and C6 is blocked."
```

Equivalent environment variables:

```bash
export ADAPTIVEROUTE_ORCHESTRATOR_BASE_URL="http://127.0.0.1:8000/v1"
export ADAPTIVEROUTE_ORCHESTRATOR_API_KEY="local"
export ADAPTIVEROUTE_ORCHESTRATOR_MODEL="auto"
```

The same client contract can be used with a local Qwen/llama.cpp/vLLM server or with an external OpenAI-compatible provider such as Kimi/Moonshot. The LLM extractor is still guarded by deterministic validation and falls back to rule-based extraction if the provider returns an invalid event.

The routing policy model can run in three modes configured through `.env` or exported environment variables:

```bash
# Uses Pyomo + HiGHS as the deterministic candidate generator.
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=solver

# Calls the trained LoRA through an OpenAI-compatible API.
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=api
ADAPTIVEROUTE_ROUTING_POLICY_BASE_URL=http://127.0.0.1:8000/v1
ADAPTIVEROUTE_ROUTING_POLICY_API_KEY=local
ADAPTIVEROUTE_ROUTING_POLICY_MODEL=adaptiveroute-routing-policy

# Loads the trained LoRA adapter directly in the app process.
# This is the preferred mode when a tester does not have access to your local API.
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=local
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_ADAPTER_PATH=outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_LOAD_AT_STARTUP=false
```

To run the demo from `.env`:

```bash
uv run --group train python scripts/agentic_replan_demo.py --from-env "Customer C3 cannot receive now."
```

Set `ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_LOAD_AT_STARTUP=true` if the application should fail fast during startup when the local adapter cannot be loaded.

## FastAPI Agentic Backend

Run the API locally:

```bash
uv run uvicorn adaptiveroute.api.app:app --host 127.0.0.1 --port 8090
```

Primary endpoint:

```bash
curl -sS http://127.0.0.1:8090/v1/agentic/replan \
  -H 'Content-Type: application/json' \
  -d '{"message":"Customer C3 cannot receive now."}' | python3 -m json.tool
```

The API persists:

- conversations;
- messages;
- agent runs;
- trace payloads;
- context windows.

Operational scenario and route assignment APIs are exposed through:

```bash
curl -sS -X POST http://127.0.0.1:8090/v1/scenarios/demo | python3 -m json.tool

curl -sS -X POST http://127.0.0.1:8090/v1/operational-routes \
  -H 'Content-Type: application/json' \
  -d '{"id":"ROUTE-001","driver_id":"DRIVER-001","scenario_id":"demo-cvrp-8","status":"in_progress"}' \
  | python3 -m json.tool

curl -sS http://127.0.0.1:8090/v1/operational-routes/ROUTE-001 | python3 -m json.tool
```

Operational routes associate a driver-facing `route_id` with a stored scenario
and the current plan. A driver can say:

```text
Preciso que refaça minha rota ROUTE-001, há um bloqueio entre C1 e C3.
```

The API extracts `ROUTE-001`, resolves the associated scenario, runs the
agentic replanning workflow, persists the mutated scenario, and updates the
route's `current_plan`.

RAG documentation retrieval is exposed through:

```bash
curl -sS http://127.0.0.1:8090/v1/rag/ingest \
  -H 'Content-Type: application/json' \
  -d '{"paths":["README.md","docs"]}' | python3 -m json.tool

curl -sS http://127.0.0.1:8090/v1/rag/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"How does the routing policy model work?","limit":3}' | python3 -m json.tool
```

Memory backend is controlled by:

```env
ADAPTIVEROUTE_MEMORY_BACKEND=memory
# or
ADAPTIVEROUTE_MEMORY_BACKEND=mongo
MONGODB_URI=mongodb://mongo:27017
MONGODB_DATABASE=adaptiveroute
```

RAG backend is controlled by:

```env
ADAPTIVEROUTE_RAG_BACKEND=memory
# or
ADAPTIVEROUTE_RAG_BACKEND=pgvector
ADAPTIVEROUTE_RAG_POSTGRES_DSN=postgresql://adaptiveroute:adaptiveroute@postgres:5432/adaptiveroute

# deterministic fallback
ADAPTIVEROUTE_RAG_EMBEDDING_BACKEND=hash

# OpenAI-compatible embeddings
ADAPTIVEROUTE_RAG_EMBEDDING_BACKEND=api
ADAPTIVEROUTE_RAG_EMBEDDING_BASE_URL=http://127.0.0.1:8000/v1
ADAPTIVEROUTE_RAG_EMBEDDING_API_KEY=local
ADAPTIVEROUTE_RAG_EMBEDDING_MODEL=embed-local
ADAPTIVEROUTE_RAG_EMBEDDING_DIM=384
```

Local CLI:

```bash
uv run python scripts/ingest_rag_documents.py README.md docs
uv run python scripts/query_rag.py "How does the solver fallback work?"
```

## Frontend

A lightweight Vite frontend is available in `frontend/`.

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Docker

Lightweight profile, no GPU/model required:

```bash
cp .env.docker.example .env.docker
./scripts/docker_up.sh
```

This starts:

- FastAPI backend on `http://127.0.0.1:8090`;
- MongoDB on `localhost:27018` externally and `mongo:27017` inside Docker;
- Postgres + pgvector on `localhost:5433` externally and `postgres:5432` inside Docker;
- frontend on `http://127.0.0.1:5173`.

Stop:

```bash
./scripts/docker_down.sh
```

Smoke test:

```bash
./scripts/smoke_docker_stack.sh
```

GPU profile for loading the LoRA directly in the container:

```bash
cp .env.docker.gpu.example .env.docker.gpu
./scripts/docker_up_gpu.sh
```

The GPU profile requires NVIDIA Container Toolkit and the trained adapter under `outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5`.

## Troubleshooting

Mongo unavailable:

- use `ADAPTIVEROUTE_MEMORY_BACKEND=memory` for local smoke tests;
- in Docker, check `./scripts/docker_compose_cmd.sh ps`;
- Mongo is exposed on `localhost:27018` to avoid collisions with a host Mongo on `27017`.

LoRA adapter missing:

- use `ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=solver`;
- or place the adapter at `outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5`;
- then run with `uv run --group train ...`.

GPU OOM:

- use `solver` backend for the demo;
- use `api` backend if the model is served elsewhere;
- keep `ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_LOAD_AT_STARTUP=false` for lazy loading.

API routing model unavailable:

- the workflow records the policy error and falls back to Pyomo + HiGHS;
- check `/v1/models` on the configured OpenAI-compatible endpoint;
- check `ADAPTIVEROUTE_ROUTING_POLICY_BASE_URL` and `ADAPTIVEROUTE_ROUTING_POLICY_MODEL`.

Fallback to solver:

- intentional behavior when the routing policy fails or returns an invalid route;
- final plans still pass deterministic validation before being returned.

## Audit And Prepare Training Data

```bash
uv run python scripts/audit_sft_dataset.py data/training_compact
uv run python scripts/prepare_chat_dataset.py data/training_compact --out-dir data/chat_training_compact --format messages
uv run python scripts/merge_sft_datasets.py data/training_compact_20k data/training_compact_20k_part2 --out-dir data/training_compact_30k --shuffle-seed 42
```

See [docs/TRAINING.md](docs/TRAINING.md) for the LoRA/QLoRA workflow and [docs/MODEL_DECISION.md](docs/MODEL_DECISION.md) for the selected routing policy model.
See [docs/AGENTIC_API_MEMORY_DOCKER_PLAN.md](docs/AGENTIC_API_MEMORY_DOCKER_PLAN.md) for the FastAPI, MongoDB memory, context-window, and Docker implementation plan.

## Evaluate Model Predictions

```bash
uv run python scripts/evaluate_predictions.py \
  --dataset data/training_compact_30k/sft_test.jsonl \
  --predictions outputs/predictions/smoke_lora_test.jsonl \
  --details-out outputs/predictions/smoke_lora_eval_details.jsonl
```

## Current Scope

Implemented:

- Small synthetic CVRP scenario.
- Pyomo + HiGHS routing engine.
- Independent route validation.
- CLI demo.
- Synthetic scenario generator.
- Structured mutations for blocked arcs, unavailable customers, and priority changes.
- SFT dataset builder for replanning examples.
- Plan comparison for original vs replanned routes.
- Counterfactual route analysis for user-proposed sequences.
- Replanning service that orchestrates solve, mutation, replan, validation, comparison, and report output.
- JSONL trace logging for harness observability.
- Rule-based event extraction with an LLM-compatible interface.
- End-to-end harness from natural language event to validated replan.
- Dataset audit for compact SFT rows.
- Chat/messages dataset conversion for LoRA-style training.
- Optional LoRA/QLoRA training and prediction scripts.
- Deterministic evaluation for model route predictions.
- Selected LoRA v5 routing policy model for candidate generation.
- LangGraph-based agentic replanning workflow with validation, repair, and solver fallback.
- Generic `RoutingWorkflowAgent` base class with specialized workflow agents for extraction, solving, mutation, candidate generation, validation, repair, fallback, and response composition.
- OpenAI-compatible orchestrator client with LLM event extraction and rule-based fallback.
- Basic tests.

Next:

- `LLMRoutingEngine` backed by the selected LoRA v5 adapter.
- API/UI integration for the agentic workflow.
