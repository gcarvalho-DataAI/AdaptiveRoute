from __future__ import annotations

import argparse
import json

from adaptiveroute.agentic import AgenticRoutingService
from adaptiveroute.agentic.candidates import ApiRoutingCandidateGenerator
from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.llm.openai_compatible import OpenAICompatibleChatClient, OpenAICompatibleSettings
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AdaptiveRoute agentic replanning workflow on the demo scenario.")
    parser.add_argument(
        "message",
        nargs="?",
        default="Accident between C1 and C3. Avoid that road.",
        help="Operational update to parse and replan against.",
    )
    parser.add_argument("--llm-orchestrator", action="store_true", help="Use OpenAI-compatible LLM event extraction.")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible base URL, e.g. http://127.0.0.1:8000/v1.")
    parser.add_argument("--api-key", default=None, help="OpenAI-compatible API key. Use 'local' for local servers.")
    parser.add_argument("--model", default=None, help="Orchestrator model name. Use 'auto' to select from /models.")
    parser.add_argument("--api-routing-model", action="store_true", help="Use an OpenAI-compatible routing policy model for candidate generation.")
    parser.add_argument("--routing-base-url", default=None, help="Routing policy OpenAI-compatible base URL.")
    parser.add_argument("--routing-api-key", default=None, help="Routing policy API key.")
    parser.add_argument("--routing-model", default=None, help="Routing policy model name.")
    parser.add_argument("--from-env", action="store_true", help="Build orchestrator and routing policy backends from ADAPTIVEROUTE_* env vars.")
    args = parser.parse_args()

    engine = PyomoHighsEngine()
    if args.from_env:
        service = AgenticRoutingService.from_env(engine)
        result = service.run(build_demo_scenario(), args.message)
        print(json.dumps(result.response, indent=2))
        return 0 if result.succeeded else 1

    candidate_generator = None
    if args.api_routing_model:
        env_routing_settings = OpenAICompatibleSettings.from_env(prefix="ADAPTIVEROUTE_ROUTING_POLICY")
        routing_settings = OpenAICompatibleSettings(
            base_url=(args.routing_base_url or env_routing_settings.base_url).rstrip("/"),
            api_key=args.routing_api_key or env_routing_settings.api_key,
            model=args.routing_model or env_routing_settings.model,
            timeout_seconds=env_routing_settings.timeout_seconds,
            temperature=env_routing_settings.temperature,
        )
        candidate_generator = ApiRoutingCandidateGenerator(OpenAICompatibleChatClient(routing_settings))

    if args.llm_orchestrator:
        env_settings = OpenAICompatibleSettings.from_env()
        settings = OpenAICompatibleSettings(
            base_url=(args.base_url or env_settings.base_url).rstrip("/"),
            api_key=args.api_key or env_settings.api_key,
            model=args.model or env_settings.model,
            timeout_seconds=env_settings.timeout_seconds,
            temperature=env_settings.temperature,
        )
        service = AgenticRoutingService.with_openai_compatible_orchestrator(
            engine,
            settings=settings,
            candidate_generator=candidate_generator,
        )
    else:
        service = AgenticRoutingService(engine, candidate_generator=candidate_generator)
    result = service.run(build_demo_scenario(), args.message)
    print(json.dumps(result.response, indent=2))
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
