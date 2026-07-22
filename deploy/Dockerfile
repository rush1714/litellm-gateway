FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    LITELLM_CONFIG=/app/config/litellm.yaml \
    LITELLM_PORT=4001

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock* README.md ./
RUN if [ -f uv.lock ]; then uv sync --frozen --no-dev; else uv sync --no-dev; fi

RUN prisma generate --schema=/app/.venv/lib/python3.12/site-packages/litellm/proxy/schema.prisma

COPY config ./config

EXPOSE 4001

CMD ["sh", "-c", "exec litellm --config ${LITELLM_CONFIG:-/app/config/litellm.yaml} --host 0.0.0.0 --port ${LITELLM_PORT:-4001}"]
