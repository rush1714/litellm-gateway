# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

```bash
# Install/sync Python dependencies with uv
uv sync
make install

# Start, inspect, and stop the local LiteLLM proxy
make start
make status
make stop
make health

# Equivalent direct scripts
./deploy/scripts/start.sh
./deploy/scripts/status.sh
./deploy/scripts/stop.sh
./deploy/scripts/wait-for-health.sh

# Run connectivity and health checks
make redis-check
uv run python tools/check_redis.py

make prisma-check
uv run python tools/check_prisma.py

# Regenerate Prisma client after schema/migration updates
uv run prisma generate --schema .venv/lib/python3.12/site-packages/litellm_proxy_extras/schema.prisma

# Run tests
PYTHONPATH=. uv run python tests/test_ica_responses_proxy.py
PYTHONPATH=. uv run python tests/test_usage_api.py
make usage-api-test

# Lint/format/review
make lint
make format
make review
make review-report
make hooks-install

# Podman/Docker Compose deployment helpers
make docker-config
make docker-up
make docker-logs
make docker-down
```

The project uses `uv` with `pyproject.toml` and `uv.lock`. Runtime dependencies are LiteLLM (`1.106.1`) with its proxy extra, Prisma, Redis (`redis`, `hiredis`), python-dotenv, FastAPI/Uvicorn, and PyYAML. Ruff is the development linter/formatter.

## Commit and push workflow

- Do not commit or push without confirmation. After code changes, present:
  - summary of changed files,
  - checks run and their results,
  - proposed Conventional Commit message,
  - exact `git commit` command,
  - exact `make sync-branches` command for pushing `main` and syncing `dev`/`sit`.
- After the user confirms, run the commit and branch sync flow automatically when the harness permits it. If the harness blocks push, ask the user to run the provided command.
- Use Conventional Commits. Allowed types are `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `ci`, `perf`, `style`, `revert`, and `ops`.
- If a review or security scan is meaningful, write a Markdown report under `docs/reports/` and mention whether it is committed.

## Architecture overview

This repository is an engineered deployment wrapper for a LiteLLM Gateway, not a custom application server.

- `config/litellm.yaml` is the source LiteLLM proxy configuration. It reads `LITELLM_MASTER_KEY`, `DATABASE_URL`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `ICA_BASE`, and `ICA_KEY` from the environment and defines Claude-compatible aliases, best-use custom aliases, plus router settings.
  - `router_settings`: configured with `simple-shuffle`, `num_retries: 2`, `timeout: 180`, Redis coordination, and a service/error `fallbacks` chain prioritizing Gemini series (`gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`) and `GLM-5.3`. Local Ollama models (`local-*`) are intentionally excluded from fallbacks to maintain isolation. `context_window_fallbacks` routes smaller context models to 1M Gemini.
  - `litellm_settings`: enables Redis response caching, `drop_params: true`, and `use_chat_completions_url_for_anthropic_messages: true` for Claude Code compatibility with `/v1/messages`.
  - `docs/can-use-models-list.md` is the source model catalog; `docs/model-routing.md` documents the alias/fallback strategy. Preserve the existing alias intent unless the user asks to change routing.
- `config/litellm.backup.yaml` is a historical/alternate LiteLLM config. Treat `config/litellm.yaml` as the source config; startup writes a generated runtime config under `logs/` or `/tmp`.
- `.env` is committed as a placeholder environment template. Do not commit real local secrets; keep them in `.env.local` or another ignored file when needed.
  - `LITELLM_ENABLE_DATABASE` controls whether startup keeps the LiteLLM `database_url` setting.
  - `LITELLM_ENABLE_REDIS` controls whether startup keeps Redis coordination and response caching settings. When `REDIS_PASSWORD` is empty, startup cleanly strips the password field from the generated runtime config.
- `deploy/scripts/start.sh`:
  - Locates the repo root dynamically and resolves symlinks from `/Users/guobiao/bin`.
  - Loads `.env` without overriding explicit environment variables.
  - Prepares a runtime config with `deploy/scripts/prepare-litellm-config.py`.
  - Auto-checks and links the Prisma query-engine binary if needed.
  - When `LITELLM_USE_ICA_PROXY=true`, starts the local `ica-responses-proxy` on port 4101 (PID managed) to append `api-version` for `/responses` while preserving `/chat/completions` and sanitizing unsupported `prompt_cache_key` parameters.
  - Starts `litellm` on `LITELLM_HOST`/`LITELLM_PORT` (default `4001`), writes logs to `logs/litellm-$LITELLM_PORT.log`, and records `logs/litellm-$LITELLM_PORT.pid`.
- `deploy/scripts/status.sh` reports the configured port state, ICA proxy state, Redis connectivity, and calls `/health` and `/v1/models`. It uses `LITELLM_MASTER_KEY` from `.env` when available and does not contain a fallback secret.
- `deploy/scripts/stop.sh` stops both the LiteLLM gateway and the ICA proxy listener on the configured ports.
- `deploy/Dockerfile` and `deploy/docker-compose.yml` provide container deployment. Compose uses `.env`, exposes host `${LITELLM_PORT:-4001}`, maps `host.docker.internal` for local Redis/Ollama access, mounts `config/litellm.yaml` read-only, and includes a PostgreSQL service. `make docker-up` starts PostgreSQL only when `LITELLM_ENABLE_DATABASE` is enabled. `Makefile` prefers `podman compose` and falls back to `docker compose`.
- `tools/check_redis.py` verifies local Redis connectivity, reports Redis server version and ping roundtrip, and performs write/read/delete self-tests.
- `tools/check_prisma.py` is an async Prisma connectivity check. It loads `.env`, skips when `LITELLM_ENABLE_DATABASE=false`, reads `DATABASE_URL`, masks credentials in output, and runs `SELECT 1`.
- `tools/quality_checks.py` provides fast hook/review checks (blocked files, placeholder verification, secret scanning, shell syntax, YAML syntax, and ruff linting) and optional Markdown reports.
- `docs/sql/litellm-usage-queries.sql` contains reporting queries for the LiteLLM PostgreSQL `"LiteLLM_SpendLogs"` table; camelCase columns such as `"startTime"` and `"endTime"` must be quoted.

## OpenSpec workflow

The repo includes OpenSpec configuration at `openspec/config.yaml` with `schema: spec-driven`, plus Claude commands/skills under `.claude/commands/opsx/` and `.claude/skills/`. For planned changes that should go through OpenSpec, use the existing `/opsx:*` commands or matching skills rather than hand-creating change artifacts.

Useful OpenSpec CLI commands reflected by the local skill files:

```bash
openspec new change "<change-name>"
openspec status --change "<change-name>" --json
openspec instructions <artifact-id> --change "<change-name>" --json
openspec instructions apply --change "<change-name>" --json
openspec list --json
```

The OpenSpec skills emphasize using CLI-reported `planningHome`, `changeRoot`, `artifactPaths`, and `contextFiles` instead of assuming fixed artifact paths.
