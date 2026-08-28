# Software Engineering Design

AdaptiveRoute is structured as a modular Python application with a React frontend. The implementation favors explicit boundaries over implicit framework coupling. This is intentional: optimization, LLM calls, validation, storage and UI behavior need to be independently testable.

## Design Principles

### Keep the LLM outside the trust boundary

LLM-generated route candidates are not accepted directly. They must pass deterministic validation. This keeps the system robust when the model omits customers, violates capacity or produces malformed outputs.

### Separate domain logic from transport

FastAPI routes are thin orchestration wrappers. The actual behavior lives in services, repositories and domain modules. This keeps HTTP concerns separate from route planning and agentic logic.

### Make backends swappable

The system supports interchangeable implementations for:

- memory backend: in-memory or MongoDB;
- RAG backend: in-memory or pgvector;
- routing policy: solver, OpenAI-compatible API or local LoRA;
- map routing: OSRM or fallback geometry/distance;
- event extraction: rules or OpenAI-compatible LLM.

This is useful for tests, local development, GPU experiments and demo environments.

### Validate with independent code

The validator is separate from the solver and the model. This avoids using the same component to both produce and judge a plan.

## Package Layout

```text
src/adaptiveroute/
  agentic/      LangGraph workflow, agent classes, candidate generators, repair logic
  api/          FastAPI application, routes, schemas and dependency wiring
  data/         Demo and synthetic scenario generation
  domain/       Core dataclasses and serialization
  drivers/      Driver records, authentication metadata and repository/service layer
  llm/          OpenAI-compatible client abstraction
  maps/         OSRM/fallback route geometry and distance matrix
  memory/       Conversations, messages, context windows, route Q&A and traces
  operations/   Operational route records and current-plan persistence
  orders/       Spreadsheet/order ingestion
  planning/     Daily planning and async job lifecycle
  rag/          Document chunking, embeddings, pgvector/memory stores
  scenarios/    Scenario repository/service layer
  services/     Solver-independent route operations, validation and reports
  solvers/      Pyomo + HiGHS engine
  training/     Dataset generation, prompt formatting, audit and prediction evaluation
```

## Service and Repository Pattern

Persistence is hidden behind repository protocols. Services depend on repository interfaces rather than direct MongoDB calls.

Examples:

- `ConversationService` uses a conversation repository and stores messages, context windows and agent runs.
- `DriverService` manages driver records and credential metadata.
- `OperationalRouteService` manages route records and current plans.
- `PlanningJobService` manages async job records.
- `RagService` stores and retrieves document chunks.

This makes unit tests fast because they can use in-memory repositories.

## Agent Base Class

All workflow nodes inherit from `RoutingWorkflowAgent`. The base class provides:

- a shared `name`;
- callable behavior for LangGraph;
- a `run` method contract;
- trace helper;
- error helper.

Specialized agents implement only one responsibility. This keeps the graph readable and makes failures easier to isolate.

## Configuration

Runtime configuration is environment-driven. Important variables include:

```text
ADAPTIVEROUTE_MEMORY_BACKEND
ADAPTIVEROUTE_RAG_BACKEND
ADAPTIVEROUTE_RAG_EMBEDDING_BACKEND
ADAPTIVEROUTE_ORCHESTRATOR_BACKEND
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND
ADAPTIVEROUTE_MAP_ROUTER_BACKEND
ADAPTIVEROUTE_SOLVER_TIME_LIMIT_SECONDS
ADAPTIVEROUTE_SOLVER_MIP_GAP
```

Example files:

- `.env.example`;
- `.env.docker.example`;
- `.env.docker.gpu.example`.

## Testing Strategy

The test suite covers:

- solver feasibility;
- plan validation;
- event extraction;
- replanning service behavior;
- agentic workflow;
- API behavior;
- driver and planning APIs;
- memory service;
- RAG service/API;
- map API;
- OpenAI-compatible client behavior;
- training dataset and prediction evaluation utilities.

Recommended smoke test set:

```bash
uv run pytest tests/test_memory_service.py tests/test_agentic_routing.py tests/test_drivers_and_planning_api.py tests/test_map_api.py
uv run pytest --forked tests/test_pyomo_highs_solver.py tests/test_plan_validation.py
```

Full test run:

```bash
uv run pytest
```

## Current PoC Trade-offs

The implementation is intentionally pragmatic. Known trade-offs:

- authentication is simplified for PoC usage;
- admin authentication is still frontend-only for demo usage;
- driver JWT is issued and accepted by driver-scoped status/profile endpoints, with compatibility credential payloads still enabled;
- local LLM serving is external to the main Compose stack by default;
- frontend is currently a single React entry file rather than a fully decomposed component tree;
- route progress is simulated/coarse because HiGHS does not expose reliable granular optimization progress through this integration;
- the trained route policy is reliable mainly for small tactical scenarios.

## Production Hardening Backlog

Before production usage, the following should be implemented:

- real authentication and authorization;
- backend admin authentication and authorization;
- bearer-token enforcement on protected endpoints;
- credential rotation;
- durable background worker queue;
- stronger job cancellation semantics;
- backend filtering and cursor pagination for high-volume collections;
- stricter observability: metrics and tracing correlated by domain identifiers;
- componentized frontend architecture;
- larger-cardinality model training;
- model-serving lifecycle management;
- formal integration tests against the Docker stack.
