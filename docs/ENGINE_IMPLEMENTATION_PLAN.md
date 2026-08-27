# AdaptiveRoute Engine Implementation Plan

This document is the working implementation plan for the AdaptiveRoute engine. It should be updated as the project evolves and used as the checklist for engine work before the UI layer is built.

## Objective

Build the core AdaptiveRoute engine: a logistics replanning engine where operational events are converted into structured scenario changes, applied to a small CVRP scenario, solved with Pyomo + HiGHS, validated deterministically, compared against the previous plan, and used to generate evaluation and fine-tuning datasets.

## Technical Principle

The optimizer is the source of truth. The LLM does not own feasibility. The LLM interprets events, may generate experimental candidate routes, and explains trade-offs, but every route must pass deterministic validation before it reaches the planner.

Current model decision: `outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5` is the selected routing policy adapter for the Agentic AI module. See [MODEL_DECISION.md](MODEL_DECISION.md).

Current agentic workflow: `src/adaptiveroute/agentic/` implements the LangGraph replanning flow with event extraction, base solve, mutation, candidate generation, deterministic validation, conservative repair, and Pyomo + HiGHS fallback.

Current orchestrator integration: `src/adaptiveroute/llm/` implements a lightweight OpenAI-compatible chat client. The agentic service can use this client for LLM-backed event extraction while preserving deterministic fallback.

## MVP Scope

Included:

- Small CVRP.
- 1 depot.
- 2 to 4 vehicles.
- 8 to 20 customers.
- Vehicle capacity.
- Customer demand.
- Explicit distance matrix.
- Required and optional customers.
- Priority customers.
- Blocked arcs.
- Unavailable customers.
- User-proposed route analysis.
- Pyomo + HiGHS solver.
- Synthetic scenario generation.
- Solution validation.
- Plan comparison.
- Initial SFT dataset generation.

Out of scope for the MVP:

- Real traffic.
- Real maps.
- GPS.
- Full VRPTW.
- Multi-depot routing.
- Pickup and delivery.
- Full stochastic/dynamic simulation.
- Full RL/GRPO training.
- A 7B fine-tuned model as the unchecked primary solver.

## Workstreams

### 1. Domain Model

Owner: OR Engineer + Backend/AI Engineer

Activities:

- Define core entities.
- Create versioned schemas.
- Keep JSON serialization clean.
- Separate scenario, event, solution, and metrics.

Entities:

- `Node`
- `Depot`
- `Customer`
- `Vehicle`
- `RoutingScenario`
- `RoutingPlan`
- `VehicleRoute`
- `RouteStop`
- `OperationalEvent`
- `ScenarioMutation`
- `PlanMetrics`
- `ValidationResult`
- `ComparisonResult`

Requirements:

- Every object must be serializable.
- IDs must be stable, e.g. `D0`, `C1`, `V1`.
- Distances must be represented by an explicit matrix.
- Domain models must not depend on Pyomo.
- Domain models must not depend on any LLM provider.

Deliverables:

- `src/adaptiveroute/domain/models.py`
- `src/adaptiveroute/domain/events.py`
- `tests/test_domain_serialization.py`

### 2. Scenario Generator

Owner: OR Engineer

Activities:

- Generate controlled synthetic scenarios.
- Create small demo scenarios.
- Create batch scenarios for SFT.
- Ensure distribution diversity.

Parameters:

- `num_customers`
- `num_vehicles`
- `vehicle_capacity`
- `coordinate_range`
- `demand_range`
- `priority_ratio`
- `seed`
- `clustered_vs_uniform`

Instance types:

- Uniform random.
- Clustered customers.
- Light demand.
- Tight demand.
- Nearly critical capacity.
- Distance with noise.

Requirements:

- Generation must be reproducible by seed.
- Base scenarios should not be infeasible unless intentionally generated for negative tests.
- Batch generation must support JSONL output.
- Demo scenario must be saved as JSON.

Deliverables:

- `src/adaptiveroute/data/generator.py`
- `data/demo/demo_scenario.json`
- `scripts/generate_scenarios.py`
- `tests/test_scenario_generator.py`

