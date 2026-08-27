# AdaptiveRoute Agentic API, Memory, and Docker Implementation Plan

This is the working checklist for converting AdaptiveRoute from a local engine/agentic PoC into a runnable backend application with conversation memory, context-window management, and Docker-based setup.

## Objective

Build a FastAPI-based Agentic AI backend that:

- exposes the AdaptiveRoute LangGraph workflow through HTTP;
- persists full conversation history in MongoDB;
- maintains a rolling context window for each conversation;
- stores agent runs, traces, route plans, validations, and errors for auditability;
- supports the trained routing policy either through an API or by loading the LoRA adapter directly in-process;
- can be started by a tester with Docker using a small number of commands.

## Current Baseline

Implemented:

- Pyomo + HiGHS routing engine.
- Deterministic validation, repair, comparison, and solver fallback.
- LangGraph agentic workflow.
- Generic `RoutingWorkflowAgent` base class and specialized workflow agents.
- OpenAI-compatible client.
- Routing policy backend modes:
  - `solver`
  - `api`
  - `local`
- `.env` / `.env.example` support.
- FastAPI wrapper script: `scripts/serve_agentic_api.py`.
- VS Code launch/tasks for local development.
- Lightweight Vite frontend.
- Dockerfile, Docker Compose, Docker env examples, and Docker helper scripts.
- Postgres + pgvector RAG backend for project/tool/model/solver documentation.

The temporary HTTP script has been replaced by a uvicorn/FastAPI wrapper.

## Target Architecture

```text
Frontend
  ↓
FastAPI Agentic Backend
  ↓
Conversation Service
  ├── MongoDB: full message history
  ├── MongoDB: rolling context window / summaries
  └── AgenticRoutingService / LangGraph
        ├── Orchestrator LLM
        ├── Routing policy model
        ├── Pyomo + HiGHS solver
        ├── validator
        └── repair/fallback
```

## Engineering Principle

Keep business logic out of the API and persistence layers.

Correct dependency direction:

```text
FastAPI routes
  ↓
Application services
  ↓
Agentic workflow / solver / validator
  ↓
Domain models
```

MongoDB should not be called directly from workflow agents. Agents should remain deterministic, testable units that operate on input state and return partial state updates.

## Configuration

Required runtime variables:

```env
ADAPTIVEROUTE_API_HOST=0.0.0.0
ADAPTIVEROUTE_API_PORT=8090

MONGODB_URI=mongodb://mongo:27017
MONGODB_DATABASE=adaptiveroute

ADAPTIVEROUTE_CONTEXT_RECENT_MESSAGES=8
ADAPTIVEROUTE_CONTEXT_SUMMARY_MAX_CHARS=4000
```

Routing policy backend options:

```env
# deterministic fallback, safest for any tester machine
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=solver

# trained LoRA behind an OpenAI-compatible API
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=api
ADAPTIVEROUTE_ROUTING_POLICY_BASE_URL=http://127.0.0.1:8000/v1
ADAPTIVEROUTE_ROUTING_POLICY_API_KEY=local
ADAPTIVEROUTE_ROUTING_POLICY_MODEL=adaptiveroute-routing-policy

# trained LoRA loaded directly in-process
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=local
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_ADAPTER_PATH=outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_4BIT=true
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_BF16=true
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_LOAD_AT_STARTUP=false
```

## Workstream 1 — FastAPI Backend

Owner: Backend / AI Engineer

Create:

```text
src/adaptiveroute/api/
  __init__.py
  app.py
  routes.py
  schemas.py
  dependencies.py
  settings.py
```

Required endpoints:

```http
GET  /health
POST /v1/conversations
GET  /v1/conversations/{conversation_id}
GET  /v1/conversations/{conversation_id}/messages
POST /v1/conversations/{conversation_id}/messages
GET  /v1/conversations/{conversation_id}/context
POST /v1/agentic/replan
```

Primary request:

