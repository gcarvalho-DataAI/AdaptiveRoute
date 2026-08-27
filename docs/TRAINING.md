# AdaptiveRoute Training Notes

## Current Model Decision

The current selected routing policy model is:

```text
outputs/models/adaptiveroute-qwen2_5-7b-lora-error20k-v5
```

See [MODEL_DECISION.md](MODEL_DECISION.md) for the closed model comparison and runtime contract.

The trained model is not the source of truth. It is a candidate generator whose outputs must be checked by deterministic validation before they are accepted.

## 1. Generate Compact SFT Data

```bash
systemd-inhibit --why="Generating AdaptiveRoute SFT dataset" \
  uv run python scripts/build_sft_dataset_chunked.py \
  --n 20000 \
  --chunk-size 100 \
  --min-chunk-size 10 \
  --num-customers 8 \
  --out-dir data/training_compact_20k \
  --format compact \
  --resume \
  2>&1 | tee -a dataset_20k.log
```

## 2. Audit Dataset

```bash
uv run python scripts/audit_sft_dataset.py data/training_compact_20k
```

Expected:

- `invalid_rows: 0`
- roughly balanced `BLOCK_ARC` and `CUSTOMER_UNAVAILABLE`
- train/val/test split near 80/10/10

## 3. Convert To Chat Messages

```bash
uv run python scripts/prepare_chat_dataset.py \
  data/training_compact_20k \
  --out-dir data/chat_training_compact_20k \
  --format messages
```

## 4. Install Training Dependencies

```bash
uv sync --group train
```

## 5. Train LoRA/QLoRA

Example:

```bash
uv run python scripts/train_lora.py \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --dataset-dir data/chat_training_compact_20k \
  --output-dir outputs/models/adaptiveroute-qwen2_5-7b-lora \
  --max-seq-length 4096 \
  --epochs 1 \
  --per-device-batch-size 1 \
  --gradient-accumulation-steps 8 \
  --bf16
```

For the current POC, do not continue training by default. The next engineering step is integrating the selected v5 adapter into the Agentic AI module with validation, repair, and Pyomo + HiGHS fallback.
