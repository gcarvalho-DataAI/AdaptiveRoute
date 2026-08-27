# AdaptiveRoute Model Decision

This document closes the current model-training track and defines which model should be used by the next Agentic AI module.

## Decision

Use `outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5` as the selected routing policy model.

The model must be used as a candidate route generator inside the routing agent workflow. It must not be treated as the source of truth for feasibility. Runtime validation, repair, and Pyomo + HiGHS fallback remain mandatory.

## Selected Model

- Base model: `Qwen/Qwen2.5-7B-Instruct`
- Adapter: `outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5`
- Training method: LoRA/QLoRA continuation
- Role: specialized route proposal policy
- Input: structured scenario, base route, operational event
- Output: JSON route candidate

## Model Comparison

All models were evaluated on the same 1,000-row sample from `data/training_curriculum_100k/sft_test.jsonl`.

| Model | Main training data | Feasible rate | Capacity violations | Blocked arc violations | Exact match |
| --- | --- | ---: | ---: | ---: | ---: |
| v3 | 30K compact curriculum | 91.7% | 72 | 11 | 4.6% |
| v4 | v3 + 70K hard continuation | 92.9% | 61 | 10 | 5.8% |
| v5 | v4 + 20K error-driven continuation | 94.4% | 46 | 9 | 5.6% |
| v6 | v5 + 10K additional error-driven continuation | 94.0% | 50 | 10 | 5.4% |

## Rationale

v5 is the best trade-off observed so far:

- highest feasible route rate;
- lowest capacity violation count;
- lowest blocked-arc violation count;
- stable JSON generation rate;
- no observed training failure in the final run;
- v6 did not improve the benchmark and slightly regressed.

Exact match is not the primary decision metric because CVRP often has multiple feasible route plans. Feasibility and operational-rule compliance matter more for this POC.

## Evaluation Artifacts

- v5 model: `outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5`
- v5 train log: `train_lora_error20k_v5.log`
- v5 evaluation log: `eval_lora_error20k_v5_on_complete.log`
- v5 predictions: `outputs/predictions/lora_error20k_v5_curriculum_test_1000.jsonl`
- v5 evaluation details: `outputs/predictions/lora_error20k_v5_curriculum_test_1000_eval_details.jsonl`
- v6 model: `outputs/models/adaptiveroute-qwen2_5-7b-lora-error10k-v6`
- v6 evaluation log: `eval_lora_error10k_v6_on_complete.log`

## Runtime Contract

The selected model must be called behind a deterministic guardrail:

```text
scenario + base_plan + event
-> LoRA v5 candidate generation
-> JSON parsing
-> deterministic route validation
-> repair if needed
-> Pyomo + HiGHS fallback if still invalid
-> final response
```

The accepted final plan must include:

- candidate source: `lora_v5`, `lora_v5_repaired`, or `pyomo_highs_fallback`;
- validation result;
- violation list if any candidate was rejected;
- distance/load metrics;
- final route JSON.

## Next Engineering Step

Start the Agentic AI module with LangGraph.

The recommended graph is:

```text
parse_user_request
-> build_or_update_scenario
-> generate_candidate_plan_with_lora_v5
-> verify_candidate_plan
-> repair_candidate_plan
-> solver_fallback_if_needed
-> compose_user_response
```

The orchestrator/chat model should be a separate reasoning-capable model. The LoRA v5 model should only serve the route-specialist agent/tool.

The orchestrator side now has an OpenAI-compatible client abstraction. It can target local Qwen/llama.cpp/vLLM serving or an external compatible provider such as Kimi/Moonshot via configuration, without changing the routing graph.

## Closed Items

- Base compact dataset generated.
- Hard curriculum datasets generated.
- Error-driven datasets generated.
- LoRA v3/v4/v5/v6 evaluated.
- v5 selected as current routing policy model.

## Open Items

- Implement `LLMRoutingEngine` backed by the selected v5 adapter.
- Add API endpoint for replanning.
- Add UI after engine integration is stable.

## Agentic Module Status

The first LangGraph-based agentic workflow is implemented in `src/adaptiveroute/agentic/`.

Current graph:

```text
extract_event
-> solve_base
-> apply_event
-> generate_candidate
-> validate_candidate
-> repair_candidate if invalid
-> solver_fallback if still invalid
-> compose_response
```

The candidate generator is currently plug-compatible. The default implementation is solver-backed for deterministic testing. The next implementation step is replacing or augmenting it with the selected LoRA v5 adapter while keeping the same validation, repair, and fallback contract.

OpenAI-compatible orchestrator configuration:

```text
ADAPTIVEROUTE_ORCHESTRATOR_BASE_URL=http://127.0.0.1:8000/v1
ADAPTIVEROUTE_ORCHESTRATOR_API_KEY=local
ADAPTIVEROUTE_ORCHESTRATOR_MODEL=auto
```
