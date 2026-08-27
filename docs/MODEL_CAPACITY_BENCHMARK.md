# AdaptiveRoute Routing Policy Capacity Benchmark

## Objective

Estimate the maximum operational scenario size where the fine-tuned routing policy model can generate valid replanning candidates without using the deterministic solver as the candidate generator.

The benchmark measures model viability by scenario size, not solver scalability.

## Viability definition

A scenario size is considered viable when the strict candidate validation pass rate is at least 90%.

Strict validation means:

- every active required customer is visited exactly once;
- each route starts and ends at the depot;
- only known vehicles and active customers are used;
- blocked arcs are not used;
- vehicle capacity is respected.

The benchmark also reports repaired-valid rate, but this is a safety-layer metric and should not be used as the pure model capability limit.

## Benchmark command

The benchmark script is:

```bash
scripts/benchmark_routing_policy_capacity.py
```

Run against the LoRA policy API:

```bash
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=api \
ADAPTIVEROUTE_ROUTING_POLICY_BASE_URL=http://127.0.0.1:8000/v1 \
ADAPTIVEROUTE_ROUTING_POLICY_API_KEY=local \
ADAPTIVEROUTE_ROUTING_POLICY_MODEL=adaptiveroute-routing-policy \
ADAPTIVEROUTE_ROUTING_POLICY_MAX_RETRIES=3 \
uv run python scripts/benchmark_routing_policy_capacity.py \
  --customer-grid 8,9,10 \
  --samples-per-size 5 \
  --profile balanced \
  --event-types block_arc,customer_unavailable \
  --out outputs/evaluations/routing_policy_capacity_lora_boundary_8_10.json
```

For a broader run:

```bash
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=api \
ADAPTIVEROUTE_ROUTING_POLICY_BASE_URL=http://127.0.0.1:8000/v1 \
ADAPTIVEROUTE_ROUTING_POLICY_API_KEY=local \
ADAPTIVEROUTE_ROUTING_POLICY_MODEL=adaptiveroute-routing-policy \
ADAPTIVEROUTE_ROUTING_POLICY_MAX_RETRIES=3 \
uv run python scripts/benchmark_routing_policy_capacity.py \
  --customer-grid 8,9,10,12,14,16 \
  --samples-per-size 20 \
  --profile balanced \
  --event-types block_arc,customer_unavailable \
  --out outputs/evaluations/routing_policy_capacity_lora_balanced_full.json \
  2>&1 | tee benchmark_routing_policy_capacity.log
```

## Current measured result

Using `outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5` served as `adaptiveroute-routing-policy`, the current measured strict viability boundary is:

```text
Maximum viable size: 9 customers
```

Boundary run:

| Customers | Cases | Strict valid rate | Repaired valid rate | Avg candidate latency | Main failure mode |
|---:|---:|---:|---:|---:|---|
| 8 | 5 | 100% | 100% | 1.59s | — |
| 9 | 5 | 100% | 100% | 1.71s | — |
| 10 | 5 | 60% | 60% | 3.99s | missing customer |

Probe run:

| Customers | Cases | Strict valid rate | Main failure mode |
|---:|---:|---:|---|
| 8 | 3 | 100% | — |
| 10 | 3 | 66.7% | missing customer |
| 12 | 3 | 33.3% | missing customer |
| 14 | 3 | 0% | missing customer |

## Interpretation

The dominant failure mode above 9 customers is customer omission, especially once the model must handle identifiers outside or near the edge of the training distribution such as `C10+`.

This indicates a cardinality/generalization limit of the current fine-tuned policy model. It is not primarily a solver issue and not primarily a route-distance issue.

## Recommended next refinement

To push the viable boundary beyond 9 customers:

1. Generate training data with explicit larger-cardinality scenarios: 10, 12, 16, 20, and 24 customers.
2. Balance the dataset so every active customer id appears in the target output.
3. Add curriculum fine-tuning: start from 8 customers, then mix larger scenarios progressively.
4. Add evaluation splits by cardinality, not only random train/validation/test splits.
5. Keep the validation-feedback retry loop, but treat retries as guardrails, not as model capability.

For the PoC, the safe claim is:

> The current LoRA routing policy is reliable for small tactical replanning scenarios around 8–9 customers. Larger route sets should use the deterministic solver as the authority, with the model acting as a fast candidate generator or explanation layer until larger-cardinality fine-tuning is completed.
