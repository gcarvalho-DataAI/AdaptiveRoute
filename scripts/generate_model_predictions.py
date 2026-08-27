from __future__ import annotations

import argparse
import json
from pathlib import Path

from adaptiveroute.training.prompt_format import SYSTEM_PROMPT, build_user_prompt


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate route predictions from a base/fine-tuned causal LM.")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--dataset", required=True, help="Compact SFT JSONL file, usually sft_test.jsonl.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args()

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        print("Inference dependencies are not installed.")
        print("Install them with: uv sync --group train")
        print(f"Missing import: {exc}")
        return 1

    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(args.model_path, trust_remote_code=True, device_map="auto")
    model.eval()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as out_file:
        for idx, row in enumerate(iter_jsonl(Path(args.dataset))):
            if idx >= args.limit:
                break
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(row)},
            ]
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            with torch.no_grad():
                generated = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            generated_text = tokenizer.decode(generated[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
            out_file.write(json.dumps({"row_index": idx, "target": row["output"], "prediction_text": generated_text}, ensure_ascii=False))
            out_file.write("\n")
    print(f"Wrote predictions to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

