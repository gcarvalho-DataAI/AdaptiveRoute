from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SFT data in subprocess chunks to isolate native solver crashes.")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--num-customers", type=int, default=8)
    parser.add_argument("--num-vehicles", type=int, default=2)
    parser.add_argument("--out-dir", default="data/training_compact")
    parser.add_argument("--format", choices=["full", "compact"], default="compact")
    parser.add_argument(
        "--profile",
        choices=["balanced", "capacity_tight", "blocked_arc", "mixed_hard", "capacity_extreme", "blocked_capacity"],
        default="balanced",
        help="Synthetic data profile.",
    )
    parser.add_argument("--keep-chunks", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Reuse existing chunk outputs and continue from the next seed.")
    parser.add_argument("--min-chunk-size", type=int, default=10, help="Smallest retry chunk size after native crashes.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    chunk_root = out_dir / ".chunks"
    chunk_root.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = load_existing_rows(chunk_root) if args.resume else []
    if len(all_rows) > args.n:
        all_rows = all_rows[: args.n]

    remaining = args.n - len(all_rows)
    chunk_index = next_chunk_index(chunk_root) if args.resume else 0
    seed = next_seed(args.seed_start, all_rows)
    target_chunk_size = args.chunk_size

    while remaining > 0:
        current_n = min(target_chunk_size, remaining)
        chunk_dir = chunk_root / f"chunk_{chunk_index:04d}"
        print(f"[chunk {chunk_index}] generating {current_n} examples from seed {seed}")
        completed = run_chunk(
            n=current_n,
            seed=seed,
            num_customers=args.num_customers,
            num_vehicles=args.num_vehicles,
            chunk_dir=chunk_dir,
            output_format=args.format,
            profile=args.profile,
        )
        if completed.returncode != 0:
            print(f"[chunk {chunk_index}] failed with exit code {completed.returncode}", file=sys.stderr)
            if current_n > args.min_chunk_size:
                target_chunk_size = max(args.min_chunk_size, current_n // 2)
                print(f"[chunk {chunk_index}] retrying from seed {seed} with chunk size {target_chunk_size}")
                continue
            print(f"[chunk {chunk_index}] skipping seed range {seed}-{seed + current_n - 1}")
            seed += current_n
            continue

        rows = read_chunk_rows(chunk_dir)
        all_rows.extend(rows)

        remaining = args.n - len(all_rows)
        seed = next_seed(seed + current_n, all_rows)
        chunk_index += 1
        target_chunk_size = args.chunk_size

    train_end = int(len(all_rows) * 0.8)
    val_end = int(len(all_rows) * 0.9)
    write_jsonl(out_dir / "sft_train.jsonl", all_rows[:train_end])
    write_jsonl(out_dir / "sft_val.jsonl", all_rows[train_end:val_end])
    write_jsonl(out_dir / "sft_test.jsonl", all_rows[val_end:])

    print(f"Requested: {args.n}")
    print(f"Written: {len(all_rows)}")
    print(f"Output: {out_dir}")
    print(f"Splits: train={train_end}, val={val_end - train_end}, test={len(all_rows) - val_end}")

    if not args.keep_chunks:
        shutil.rmtree(chunk_root)

    return 0 if len(all_rows) == args.n else 1


def run_chunk(
    *,
    n: int,
    seed: int,
    num_customers: int,
    num_vehicles: int,
    chunk_dir: Path,
    output_format: str,
    profile: str,
) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        "scripts/build_sft_dataset.py",
        "--n",
        str(n),
        "--seed-start",
        str(seed),
        "--num-customers",
        str(num_customers),
        "--num-vehicles",
        str(num_vehicles),
        "--out-dir",
        str(chunk_dir),
        "--format",
        output_format,
        "--profile",
        profile,
    ]
    return subprocess.run(command, check=False)


def read_chunk_rows(chunk_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for split in ("sft_train.jsonl", "sft_val.jsonl", "sft_test.jsonl"):
        rows.extend(read_jsonl(chunk_dir / split))
    return rows


def load_existing_rows(chunk_root: Path) -> list[dict]:
    rows: list[dict] = []
    for chunk_dir in sorted(chunk_root.glob("chunk_*")):
        rows.extend(read_chunk_rows(chunk_dir))
    return rows


def next_chunk_index(chunk_root: Path) -> int:
    indexes: list[int] = []
    for chunk_dir in chunk_root.glob("chunk_*"):
        suffix = chunk_dir.name.rsplit("_", maxsplit=1)[-1]
        if suffix.isdigit():
            indexes.append(int(suffix))
    return max(indexes, default=-1) + 1


def next_seed(default_seed: int, rows: list[dict]) -> int:
    seeds = [int(row.get("metadata", {}).get("seed", 0)) for row in rows if row.get("metadata", {}).get("seed")]
    return max(seeds, default=default_seed - 1) + 1


if __name__ == "__main__":
    raise SystemExit(main())
