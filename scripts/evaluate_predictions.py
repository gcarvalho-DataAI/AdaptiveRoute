from __future__ import annotations

import argparse
import json
from pathlib import Path

from adaptiveroute.training.prediction_eval import evaluate_predictions, summary_to_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate model route predictions with deterministic validation.")
    parser.add_argument("--dataset", required=True, help="Compact SFT JSONL used to generate predictions.")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--details-out")
    args = parser.parse_args()

    summary, details = evaluate_predictions(Path(args.dataset), Path(args.predictions))
    print(json.dumps(summary_to_dict(summary), indent=2, sort_keys=True))
    if args.details_out:
        out_path = Path(args.details_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as file:
            for row in details:
                file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                file.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