### 3. CVRPLIB Importer

Owner: OR Engineer

Activities:

- Download/import small CVRPLIB instances.
- Read instances using `vrplib`.
- Convert them to `RoutingScenario`.
- Support customer subsetting.

Requirements:

- Support at least one `.vrp` instance.
- Support `--max-customers 10`.
- Preserve depot, coordinates, demand, and capacity.
- Compute Euclidean matrix when needed.

Deliverables:

- `src/adaptiveroute/data/vrplib_importer.py`
- `scripts/import_cvrplib_instance.py`
- `data/raw/`
- `data/demo/cvrplib_subset_10.json`

Exit criterion:

```bash
python scripts/import_cvrplib_instance.py data/raw/A-n32-k5.vrp --max-customers 10
```

### 4. Pyomo + HiGHS Solver

Owner: OR Engineer

Activities:

- Implement abstract `RoutingEngine`.
- Implement `PyomoHighsEngine`.
- Solve small CVRP instances.
- Return clear solver status.

Model variables:

- `x[i,j,k]`: binary, vehicle `k` traverses arc `i -> j`.
- `y[i,k]`: binary, customer `i` is served by vehicle `k`.
- `u[i,k]`: MTZ order variable for subtour elimination.
- `vehicle_used[k]`: binary, vehicle `k` is active.

Constraints:

- Every active required customer is visited exactly once.
- Flow in equals flow out for every customer and vehicle.
- A used vehicle leaves the depot.
- A used vehicle returns to the depot.
- Vehicle capacity is respected.
- Self loops are forbidden.
- Blocked arcs are forbidden.
- MTZ constraints eliminate subtours.

Objective:

- Minimize total distance.
- Optionally add priority delay penalties.
- Optionally add soft preference penalties.

Requirements:

- Must not crash on infeasible instances.
- Must return solve time.
- Must return status and gap when available.
- Must use local HiGHS.
- Must solve the demo scenario in a few seconds.

Deliverables:

- `src/adaptiveroute/solvers/base.py`
- `src/adaptiveroute/solvers/pyomo_highs.py`
- `tests/test_pyomo_highs_solver.py`
- `scripts/solve_demo.py`

Exit criteria:

```bash
python scripts/solve_demo.py
pytest tests/test_pyomo_highs_solver.py
```

### 5. Scenario Mutations

Owner: AI Engineer + OR Engineer

Activities:

- Apply structured events to scenarios.
- Keep mutations auditable.
- Separate raw events from applied changes.

MVP events:

- `BLOCK_ARC`
- `CUSTOMER_UNAVAILABLE`
- `CUSTOMER_PRIORITY_CHANGE`
- `FORCE_NEXT_STOP`
- `EXPLAIN_ROUTE_CHOICE`

Implementation priority:

1. `BLOCK_ARC`
2. `CUSTOMER_UNAVAILABLE`
3. `CUSTOMER_PRIORITY_CHANGE`
4. `EXPLAIN_ROUTE_CHOICE`
5. `FORCE_NEXT_STOP`

Requirements:

- Every mutation must produce a diff.
- Invalid events must return clear errors.
- Out-of-scope events must not alter the scenario.
- Mutations must be replayable from the original scenario.

Deliverables:

- `src/adaptiveroute/services/mutations.py`
- `tests/test_mutations.py`

### 6. Plan Validation

Owner: OR Engineer

Activities:

- Validate any plan, whether produced by the solver or by a learned candidate model.
- Produce explicit violations.
- Generate feasibility status.

Checks:

- All active required customers are visited.
- No duplicate customers.
- No inactive customers are visited.
- Capacity is respected.
- Routes start and end at the depot.
- Blocked arcs are avoided.
- Vehicle IDs are valid.
- Customer IDs are valid.
- Routes are connected.
- Forced next stop is respected when applicable.

Requirements:

- Validator must be solver-independent.
- Validator must accept candidate plans in JSON.
- Validator must be used in tests, harness, and dataset generation.
- Fatal errors and warnings must be differentiated.

