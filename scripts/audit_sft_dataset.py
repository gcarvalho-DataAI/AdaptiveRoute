from __future__ import annotations

import argparse
import json
from pathlib import Path

from adaptiveroute.training.audit import audit_dataset, audit_to_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit compact AdaptiveRoute SFT datasets.")
    parser.add_argument("dataset_dir", help="Directory containing sft_train.jsonl, sft_val.jsonl, and sft_test.jsonl.")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    paths = [dataset_dir / "sft_train.jsonl", dataset_dir / "sft_val.jsonl", dataset_dir / "sft_test.jsonl"]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        print(json.dumps({"error": "missing_files", "files": missing}, indent=2))
        return 1

    audit = audit_dataset(paths)
    print(json.dumps(audit_to_dict(audit), indent=2, sort_keys=True))
    return 0 if audit.invalid_rows == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
