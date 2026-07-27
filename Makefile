.PHONY: install start stop status health prisma-check db-up db-down db-logs db-shell lint format review review-report hooks-install sync-branches docker-config docker-up docker-down docker-logs clean

COMPOSE ?= $(shell if command -v podman >/dev/null 2>&1; then printf 'podman compose'; else printf 'docker compose'; fi)
COMPOSE_FILE ?= deploy/docker-compose.yml
COMPOSE_ENV_FILE ?= .env
COMPOSE_PROJECT_ENV_FILE ?= $(if $(filter /%,$(COMPOSE_ENV_FILE)),$(COMPOSE_ENV_FILE),../$(COMPOSE_ENV_FILE))
export COMPOSE_PROJECT_ENV_FILE
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

db-up:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) up -d postgres
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec -T postgres sh -c 'until pg_isready -U "$${POSTGRES_USER:-litellm}" -d "$${POSTGRES_DB:-litellm}"; do sleep 1; done'

db-down:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) stop postgres

db-logs:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) logs -f postgres

db-shell:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec postgres sh -c 'psql -U "$${POSTGRES_USER:-litellm}" -d "$${POSTGRES_DB:-litellm}"'

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
	@if grep -Eiq '^LITELLM_ENABLE_DATABASE=(false|0|no|off)$$' $(COMPOSE_ENV_FILE); then \
		$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) up -d --build litellm; \
	else \
		$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) up -d postgres; \
		$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec -T postgres sh -c 'until pg_isready -U "$${POSTGRES_USER:-litellm}" -d "$${POSTGRES_DB:-litellm}"; do sleep 1; done'; \
		$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) up -d --build litellm; \
	fi

docker-down:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) down

docker-logs:
	$(COMPOSE) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) logs -f litellm

clean:
	rm -f logs/litellm.pid
	rm -f logs/*.pid
	rm -f logs/*.runtime.yaml
	rm -f logs/*.log
