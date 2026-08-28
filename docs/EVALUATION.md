# Evaluation Methodology

AdaptiveRoute evaluation separates mathematical feasibility, model behavior, agent workflow correctness and user-facing operational usefulness.

## Evaluation Goals

The project tests the following hypothesis:

> A fine-tuned route-policy model can produce fast approximate replanning candidates for small tactical disruptions, while Pyomo + HiGHS remains the authoritative optimizer for exact planning and fallback.

The model is successful when it returns structured, feasible route candidates quickly enough for on-the-fly operational use. It is not expected to prove optimality.

## Solver Evaluation

The Pyomo + HiGHS solver is evaluated as the deterministic planning baseline.

Checks:

- solver returns an optimal or acceptable feasible solution;
- all active required customers are served;
- vehicle capacity is respected;
- blocked arcs are avoided;
- route starts and ends at depot;
- distance totals are internally consistent.

Relevant tests:

```bash
uv run pytest tests/test_pyomo_highs_solver.py tests/test_plan_validation.py
```

## Route Policy Model Evaluation

The trained model is evaluated as a candidate generator.

Primary metrics:

- valid JSON rate;
- feasible candidate rate;
- capacity violation count;
- blocked-arc violation count;
- missing customer count;
- inactive/unknown customer count;
- average candidate latency;
- exact match rate, treated as secondary.

Exact match is secondary because CVRP can have multiple valid solutions. Feasibility and operational-rule compliance are more important for this PoC.

## Model Comparison

Fixed benchmark:

```text
1,000 examples from data/training_curriculum_100k/sft_test.jsonl
```

| Model | Main training data | Feasible rate | Capacity violations | Blocked arc violations | Exact match |
|---|---|---:|---:|---:|---:|
| v3 | 30K compact curriculum | 91.7% | 72 | 11 | 4.6% |
| v4 | v3 + 70K hard continuation | 92.9% | 61 | 10 | 5.8% |
| v5 | v4 + 20K error-driven continuation | 94.4% | 46 | 9 | 5.6% |
| v6 | v5 + 10K additional continuation | 94.0% | 50 | 10 | 5.4% |

Selected version:

```text
outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5
```

Reason:

- best feasible candidate rate;
- lowest capacity violation count;
- lowest blocked-arc violation count;
- stable JSON generation;
- v6 did not improve the benchmark.

## Final v5 Metrics

```text
Total examples: 1,000
Valid JSON: 1,000
Valid JSON rate: 100.0%
Feasible candidates: 944
Feasible rate: 94.4%
Exact match: 56
Exact match rate: 5.6%
Blocked arc violations: 9
Capacity violations: 46
Inactive/unknown customer violations: 1
Missing customer violations: 1
```

## Capacity Boundary Evaluation

The capacity benchmark estimates the maximum scenario size where the current LoRA policy can reliably generate valid route candidates without depending on solver fallback.

Measured strict viability boundary:

```text
8-9 customers
```

Boundary run:

| Customers | Cases | Strict valid rate | Repaired valid rate | Avg candidate latency | Main failure mode |
|---:|---:|---:|---:|---:|---|
| 8 | 5 | 100% | 100% | 1.59s | — |
| 9 | 5 | 100% | 100% | 1.71s | — |
| 10 | 5 | 60% | 60% | 3.99s | Missing customer |

Probe run:

| Customers | Cases | Strict valid rate | Main failure mode |
|---:|---:|---:|---|
| 8 | 3 | 100% | — |
| 10 | 3 | 66.7% | Missing customer |
| 12 | 3 | 33.3% | Missing customer |
| 14 | 3 | 0% | Missing customer |

Interpretation:

- The model is useful for small route-level tactical replanning.
- Larger-cardinality scenarios expose generalization limits.
- The dominant failure mode is customer omission, especially around IDs outside the original compact training profile.

## Agentic Workflow Evaluation

The workflow should be evaluated end-to-end, not only by model output.

Expected checks:

- event extraction identifies the right event type and affected nodes;
- route lookup binds the message to the correct route;
- route facts are built from actual route state;
- candidate generation uses the configured policy backend;
- validation rejects infeasible outputs;
- repair is attempted only when appropriate;
- solver fallback is triggered when repair fails;
- final response is stored in conversation memory;
- context window is updated;
- frontend shows trace and plan output.

Relevant tests:

```bash
uv run pytest tests/test_agentic_routing.py tests/test_memory_service.py tests/test_agentic_api.py
```

## UX Evaluation

For the PoC, the UI should demonstrate:

- admin can create scenarios;
- admin can run solver jobs;
- admin can monitor route records;
- admin can select one or more driver routes on the dashboard map;
- driver can log in and see only assigned route information;
- driver can ask route questions;
- driver can report disruptions;
- chat shows user/agent messages, trace, route plan and context window.

## Recommended Evaluation Commands

Run core test suite:

```bash
uv run pytest
```

Generate model predictions:

```bash
uv run python scripts/generate_model_predictions.py \
  --model-path outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5 \
  --dataset data/training_curriculum_100k/sft_test.jsonl \
  --out outputs/predictions/lora_error20k_v5_curriculum_test_1000.jsonl \
  --limit 1000
```

Evaluate predictions:

```bash
uv run python scripts/evaluate_predictions.py \
  --dataset data/training_curriculum_100k/sft_test.jsonl \
  --predictions outputs/predictions/lora_error20k_v5_curriculum_test_1000.jsonl \
  --details-out outputs/predictions/lora_error20k_v5_curriculum_test_1000_eval_details.jsonl
```

Run capacity benchmark:

```bash
uv run python scripts/benchmark_routing_policy_capacity.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model adaptiveroute-routing-policy \
  --customer-counts 8,9,10,12,14 \
  --cases-per-size 5 \
  --out outputs/evaluations/routing_policy_capacity.json
```

## Safe Claim

The current LoRA route policy validates the product hypothesis for small tactical scenarios: it can generate fast approximate route candidates that often pass deterministic validation. It should be deployed behind validation, repair and solver fallback. It should not be marketed as an exact optimizer or as a replacement for Pyomo + HiGHS.