```json
{
  "conversation_id": "optional",
  "message": "Customer C3 cannot receive now.",
  "scenario_id": "demo-cvrp-8"
}
```

Primary response:

```json
{
  "conversation_id": "...",
  "assistant_message": "...",
  "agentic_result": {},
  "context_window": {},
  "trace": []
}
```

Checklist:

- [x] Add FastAPI dependencies.
- [x] Implement app factory.
- [x] Implement settings.
- [x] Implement health endpoint.
- [x] Implement request/response schemas.
- [x] Implement replan endpoint.
- [x] Replace `scripts/serve_agentic_api.py` with FastAPI/uvicorn script or keep it only as a compatibility wrapper.
- [x] Update VS Code launch config to run uvicorn.

## Workstream 2 — MongoDB Memory Layer

Owner: Backend Engineer

Create:

```text
src/adaptiveroute/memory/
  __init__.py
  models.py
  repository.py
  service.py
  context.py
```

Collections:

### `conversations`

```json
{
  "_id": "uuid",
  "title": "Routing incident - C3 unavailable",
  "created_at": "...",
  "updated_at": "...",
  "metadata": {
    "scenario_id": "demo-cvrp-8"
  }
}
```

### `messages`

```json
{
  "_id": "uuid",
  "conversation_id": "uuid",
  "role": "user|assistant|system|tool",
  "content": "...",
  "created_at": "...",
  "metadata": {
    "agent": "routing_orchestrator",
    "trace_id": "...",
    "tokens_estimate": 123
  }
}
```

### `context_windows`

```json
{
  "_id": "uuid",
  "conversation_id": "uuid",
  "summary": "...",
  "recent_message_ids": ["..."],
  "facts": [],
  "open_constraints": [],
  "last_event": {},
  "last_plan": {},
  "updated_at": "..."
}
```

### `agent_runs`

```json
{
  "_id": "uuid",
  "conversation_id": "uuid",
  "input_message_id": "uuid",
  "status": "succeeded|failed",
  "trace": [],
  "result": {},
  "created_at": "..."
}
```

Checklist:

- [x] Add Mongo dependency.
- [x] Create repository protocol/interface.
- [x] Create Mongo repository implementation.
- [x] Add indexes:
  - [x] `messages.conversation_id + created_at`
  - [x] `agent_runs.conversation_id + created_at`
  - [x] `context_windows.conversation_id`
- [x] Implement create conversation.
- [x] Implement get conversation.
- [x] Implement append message.
- [x] Implement list messages.
- [x] Implement save agent run.
- [x] Implement get/update context window.
- [x] Add repository tests.

## Workstream 3 — Context Window and Summarization

Owner: AI Engineer

Two memory types:

1. Full memory:
   - all user messages;
   - all assistant messages;
   - tool/agent run traces;
   - plans;
   - validation results;
   - errors.

2. Context window:
   - rolling summary;
   - current scenario constraints;
   - active event state;
   - last accepted route plan;
   - last N user/assistant messages.

Initial implementation should not require an LLM summarizer. Use deterministic summarization first:

- keep last event;
- keep last final plan;
- keep last validation status;
- keep recent message IDs;
- cap summary string by character budget.

Later refinement:

- use orchestrator LLM to update the summary;
- store both old summary and updated summary;
- log summary generation as a system/tool message.

Checklist:

- [x] Define `ContextWindow` domain object.
- [x] Implement deterministic context builder.
- [x] Implement context update after every replan request.
- [x] Persist context in MongoDB.
- [x] Add summary size cap.
- [x] Add tests for context rollover.
- [x] Add tests for last plan/event retention.

## Workstream 4 — Conversation Service

Owner: Backend / AI Engineer

Create service that orchestrates:

```text
request
  ↓
resolve or create conversation
  ↓
save user message
  ↓
load context window
  ↓
run AgenticRoutingService
  ↓
save agent run
  ↓
save assistant message
  ↓
update context window
  ↓
return response
```

Checklist:

