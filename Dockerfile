FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


WORKDIR Relay/

COPY pyproject.toml uv.lock .

RUN uv sync --no-dev --frozen

COPY . .
