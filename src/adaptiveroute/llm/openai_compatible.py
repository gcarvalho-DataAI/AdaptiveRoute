from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatResponse:
    content: str
    model: str
    raw: dict[str, Any]
    reasoning_content: str | None = None


@dataclass(frozen=True)
class OpenAICompatibleSettings:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 60.0
    temperature: float = 0.1

    @classmethod
    def from_env(cls, prefix: str = "ADAPTIVEROUTE_ORCHESTRATOR") -> "OpenAICompatibleSettings":
        base_url = (
            os.getenv(f"{prefix}_BASE_URL")
            or os.getenv("OPENAI_ENDPOINT")
            or os.getenv("OPENAI_BASE_URL")
            or "http://127.0.0.1:8000/v1"
        )
        api_key = os.getenv(f"{prefix}_API_KEY") or os.getenv("OPENAI_API_KEY") or "local"
        model = os.getenv(f"{prefix}_MODEL") or os.getenv("OPENAI_CHAT_MODEL") or os.getenv("OPENAI_MODEL") or "auto"
        timeout = float(os.getenv(f"{prefix}_TIMEOUT_SECONDS", "60"))
        temperature = float(os.getenv(f"{prefix}_TEMPERATURE", "0.1"))
        return cls(
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=model,
            timeout_seconds=timeout,
            temperature=temperature,
        )


class OpenAICompatibleChatClient:
    def __init__(self, settings: OpenAICompatibleSettings):
        self._settings = settings
        self._model = settings.model if settings.model.lower() not in {"auto", "best", "default"} else self._resolve_model()

    @property
    def selected_model(self) -> str:
        return self._model

    def available_models(self) -> list[str]:
        url = f"{self._settings.base_url}/models"
        try:
            payload = self._request_json(url=url, method="GET", payload=None)
        except (RuntimeError, ValueError):
            return []

        models: list[str] = []
        data = payload.get("data")
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("id"):
                    models.append(str(item["id"]))

        raw_models = payload.get("models")
        if isinstance(raw_models, list):
            for item in raw_models:
                if isinstance(item, str):
                    models.append(item)
                elif isinstance(item, dict):
                    model_id = item.get("id") or item.get("model") or item.get("name")
                    if model_id:
                        models.append(str(model_id))

        return sorted(set(models))

    def chat(
        self,
        *,
        system: str,
        user: str,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatResponse:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._settings.temperature if temperature is None else temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        raw = self._request_json(
            url=f"{self._settings.base_url}/chat/completions",
            method="POST",
            payload=payload,
        )
        message = _first_message(raw)
        content = str(message.get("content") or "")
        reasoning_content = message.get("reasoning_content")
        if not content:
            raise RuntimeError("OpenAI-compatible chat response did not include message content.")
        return ChatResponse(
            content=content,
            model=str(raw.get("model") or self._model),
            raw=raw,
            reasoning_content=str(reasoning_content) if reasoning_content is not None else None,
        )

    def _resolve_model(self) -> str:
        models = self.available_models()
        if not models:
            return self._settings.model
        preferred = ("qwen-linkedin", "qwen", "kimi", "llama")
        for token in preferred:
            matches = [model for model in models if token in model.lower()]
            if matches:
                return sorted(matches, key=_model_score, reverse=True)[0]
        return sorted(models, key=_model_score, reverse=True)[0]

    def _request_json(self, *, url: str, method: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }
        req = request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self._settings.timeout_seconds) as resp:
                text = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible request failed with HTTP {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"OpenAI-compatible request failed: {exc}") from exc

        try:
            decoded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI-compatible response was not valid JSON: {text[:200]}") from exc
        if not isinstance(decoded, dict):
            raise ValueError("OpenAI-compatible response must be a JSON object.")
        return decoded


def _first_message(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenAI-compatible chat response did not include choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise RuntimeError("OpenAI-compatible chat choice must be an object.")
    message = first.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("OpenAI-compatible chat choice did not include a message object.")
    return message


def _model_score(model_id: str) -> tuple[int, int]:
    lowered = model_id.lower()
    params = 0
    for marker in ("70b", "32b", "14b", "8b", "7b", "3b", "0.5b"):
        if marker in lowered:
            params = int(float(marker.removesuffix("b")) * 10)
            break
    quant = 0
    if "q2" in lowered:
        quant = -3
    elif "q3" in lowered:
        quant = -2
    elif "q4" in lowered:
        quant = -1
    elif "awq" in lowered:
        quant = 0
    return (params, quant)
