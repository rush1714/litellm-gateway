.PHONY: install start stop status health prisma-check lint format review review-report hooks-install sync-branches docker-config docker-up docker-down docker-logs clean

COMPOSE ?= $(shell if command -v podman >/dev/null 2>&1; then printf 'podman compose'; else printf 'docker compose'; fi)
COMPOSE_FILE ?= deploy/docker-compose.yml
COMPOSE_ENV_FILE ?= .env
REPORT_FILE ?= docs/reports/quality-report.md

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

review:
	uv run python tools/quality_checks.py

review-report:
	uv run python tools/quality_checks.py --report $(REPORT_FILE)

hooks-install:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push

sync-branches:
	./tools/sync_branches.sh

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
