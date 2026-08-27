from __future__ import annotations

import argparse
import json
from pathlib import Path

from adaptiveroute.training.prompt_format import to_messages_row, to_prompt_completion_row


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def convert_file(input_path: Path, output_path: Path, output_format: str) -> int:
    converter = to_messages_row if output_format == "messages" else to_prompt_completion_row
    rows = [converter(row) for row in iter_jsonl(input_path)]
    write_jsonl(output_path, rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert AdaptiveRoute SFT rows to chat training JSONL.")
    parser.add_argument("dataset_dir")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--format", choices=["messages", "prompt_completion"], default="messages")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    out_dir = Path(args.out_dir)
    total = 0
    for split in ("train", "val", "test"):
        total += convert_file(dataset_dir / f"sft_{split}.jsonl", out_dir / f"{split}.jsonl", args.format)
    print(f"Wrote {total} rows to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
