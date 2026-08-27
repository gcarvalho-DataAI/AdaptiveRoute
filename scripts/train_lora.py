from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a LoRA/QLoRA routing candidate model from chat JSONL data.")
    parser.add_argument("--model-id", required=True, help="Base model, e.g. Qwen/Qwen2.5-7B-Instruct.")
    parser.add_argument("--adapter-path", default=None, help="Optional existing LoRA adapter to continue training from.")
    parser.add_argument(
        "--attn-implementation",
        default=None,
        help="Optional Transformers attention implementation, e.g. flash_attention_2.",
    )
    parser.add_argument("--dataset-dir", required=True, help="Directory with train.jsonl, val.jsonl, test.jsonl.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--max-steps", type=int, default=-1, help="Use a small value for smoke tests.")
    parser.add_argument("--train-limit", type=int, default=0, help="Limit train rows before SFT preprocessing.")
    parser.add_argument("--eval-limit", type=int, default=0, help="Limit validation rows before SFT preprocessing.")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--warmup-steps", type=int, default=0)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--lr-scheduler-type", default="linear")
    parser.add_argument("--per-device-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--eval-steps", type=int, default=250)
    parser.add_argument("--no-eval-during-train", action="store_true")
    parser.add_argument("--save-steps", type=int, default=50)
    parser.add_argument("--save-total-limit", type=int, default=3)
    parser.add_argument("--optim", default="adamw_torch", help="Trainer optimizer. adamw_torch avoids fused CUDA optimizer crashes.")
    parser.add_argument(
        "--bnb-compute-dtype",
        choices=["float16", "bfloat16"],
        default=None,
        help="4-bit compute dtype. Defaults to bfloat16 when --bf16 is set, else float16.",
    )
    parser.add_argument("--torch-empty-cache-steps", type=int, default=50)
    parser.add_argument("--resume-from-checkpoint", default=None)
    parser.add_argument("--no-gradient-checkpointing", action="store_true")
    parser.add_argument("--packing", action="store_true", help="Pack multiple formatted examples into full sequences.")
    parser.add_argument("--padding-free", action="store_true", help="Use padding-free training when supported by TRL.")
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--target-modules", default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit loading.")
    parser.add_argument("--slow-tokenizer", action="store_true", help="Use the Python tokenizer implementation.")
    parser.add_argument("--bf16", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        print("Training dependencies are not installed.")
        print("Install them with: uv sync --group train")
        print(f"Missing import: {exc}")
        return 1

    dataset_dir = Path(args.dataset_dir)
    data_files = {
        "train": str(dataset_dir / "train.jsonl"),
        "validation": str(dataset_dir / "val.jsonl"),
    }
    dataset = load_dataset("json", data_files=data_files)

    train_limit = args.train_limit
    eval_limit = args.eval_limit
    if args.max_steps > 0 and train_limit <= 0:
        effective_batch = args.per_device_batch_size * args.gradient_accumulation_steps
        train_limit = max(512, min(len(dataset["train"]), args.max_steps * effective_batch * 4))
    if args.max_steps > 0 and eval_limit <= 0:
        eval_limit = min(len(dataset["validation"]), 256)

    if train_limit > 0:
        dataset["train"] = dataset["train"].select(range(min(train_limit, len(dataset["train"]))))
    if eval_limit > 0:
        dataset["validation"] = dataset["validation"].select(range(min(eval_limit, len(dataset["validation"]))))

    print(f"Train rows: {len(dataset['train'])}")
    print(f"Validation rows: {len(dataset['validation'])}")

    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True, use_fast=not args.slow_tokenizer)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization_config = None
    if not args.no_4bit:
        bnb_compute_dtype_name = args.bnb_compute_dtype or ("bfloat16" if args.bf16 else "float16")
        bnb_compute_dtype = torch.bfloat16 if bnb_compute_dtype_name == "bfloat16" else torch.float16
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=bnb_compute_dtype,
        )

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        trust_remote_code=True,
        device_map="auto",
        quantization_config=quantization_config,
        attn_implementation=args.attn_implementation,
    )

    peft_config = None
    if args.adapter_path:
        model = PeftModel.from_pretrained(model, args.adapter_path, is_trainable=True)
    else:
        peft_config = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=[module.strip() for module in args.target_modules.split(",") if module.strip()],
        )

    def formatting_func(example):
        return tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)

    training_args = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        max_grad_norm=args.max_grad_norm,
        lr_scheduler_type=args.lr_scheduler_type,
        per_device_train_batch_size=args.per_device_batch_size,
        per_device_eval_batch_size=args.per_device_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        logging_steps=args.logging_steps,
        eval_strategy="no" if args.no_eval_during_train else "steps",
        eval_steps=args.eval_steps,
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        optim=args.optim,
        torch_empty_cache_steps=args.torch_empty_cache_steps,
        gradient_checkpointing=not args.no_gradient_checkpointing,
        bf16=args.bf16,
        fp16=not args.bf16,
        report_to=[],
        remove_unused_columns=False,
        max_length=args.max_seq_length,
        packing=args.packing,
        padding_free=args.padding_free,
        dataset_num_proc=1,
        dataloader_num_workers=0,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        peft_config=peft_config,
        formatting_func=formatting_func,
        processing_class=tokenizer,
    )
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
