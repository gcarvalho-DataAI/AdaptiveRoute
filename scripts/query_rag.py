from __future__ import annotations

import argparse
import json

from adaptiveroute.api.dependencies import get_rag_service
from adaptiveroute.config import load_project_env


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the configured AdaptiveRoute RAG repository.")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    load_project_env()
    result = get_rag_service().query(args.query, limit=args.limit)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
