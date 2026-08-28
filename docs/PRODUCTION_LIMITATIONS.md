# Production Limitations

AdaptiveRoute was built as a five-day proof of concept. The architecture is intentionally designed to be extensible, but several production concerns remain open.

## Solver Execution

The current FastAPI app exposes both synchronous and asynchronous planning paths. For production, long-running optimization must use the job path and execute outside the request lifecycle.

Risk:

- synchronous solver calls can block a Uvicorn worker;
- MTZ formulations can become slow as scenario size grows;
- cancellation is coarse and process-oriented.

Recommended hardening:

- use a dedicated worker queue;
- keep API requests limited to job creation/status/cancel;
- persist solver logs and final artifacts;
- tune solver time limits and MIP gap by scenario class.

## Test Suite Stability

The focused API/agentic test suite is stable. Solver authority tests run in a separate CI job using forked test processes. The full local test suite can still trigger a native segmentation fault in the Pyomo/HiGHS stack after repeated solver invocations in one Python process on the current local environment.

Recommended hardening:

- keep solver-heavy tests isolated in subprocesses;
- keep CI split into fast API tests and solver integration tests;
- pin a known-stable HiGHS/Pyomo combination;
- consider an alternate solver backend for integration tests.

## Mathematical Formulation

The current Pyomo model uses an MTZ-style formulation for subtour elimination. This is readable and appropriate for a PoC, but the LP relaxation is weak compared with stronger VRP formulations.

Recommended alternatives:

- OR-Tools Routing Solver for larger tactical scenarios;
- stronger branch-and-cut formulation;
- decomposition or heuristic warm starts;
- hybrid exact/heuristic strategy.

## Model Generalization

The selected LoRA policy is reliable for small tactical scenarios around 8-9 customers. Above that boundary, the dominant failure mode is customer omission.

Recommended hardening:

- train on larger cardinalities: 10, 12, 16, 20 and 24 customers;
- evaluate by scenario size, not only random test split;
- keep validation, repair and solver fallback mandatory;
- track fallback rate and violation modes in production telemetry.

## API Scalability

The current list endpoints support bounded offset-style pagination through `skip` and `limit`. This is sufficient for PoC screens, but production APIs still need query-specific filtering and indexes.

Recommended hardening:

- cursor-based pagination for high-volume collections;
- filtering by route id, driver id, status and scenario id;
- server-side search;
- indexes matching common filters.

## Observability

The current system exposes traces through application payloads and emits request-level JSON logs with request IDs. It does not yet provide production-grade observability.

Recommended hardening:

- `conversation_id`, `route_id`, `scenario_id`, `job_id` correlation;
- metrics for latency, fallback rate, validation failures and solver time;
- dashboard for model-vs-solver performance.

## Frontend Structure

The frontend is currently optimized for fast PoC iteration and is implemented primarily in one React entry file.

Recommended hardening:

- split views, components, hooks and API client modules;
- add component tests;
- add role-based route guards;
- move auth state handling into a dedicated module.
