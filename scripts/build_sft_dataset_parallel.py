from __future__ import annotations

import argparse
import json
import math
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
    parser = argparse.ArgumentParser(description="Build SFT data with parallel, non-overlapping seed shards.")
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--num-customers", type=int, default=8)
    parser.add_argument("--num-vehicles", type=int, default=2)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--format", choices=["full", "compact"], default="compact")
    parser.add_argument(
        "--profile",
        choices=["balanced", "capacity_tight", "blocked_arc", "mixed_hard", "capacity_extreme", "blocked_capacity"],
        default="balanced",
    )
    parser.add_argument("--min-chunk-size", type=int, default=10)
    parser.add_argument("--keep-shards", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if args.workers < 1:
        raise ValueError("--workers must be >= 1")

    out_dir = Path(args.out_dir)
    shard_root = out_dir / ".shards"
    shard_root.mkdir(parents=True, exist_ok=True)

    processes: list[tuple[int, Path, subprocess.Popen]] = []
    shard_size = math.ceil(args.n / args.workers)
    seed_stride = shard_size * 20

    for worker_idx in range(args.workers):
        shard_n = min(shard_size, args.n - worker_idx * shard_size)
        if shard_n <= 0:
            break
        shard_dir = shard_root / f"shard_{worker_idx:02d}"
        shard_seed = args.seed_start + worker_idx * seed_stride
        log_path = shard_root / f"shard_{worker_idx:02d}.log"
        command = [
            sys.executable,
            "scripts/build_sft_dataset_chunked.py",
            "--n",
            str(shard_n),
            "--chunk-size",
            str(args.chunk_size),
            "--min-chunk-size",
            str(args.min_chunk_size),
            "--seed-start",
            str(shard_seed),
            "--num-customers",
            str(args.num_customers),
            "--num-vehicles",
            str(args.num_vehicles),
            "--out-dir",
            str(shard_dir),
            "--format",
            args.format,
            "--profile",
            args.profile,
            "--keep-chunks",
        ]
        if args.resume:
            command.append("--resume")

        print(f"[parallel] starting shard {worker_idx}: n={shard_n}, seed_start={shard_seed}, out={shard_dir}")
        log_file = log_path.open("a", encoding="utf-8")
        process = subprocess.Popen(command, stdout=log_file, stderr=subprocess.STDOUT)
        processes.append((worker_idx, log_path, process))

    failed = False
    for worker_idx, log_path, process in processes:
        return_code = process.wait()
        print(f"[parallel] shard {worker_idx} exited with {return_code}; log={log_path}")
        if return_code != 0:
            failed = True

    if failed:
        print("[parallel] at least one shard failed; rerun with --resume after inspecting shard logs", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for shard_dir in sorted(shard_root.glob("shard_*")):
        for split in ("sft_train.jsonl", "sft_val.jsonl", "sft_test.jsonl"):
            rows.extend(read_jsonl(shard_dir / split))

    rows = rows[: args.n]
    train_end = int(len(rows) * 0.8)
    val_end = int(len(rows) * 0.9)
    write_jsonl(out_dir / "sft_train.jsonl", rows[:train_end])
    write_jsonl(out_dir / "sft_val.jsonl", rows[train_end:val_end])
    write_jsonl(out_dir / "sft_test.jsonl", rows[val_end:])

    print(f"Requested: {args.n}")
    print(f"Written: {len(rows)}")
    print(f"Output: {out_dir}")
    print(f"Splits: train={train_end}, val={val_end - train_end}, test={len(rows) - val_end}")

    if not args.keep_shards:
        shutil.rmtree(shard_root)

    return 0 if len(rows) == args.n else 1


if __name__ == "__main__":
    raise SystemExit(main())
