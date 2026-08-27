from __future__ import annotations

import hashlib
import json
import math
import os
from typing import Any, Protocol
from urllib import error, request


class EmbeddingClient(Protocol):
    @property
    def dimension(self) -> int: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbeddingClient:
    """Deterministic local embedding fallback for tests and CPU-only demos."""

    def __init__(self, dimension: int = 384):
        if dimension <= 0:
            raise ValueError("dimension must be positive.")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_normalize(_hash_embedding(text, self._dimension)) for text in texts]


class ApiEmbeddingClient:
    """OpenAI-compatible embedding client."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        dimension: int,
        timeout_seconds: float = 120.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._dimension = dimension
        self._timeout_seconds = timeout_seconds

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {"model": self._model, "input": texts}
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self._base_url}/embeddings",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Embedding API failed with HTTP {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Embedding API request failed: {exc}") from exc

        data = decoded.get("data")
        if not isinstance(data, list):
            raise ValueError("Embedding API response must include a data list.")
        vectors: list[list[float]] = []
        for item in sorted(data, key=lambda row: row.get("index", 0) if isinstance(row, dict) else 0):
            if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
                raise ValueError("Embedding API item must include an embedding list.")
            vector = [float(value) for value in item["embedding"]]
            vectors.append(_fit_dimension(vector, self._dimension))
        if len(vectors) != len(texts):
            raise ValueError("Embedding API returned a different number of vectors than inputs.")
        return vectors


def build_embedding_client(prefix: str = "ADAPTIVEROUTE_RAG_EMBEDDING") -> EmbeddingClient:
    backend = os.getenv(f"{prefix}_BACKEND", "hash").strip().lower()
    dimension = int(os.getenv(f"{prefix}_DIM", "384"))
    if backend == "hash":
        return HashEmbeddingClient(dimension=dimension)
    if backend == "api":
        return ApiEmbeddingClient(
            base_url=os.getenv(f"{prefix}_BASE_URL", "http://127.0.0.1:8000/v1"),
            api_key=os.getenv(f"{prefix}_API_KEY", "local"),
            model=os.getenv(f"{prefix}_MODEL", "embed-local"),
            dimension=dimension,
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT_SECONDS", "120")),
        )
    raise ValueError(f"Unsupported {prefix}_BACKEND. Use one of: hash, api.")


def _hash_embedding(text: str, dimension: int) -> list[float]:
    vector = [0.0] * dimension
    tokens = text.lower().split()
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    return vector


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _fit_dimension(vector: list[float], dimension: int) -> list[float]:
    if len(vector) == dimension:
        return vector
    if len(vector) > dimension:
        return vector[:dimension]
    return vector + [0.0] * (dimension - len(vector))
