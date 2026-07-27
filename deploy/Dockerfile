FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    LITELLM_CONFIG=/app/config/litellm.yaml \
    LITELLM_RUNTIME_CONFIG=/tmp/litellm-runtime.yaml \
    LITELLM_PORT=4001

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock* README.md ./
RUN if [ -f uv.lock ]; then uv sync --frozen --no-dev; else uv sync --no-dev; fi

RUN prisma generate --schema=/app/.venv/lib/python3.12/site-packages/litellm/proxy/schema.prisma

COPY config ./config
COPY deploy/scripts/prepare-litellm-config.py ./deploy/scripts/prepare-litellm-config.py

EXPOSE 4001

CMD ["sh", "-c", "python /app/deploy/scripts/prepare-litellm-config.py ${LITELLM_CONFIG:-/app/config/litellm.yaml} ${LITELLM_RUNTIME_CONFIG:-/tmp/litellm-runtime.yaml} && exec litellm --config ${LITELLM_RUNTIME_CONFIG:-/tmp/litellm-runtime.yaml} --host 0.0.0.0 --port ${LITELLM_PORT:-4001}"]