Deliverables:

- `src/adaptiveroute/services/validation.py`
- `tests/test_plan_validation.py`

### 7. Plan Comparison

Owner: AI Engineer

Activities:

- Compare original and replanned routes.
- Generate metrics and evidence for explanation.

Metrics:

- `total_distance_before`
- `total_distance_after`
- `distance_delta`
- `served_customers_before`
- `served_customers_after`
- `priority_customers_served`
- `vehicle_loads`
- `changed_edges`
- `removed_customers`
- `added_constraints`
- `feasibility_status`

Requirements:

- Result must be serializable.
- Result must include concrete evidence.
- Result must support both UI and LLM explanation.

Deliverables:

- `src/adaptiveroute/services/comparison.py`
- `tests/test_plan_comparison.py`

### 8. Counterfactual Route Analysis

Owner: OR Engineer + AI Engineer

Activities:

- Evaluate a route proposed by the user.
- Compare cost and feasibility against the optimized plan.
- Explain why the proposed route was not selected.

Example input:

```text
V1: D0 -> C1 -> C5 -> C4 -> C8 -> D0
```

Checks:

- Does it violate capacity?
- Does it miss required customers?
- Does it use blocked arcs?
- Does it increase distance?
- Does it displace a priority customer?
- Does it force the wrong vehicle?

Deliverables:

- `src/adaptiveroute/services/counterfactual.py`
- `tests/test_counterfactual.py`

### 9. Event Extraction Dataset

Owner: AI Engineer

Activities:

- Create a small natural-language dataset for structured events.
- Cover phrasing variation.
- Support extractor evals and future SFT.

Example:

```json
{
  "input": "There was an accident between C3 and C7. Avoid that road.",
  "expected_event": {
    "type": "BLOCK_ARC",
    "from_node": "C3",
    "to_node": "C7",
    "bidirectional": true
  }
}
```

Categories:

- Accident/blockage.
- Unavailable customer.
- Urgent customer.
- Driver-proposed route.
- Out-of-scope request.
- Ambiguous request.

Deliverables:

- `data/evals/event_extraction.jsonl`
- `tests/test_event_extraction_fixtures.py`

### 10. Expert Dataset For SFT

Owner: OR Engineer + AI Engineer

Activities:

- Generate pairs of `scenario + event -> route plan`.
- Solve with Pyomo + HiGHS.
- Validate each solution.
- Save only feasible examples.
- Create train/validation/test splits.

Recommended format:

```json
{
  "instruction": "Replan the route after the operational event.",
  "input": {
    "scenario": "...",
    "event": "..."
  },
  "output": {
    "routes": {
      "V1": ["D0", "C2", "C5", "D0"],
      "V2": ["D0", "C1", "C3", "C4", "D0"]
    }
  },
  "metadata": {
    "total_distance": 182.4,
    "solver": "pyomo_highs",
    "validation_passed": true,
    "seed": 42
  }
}
```

Requirements:

- Do not include long explanations in the target output.
- Target output must be structured.
- Validate before writing examples.
- Include dynamic events, not only static CVRP.
- Start with 500 to 2,000 small examples.

Deliverables:

- `src/adaptiveroute/training/dataset_builder.py`
- `scripts/build_sft_dataset.py`
- `data/training/sft_train.jsonl`
- `data/training/sft_val.jsonl`
- `data/training/sft_test.jsonl`

### 11. Learned Candidate Engine

Owner: AI Engineer

Activities:

- Define interface for learned candidate engines.
- Implement `LLMRoutingEngine` backed by the selected LoRA v5 adapter.
- Keep the model isolated from direct user conversation.
- Prepare path for fine-tuned model inference.
- Parse route JSON into domain models.
- Validate after inference.
- Repair invalid candidates when possible.
- Fall back to Pyomo + HiGHS when repair fails.

Flow:

