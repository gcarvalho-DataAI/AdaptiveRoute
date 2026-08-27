from __future__ import annotations

import json

from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.services.counterfactual import analyze_counterfactual, counterfactual_to_dict
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def main() -> int:
    scenario = build_demo_scenario()
    result = PyomoHighsEngine().solve(scenario)
    if result.plan is None:
        print(f"Reference solve failed: {result.status} {result.message}")
        return 1

    proposed = {
        "V1": ["D0", "C8", "C2", "C7", "D0"],
        "V2": ["D0", "C1", "C3", "C4", "C5", "C6", "D0"],
    }
    analysis = analyze_counterfactual(scenario, result.plan, proposed)
    print(json.dumps(counterfactual_to_dict(analysis), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