- [x] Implement `ConversationService`.
- [x] Support new conversation when `conversation_id` is absent.
- [x] Support existing conversation when `conversation_id` is provided.
- [x] Attach current context to agentic request path.
- [x] Save full trace.
- [x] Save validation and final plan.
- [x] Save error state if workflow fails.
- [x] Return context window in API response for visibility.

## Workstream 5 — Docker

Owner: Backend / DevOps Engineer

Create:

```text
Dockerfile
docker-compose.yml
.dockerignore
.env.docker.example
scripts/docker_up.sh
scripts/docker_down.sh
```

Services:

```yaml
services:
  api:
    build: .
    ports:
      - "8090:8090"
    env_file:
      - .env.docker
    depends_on:
      - mongo
    volumes:
      - ./outputs:/app/outputs
      - ./data:/app/data

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
```

Recommended profiles:

### CPU/light profile

Use:

```env
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=solver
```

Goal: any tester can run the app without GPU/model downloads.

### GPU/local-LoRA profile

Use:

```env
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=local
```

Requires:

- NVIDIA driver;
- NVIDIA Container Toolkit;
- model adapter available under `outputs/models/...`;
- image with Torch, Transformers, PEFT, BitsAndBytes.

Checklist:

- [x] Add Dockerfile for API.
- [x] Add compose file with API + Mongo.
- [x] Add `.dockerignore`.
- [x] Add `.env.docker.example`.
- [x] Add CPU/light profile.
- [x] Add GPU profile.
- [x] Validate `docker compose up`.
- [x] Validate `/health`.
- [x] Validate `/v1/agentic/replan`.

## Workstream 6 — Tests

Owner: Backend / QA Engineer

Required tests:

- [x] API health endpoint.
- [x] Create conversation.
- [x] Append/list messages.
- [x] Context window creation.
- [x] Context window update after replan.
- [x] Agent run persistence.
- [x] Replan endpoint with solver backend.
- [x] Replan endpoint with fake API routing policy.
- [x] Mongo repository integration test.
- [x] Docker smoke test documentation.

Avoid loading the real LoRA model in unit tests.

## Workstream 7 — Developer Experience

Owner: Backend Engineer

Checklist:

- [x] Update `.vscode/launch.json` to run FastAPI.
- [x] Add VS Code task for Docker up/down.
- [x] Add README commands.
- [x] Add troubleshooting section:
  - [x] Mongo unavailable.
  - [x] LoRA adapter missing.
  - [x] GPU OOM.
  - [x] API routing model unavailable.
  - [x] fallback to solver.

## Workstream 8 — RAG Documentation Retrieval

Owner: AI / Backend Engineer

Implemented scope:

- [x] Add Postgres + pgvector to Docker Compose.
- [x] Add configurable RAG backend:
  - [x] `memory`
  - [x] `pgvector`
- [x] Add configurable embedding backend:
  - [x] deterministic `hash`
  - [x] OpenAI-compatible `api`
- [x] Add document/chunk models.
- [x] Add chunking for `.md`, `.txt`, `.tex`, `.py`, `.json`, `.yaml`, `.yml`, `.toml`.
- [x] Add ingestion service.
- [x] Add retrieval service.
- [x] Add FastAPI endpoints:
  - [x] `POST /v1/rag/ingest`
  - [x] `GET /v1/rag/documents`
  - [x] `POST /v1/rag/query`
- [x] Add CLI scripts:
  - [x] `scripts/ingest_rag_documents.py`
  - [x] `scripts/query_rag.py`
- [x] Add frontend buttons for RAG ingest/query.
- [x] Add Docker smoke test covering pgvector ingest/query.

Remaining refinement:

- [ ] Connect RAG retrieval as an explicit specialized-agent tool.
- [ ] Add source citation formatting to orchestrator responses.
- [ ] Add document delete/reindex endpoint.
- [ ] Add real embedding model in Docker profile if required by demo.
- [ ] Re-enable `embed-local` in the local LLM API when VRAM budget allows.

