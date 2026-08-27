from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def load_dataset_dir(dataset_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for split in ("sft_train.jsonl", "sft_val.jsonl", "sft_test.jsonl"):
        path = dataset_dir / split
        if not path.exists():
            raise FileNotFoundError(path)
        rows.extend(read_jsonl(path))
    return rows


def unique_by_seed(rows: list[dict]) -> list[dict]:
    seen: set[int] = set()
    unique: list[dict] = []
    for row in rows:
        seed = int(row.get("metadata", {}).get("seed", -1))
        if seed in seen:
            continue
        seen.add(seed)
        unique.append(row)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge AdaptiveRoute SFT datasets and recreate train/val/test splits.")
    parser.add_argument("dataset_dirs", nargs="+")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--shuffle-seed", type=int, default=42)
    parser.add_argument("--dedupe-seed", action="store_true")
    args = parser.parse_args()

    rows: list[dict] = []
    for dataset_dir in args.dataset_dirs:
        rows.extend(load_dataset_dir(Path(dataset_dir)))

    if args.dedupe_seed:
        rows = unique_by_seed(rows)

    rng = random.Random(args.shuffle_seed)
    rng.shuffle(rows)

    train_end = int(len(rows) * 0.8)
    val_end = int(len(rows) * 0.9)
    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / "sft_train.jsonl", rows[:train_end])
    write_jsonl(out_dir / "sft_val.jsonl", rows[train_end:val_end])
    write_jsonl(out_dir / "sft_test.jsonl", rows[val_end:])

    print(f"Input dirs: {len(args.dataset_dirs)}")
    print(f"Written: {len(rows)}")
    print(f"Output: {out_dir}")
    print(f"Splits: train={train_end}, val={val_end - train_end}, test={len(rows) - val_end}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
