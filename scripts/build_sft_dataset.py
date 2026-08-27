from __future__ import annotations

import argparse
import json
from pathlib import Path

from adaptiveroute.training.dataset_builder import build_sft_examples


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an SFT dataset from synthetic CVRP replanning examples.")
    parser.add_argument("--n", type=int, default=100, help="Total number of examples to generate.")
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--num-customers", type=int, default=8)
    parser.add_argument("--num-vehicles", type=int, default=2)
    parser.add_argument("--out-dir", default="data/training")
    parser.add_argument("--format", choices=["full", "compact"], default="full", help="Dataset input format.")
    parser.add_argument(
        "--profile",
        choices=["balanced", "capacity_tight", "blocked_arc", "mixed_hard", "capacity_extreme", "blocked_capacity"],
        default="balanced",
        help="Synthetic data profile.",
    )
    args = parser.parse_args()

    examples, stats = build_sft_examples(
        n=args.n,
        seed_start=args.seed_start,
        num_customers=args.num_customers,
        num_vehicles=args.num_vehicles,
        output_format=args.format,
        profile=args.profile,
    )

    train_end = int(len(examples) * 0.8)
    val_end = int(len(examples) * 0.9)
    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / "sft_train.jsonl", examples[:train_end])
    write_jsonl(out_dir / "sft_val.jsonl", examples[train_end:val_end])
    write_jsonl(out_dir / "sft_test.jsonl", examples[val_end:])

    print(f"Requested: {stats.requested}")
    print(f"Written: {stats.written}")
    print(f"Skipped: {stats.skipped}")
    print(f"Output: {out_dir}")
    return 0 if stats.written == args.n else 1


if __name__ == "__main__":
    raise SystemExit(main())