```text
scenario + event
-> LoRA v5 route policy model
-> candidate routes JSON
-> deterministic validator
-> repair if invalid
-> Pyomo + HiGHS fallback if still invalid
-> accept final feasible plan
-> compare with Pyomo baseline/reference
```

Requirements:

- Must never bypass deterministic validation.
- Must never expose raw unchecked model routes as final answers.
- Must return `candidate_rejected` if invalid and unrepaired.
- Must record whether final output came from `lora_v5`, `lora_v5_repaired`, or `pyomo_highs_fallback`.
- The LLM routing policy must run a bounded validation-feedback retry loop before repair/fallback:
  - generate candidate JSON;
  - build route plan;
  - validate deterministic constraints;
  - if invalid, send validation violations back to the model in correction mode;
  - stop when a valid plan is produced or `ADAPTIVEROUTE_ROUTING_POLICY_MAX_RETRIES` is exhausted;
  - only then allow conservative repair and Pyomo + HiGHS fallback.
- Must record violations.
- Must support Best-of-N in the future.

Deliverables:

- `src/adaptiveroute/solvers/learned_candidate.py`
- `src/adaptiveroute/training/prompt_format.py`
- `tests/test_learned_candidate_validation.py`

### 11b. Agentic AI Module

Owner: AI Engineer

Architecture:

```text
user
-> reasoning/chat orchestrator model
-> LangGraph workflow
-> route policy tool backed by LoRA v5
-> deterministic verifier
-> repair/fallback
-> final user response
```

Nodes:

- `parse_user_request`
- `build_or_update_scenario`
- `generate_candidate_plan_with_lora_v5`
- `verify_candidate_plan`
- `repair_candidate_plan`
- `solver_fallback_if_needed`
- `compose_user_response`

Requirements:

- The orchestrator/chat model and route policy model must be separate.
- The LoRA v5 model must receive structured routing inputs only.
- The graph state must carry scenario, base plan, event, candidate plan, final plan, validation, violations, and trace IDs.
- Every branch must end with either a validated final route or an explicit failure status.
- The user-facing response must say whether the final route was generated directly, repaired, or produced by solver fallback.

Deliverables:

- `src/adaptiveroute/agents/state.py`
- `src/adaptiveroute/agents/graph.py`
- `src/adaptiveroute/agents/nodes.py`
- `src/adaptiveroute/agents/tools.py`
- `tests/test_agentic_replanning_graph.py`

### 12. Engine-Level Evals

Owner: AI Engineer + OR Engineer

Activities:

- Create an engine evaluation suite.
- Measure solver quality, mutation compliance, validation, and stability.

Engine evals:

- `feasibility_rate`
- `solve_success_rate`
- `average_solve_time`
- `blocked_arc_compliance`
- `customer_unavailable_compliance`
- `priority_preservation`
- `counterfactual_detection_accuracy`
- `event_extraction_accuracy`
- `repeated_run_stability`

Learned model evals:

- `valid_json_rate`
- `feasible_route_rate`
- `average_gap_vs_pyomo`
- `best_of_n_feasible_rate`
- `duplicate_customer_rate`
- `missing_customer_rate`
- `blocked_arc_violation_rate`

Current selected model:

- `outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5`
- benchmark feasible rate: `94.4%` on 1,000 curriculum test examples
- main remaining failure mode: capacity violations

Deliverables:

- `src/adaptiveroute/evals/engine_eval.py`
- `scripts/run_engine_evals.py`
- `tests/test_engine_evals.py`

### 13. Trace Logging

Owner: Backend/AI Engineer

Activities:

- Record end-to-end engine execution.
- Produce readable JSONL traces.
- Support debug and UI panels.

Trace fields:

- `trace_id`
- `scenario_id`
- `event_input`
- `structured_event`
- `mutation_diff`
- `solver_status`
- `solver_time_ms`
- `validation_result`
- `comparison_metrics`
- `errors`
- `timestamp`

Deliverables:

- `src/adaptiveroute/services/tracing.py`
- `outputs/traces/`

### 14. CLI Demo

Owner: Backend/AI Engineer

Activities:

