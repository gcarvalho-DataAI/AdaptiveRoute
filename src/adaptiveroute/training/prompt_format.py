from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = (
    "You are AdaptiveRoute's routing candidate generator. "
    "Return only valid JSON with a top-level routes object. "
    "Every route must start and end at D0, customers must not be duplicated, "
    "and unavailable customers must not be included."
)


def build_user_prompt(row: dict[str, Any]) -> str:
    return (
        "Replan this CVRP scenario after the operational event.\n\n"
        f"Input JSON:\n{json.dumps(row['input'], ensure_ascii=False, sort_keys=True)}"
    )


def build_assistant_response(row: dict[str, Any]) -> str:
    return json.dumps(row["output"], ensure_ascii=False, sort_keys=True)


def to_messages_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(row)},
            {"role": "assistant", "content": build_assistant_response(row)},
        ],
        "metadata": row.get("metadata", {}),
    }


def to_prompt_completion_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt": f"{SYSTEM_PROMPT}\n\n{build_user_prompt(row)}\n\nAnswer:",
        "completion": build_assistant_response(row),
        "metadata": row.get("metadata", {}),
    }
