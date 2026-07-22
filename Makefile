.PHONY: install start stop status health prisma-check lint format docker-config docker-up docker-down docker-logs clean

COMPOSE ?= $(shell if command -v podman >/dev/null 2>&1; then printf 'podman compose'; else printf 'docker compose'; fi)
COMPOSE_FILE ?= deploy/docker-compose.yml
COMPOSE_ENV_FILE ?= .env

install:
	uv sync

start:
	./deploy/scripts/start.sh

stop:
	./deploy/scripts/stop.sh

status:
	./deploy/scripts/status.sh

health:
	./deploy/scripts/wait-for-health.sh

prisma-check:
	uv run python tools/check_prisma.py

lint:
	uv run ruff check .

format:
	uv run ruff format .

docker-config:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) config --quiet

docker-up:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) up -d --build

docker-down:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) down

docker-logs:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) logs -f litellm

clean:
	rm -f logs/litellm.pid
	rm -f logs/*.log