## Workstream 9 — Operational Ecosystem: Orders, Planning, Drivers, Portal

Owner: Backend / Frontend Engineer

Implemented scope:

- [x] Add driver domain model and repository.
- [x] Add driver CRUD API:
  - [x] `POST /v1/drivers`
  - [x] `GET /v1/drivers`
  - [x] `GET /v1/drivers/{driver_id}`
- [x] Add mock driver authentication for the PoC.
- [x] Add driver portal endpoints:
  - [x] `POST /v1/driver-portal/login`
  - [x] `POST /v1/driver-portal/routes/{route_id}/status`
- [x] Enforce route-level visibility/update rules for drivers.
- [x] Add scenario creation from structured orders:
  - [x] `POST /v1/scenarios/from-orders`
- [x] Add scenario creation from uploaded spreadsheet:
  - [x] `POST /v1/scenarios/from-orders-file`
  - [x] CSV support.
  - [x] XLSX support.
- [x] Calculate scenario distance matrices before solver execution.
- [x] Use OSRM `/table` distances when the routing backend is configured as `osrm`.
- [x] Fall back to haversine distance when OSRM is unavailable or disabled.
- [x] Add daily planning service that runs the traditional Pyomo + HiGHS solver.
- [x] Persist solver output as operational routes assigned to drivers.
- [x] Mark assigned drivers as `on_route`.
- [x] Add React admin flow:
  - [x] Dashboard with solver play action.
  - [x] Scenario management with daily-order feed import.
  - [x] Scenario management with CSV/XLSX upload.
  - [x] Driver wizard for user/vehicle/capacity/access creation.
  - [x] Driver portal with assigned-route-only visibility.

Known limitations:

- [ ] Spreadsheet import requires delivery latitude/longitude. Address-only geocoding is not implemented yet.
- [ ] Driver authentication is mock-only; production must hash passwords and issue signed tokens.
- [ ] Planning currently considers all available drivers in the repository. Add planning-session filters when fleet pools/regions/shifts need isolation.
- [ ] Driver route editing is status-only. Add stop-level exception capture and approval workflow if required.
- [ ] Add admin CRUD for editing/deleting drivers and scenarios after creation.

## Implementation Order

1. [x] Add dependencies and FastAPI skeleton.
2. [x] Implement settings.
3. [x] Implement Mongo memory repository.
4. [x] Implement context window service.
5. [x] Implement conversation service.
6. [x] Implement `/v1/agentic/replan`.
7. [x] Add tests with solver backend.
8. [x] Add Dockerfile and compose.
9. [x] Update VS Code launch/tasks.
10. [x] Validate local run.
11. [x] Validate Docker light profile.
12. [x] Add operational orders → scenario → solver → routes → driver portal flow.
13. [ ] Validate GPU/local-LoRA profile if hardware supports it.

## Acceptance Criteria

Minimum acceptable PoC:

- [x] `docker compose up` starts API + Mongo.
- [x] `GET /health` returns status ok.
- [x] `POST /v1/agentic/replan` returns a valid replanning result.
- [x] Mongo stores conversation, messages, context window, and agent run.
- [x] Postgres + pgvector stores documentation chunks.
- [x] RAG query returns retrieved documentation chunks.
- [x] The context endpoint shows the rolling summary/window.
- [x] The system can run without the tester having access to the developer's local LLM API by using either `solver` or `local` backend.
- [x] Admin can create a scenario from orders, run the solver, and expose assigned operational routes.
- [x] Driver can authenticate and see/update only assigned routes.

Stronger demo target:

- [x] VS Code can start backend, agentic API, and frontend.
- [x] Frontend can create/select conversations.
- [x] Frontend can show full history and context window separately.
- [x] Frontend can show trace and validation details.
- [x] Frontend can upload CSV/XLSX demand data and trigger solver planning.
- [ ] Docker GPU profile can load the trained LoRA adapter directly.
