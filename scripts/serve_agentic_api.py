from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the AdaptiveRoute FastAPI Agentic API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument(
        "--load-at-startup",
        action="store_true",
        help="Accepted for backward compatibility. Use ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_LOAD_AT_STARTUP for model loading.",
    )
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("adaptiveroute.api.app:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
