FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY scripts ./scripts
COPY docs ./docs

ARG UV_SYNC_ARGS="--no-dev"
RUN uv sync --frozen ${UV_SYNC_ARGS}

EXPOSE 8090

CMD ["uv", "run", "--no-dev", "uvicorn", "adaptiveroute.api.app:app", "--host", "0.0.0.0", "--port", "8090"]
