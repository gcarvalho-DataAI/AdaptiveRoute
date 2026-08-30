# AdaptiveRoute Routing Policy LoRA v5

Release asset:

```text
adaptiveroute-routing-policy-lora-v5.tar.gz
```

Recommended tag:

```text
model-routing-policy-lora-v5
```

Base model:

```text
Qwen/Qwen2.5-7B-Instruct
```

Adapter:

```text
outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5
```

Package contents:

```text
README.md
adapter_config.json
adapter_model.safetensors
tokenizer.json
tokenizer_config.json
chat_template.jinja
training_args.bin
```

Checksum:

```text
sha256: d40d2691e8a4301acedaba54626df48695ea52cc664602eee02f17e9c8c81773
```

Evaluation summary:

```text
Feasible plans: 94.4%
Capacity violations: 46 / 1000
Blocked-arc violations: 9 / 1000
Exact match: 5.6%
```

Operational role:

The adapter is used as the routing-policy candidate generator. It proposes tactical
route adjustments, but deterministic validation remains the authority before any
plan is exposed to users.

Known limits:

- Best validated operating range is small tactical CVRP-style scenarios.
- Generalization degrades as customer cardinality grows beyond the training
  distribution.
- The model is not a replacement for the exact Pyomo + HiGHS solver.
- The model output must remain behind deterministic route validation.

Runtime configuration:

```env
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=local
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_ADAPTER_PATH=models/adaptiveroute-routing-policy-lora-v5
ADAPTIVEROUTE_ROUTING_POLICY_MODEL=adaptiveroute-routing-policy
```

If served through an OpenAI-compatible local API:

```env
ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=api
ADAPTIVEROUTE_ROUTING_POLICY_BASE_URL=http://127.0.0.1:8000/v1
ADAPTIVEROUTE_ROUTING_POLICY_API_KEY=local
ADAPTIVEROUTE_ROUTING_POLICY_MODEL=adaptiveroute-routing-policy
```