- Create demos without UI.
- Solve base scenario.
- Apply event.
- Reoptimize.
- Compare results.
- Print a report.

Commands:

```bash
python scripts/solve_demo.py
python scripts/replan_demo.py --event "accident between C3 and C7"
python scripts/evaluate_counterfactual.py --route "V1:D0,C1,C5,C4,C8,D0"
```

Deliverables:

- `scripts/solve_demo.py`
- `scripts/replan_demo.py`
- `scripts/evaluate_counterfactual.py`

### 15. Engine Documentation

Owner: Lead/AI Engineer

Activities:

- Document technical decisions.
- Make real vs experimental scope explicit.
- Explain the Pyomo + HiGHS choice.

Documents:

- `README.md`
- `DESIGN.md`
- `ENGINE.md`
- `AGENTS.md`

Required points:

- The LLM does not solve the optimization problem.
- Pyomo + HiGHS was chosen for inspectability.
- Small scope is deliberate.
- Fine-tuned model v5 is a selected candidate generator, not a feasibility authority.
- Deterministic validation is mandatory.
- CVRPLIB is for evaluation/benchmarking.
- Synthetic scenarios are used for training data generation.

## Five-Day Timeline

### Day 1: OR Core

- Domain model.
- Scenario generator.
- Demo scenario.
- Pyomo + HiGHS baseline.
- Solve demo CLI.
- Basic feasibility tests.

Exit criteria:

```bash
python scripts/solve_demo.py
pytest tests/test_pyomo_highs_solver.py
```

### Day 2: Dynamic Replanning

- Scenario mutations.
- Blocked arcs.
- Customer unavailable.
- Priority changes.
- Plan validation.
- Plan comparison.
- Replan CLI.

Exit criteria:

```bash
python scripts/replan_demo.py --event fixtures/block_arc.json
pytest tests/test_mutations.py tests/test_plan_validation.py
```

### Day 3: Counterfactual + Data

- Counterfactual route analysis.
- CVRPLIB importer.
- Synthetic batch generator.
- SFT dataset builder v1.
- Event extraction fixtures.

Exit criteria:

```bash
python scripts/build_sft_dataset.py --n 500
python scripts/evaluate_counterfactual.py
pytest
```

### Day 4: Evals + Learned Stub

- Engine eval suite.
- Repeated scenario eval.
- Learned candidate engine stub.
- Best-of-N interface stub.
- Trace logging.

Exit criteria:

```bash
python scripts/run_engine_evals.py
pytest
```

### Day 5: Stabilization

- Small refactor pass.
- README/DESIGN/ENGINE.
- Reproducibility check.
- Clean demo outputs.
- Prepare integration with API/UI.

Exit criteria:

```bash
python scripts/solve_demo.py
python scripts/replan_demo.py
python scripts/run_engine_evals.py
pytest
```

## Definition Of Done For The Engine

The engine is ready for UI work when:

- Base scenario solves.
- At least three structured events work.
- Every generated plan is validated.
- Original and replanned plans are compared.
- Counterfactual analysis works.
- Traces are generated.
- Engine evals run.
- Initial SFT dataset can be generated.
- Failures return clear statuses.
- Documentation explains decisions and limitations.

## Main Risks

- VRP MILP becomes slow: limit demo to 8-12 customers.
- MTZ/subtour implementation is wrong: test small routes manually.
- Too many events: prioritize `BLOCK_ARC`, `CUSTOMER_UNAVAILABLE`, and `CUSTOMER_PRIORITY_CHANGE`.
- Fine-tuning consumes too much time: freeze v5 for now and move to runtime verification/repair.
- Dataset quality is poor: validate every example before writing.
- Solver infeasibility is opaque: capture status and emit clear failure messages.

## Leadership Decision

The primary delivery is the Pyomo + HiGHS replanning engine plus an Agentic AI workflow that uses the selected LoRA v5 model as a specialized route proposal policy. Fine-tuning is closed for now. The next critical path is integration: model inference, deterministic verification, repair, fallback, and LangGraph orchestration.
