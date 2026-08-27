from __future__ import annotations

import argparse
import json
from pathlib import Path

from adaptiveroute.data.generator import generate_scenario
from adaptiveroute.domain.serialization import scenario_to_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic AdaptiveRoute scenarios.")
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--num-customers", type=int, default=8)
    parser.add_argument("--num-vehicles", type=int, default=2)
    parser.add_argument("--out", default="data/generated/scenarios.jsonl")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file:
        for offset in range(args.n):
            seed = args.seed_start + offset
            scenario = generate_scenario(
                seed=seed,
                num_customers=args.num_customers,
                num_vehicles=args.num_vehicles,
                clustered=seed % 2 == 0,
            )
            file.write(json.dumps(scenario_to_dict(scenario), ensure_ascii=False, sort_keys=True))
            file.write("\n")

    print(f"Wrote {args.n} scenarios to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

