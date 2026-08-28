# AdaptiveRoute Agentic Workflow

The AdaptiveRoute agentic workflow is implemented with LangGraph and is designed around explicit, inspectable steps. Each graph node is represented by a specialized agent class inheriting from `RoutingWorkflowAgent`.

The workflow objective is to convert a natural-language route disruption into a validated route plan or a safe explanation. The trained model is used only as a candidate generator. Validation and fallback remain deterministic.

## Graph

Implemented in `src/adaptiveroute/agentic/graph.py`:

```text
extract_event
        |
        v
solve_base
        |
        v
apply_event
        |
        v
generate_candidate
        |
        v
validate_candidate
        |
        +-- valid --> compose_response
        |
        +-- invalid --> repair_candidate
                         |
                         +-- valid --> compose_response
                         |
                         +-- invalid --> solver_fallback
                                         |
                                         v
                                  compose_response
```

If event extraction fails but a context window exists, the workflow can answer as a context follow-up instead of forcing a replanning action.

## Agent Responsibilities

| Agent | Responsibility | Output |
|---|---|---|
| `ExtractEventAgent` | Extract operational event from user text. | Event object, confidence and trace metadata. |
| `SolveBaseAgent` | Solve the current scenario before mutation. | Base plan and base validation. |
| `ApplyEventAgent` | Apply disruption to the scenario. | Mutated scenario and mutation diff. |
| `GenerateCandidateAgent` | Generate a new route candidate. | Candidate plan from solver, API model or local LoRA. |
| `ValidateCandidateAgent` | Check candidate feasibility. | Validation result and final plan if valid. |
| `RepairCandidateAgent` | Attempt conservative repair of invalid candidates. | Repaired plan and validation result. |
| `SolverFallbackAgent` | Use Pyomo + HiGHS when candidate/repair fails. | Solver-backed final plan. |
| `ComposeResponseAgent` | Build response payload and trace. | API response with final plan, validation, comparison and errors. |

## Event Extraction

Supported operational events include:

- blocked arc, for example `C1 -> C3 is blocked`;
- customer unavailable, for example `C5 cannot receive for 2 hours`;
- priority change.

The extractor can run in two modes:

- rule-based extraction;
- OpenAI-compatible LLM extraction with deterministic fallback.

The LLM extractor is not trusted blindly. Its output is parsed into an explicit event object and rejected if it does not match scenario nodes or supported event types.

## Candidate Generation Modes

`ADAPTIVEROUTE_ROUTING_POLICY_BACKEND` selects the route candidate backend:

| Backend | Behavior |
|---|---|
| `solver` | Uses Pyomo + HiGHS as the candidate generator. Best for deterministic tests. |
| `api` | Calls the trained LoRA through an OpenAI-compatible API. |
| `local` | Loads the LoRA adapter directly in the API process. |

The selected trained model is:

```text
outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5
```

It is served as:

```text
adaptiveroute-routing-policy
```

## Route Q&A

Route Q&A is handled by the conversation/memory service with support from:

- route lookup;
- route fact builder;
- RAG retrieval;
- local OpenAI-compatible general LLM.

The general chat model is responsible for natural-language answers and explanations. It should not be used as the source of route feasibility. When a question implies a route change, the message should be routed into the replanning workflow.

Recommended classification:

| Message type | Correct path |
|---|---|
| “What is my next stop?” | Route Q&A using `chat-local`. |
| “Why did the plan change?” | Route Q&A using route facts, memory and RAG. |
| “What if C5 cannot receive?” | Replanning workflow using route policy + validation. |
| “C3 to C5 is blocked, should I replan?” | Replanning workflow using route policy + validation. |

## Validation Contract

Every candidate plan is validated against deterministic rules:

- all required active customers must be served;
- inactive/unavailable customers must not be served;
- no unknown customer IDs;
- no blocked arcs;
- vehicle capacity respected;
- routes must start and end at the depot.

If validation fails, the system attempts repair. If repair fails, the solver fallback is executed.

## Traceability

Every workflow node appends trace metadata. The frontend exposes this as the agent execution panel, giving visibility into:

- event extraction confidence;
- candidate source;
- validation status;
- repair/fallback decisions;
- final route source.

This is necessary for the PoC claim: the model accelerates tactical replanning, while deterministic infrastructure protects operational correctness.

