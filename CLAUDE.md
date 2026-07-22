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

# Equivalent direct scripts
./deploy/scripts/start.sh
./deploy/scripts/status.sh
./deploy/scripts/stop.sh

# Run the Prisma/PostgreSQL connectivity check
make prisma-check
uv run python tools/check_prisma.py

# Lint/format Python files
make lint
make format

# Podman/Docker Compose deployment helpers
make docker-config
make docker-up
make docker-logs
make docker-down
```

The project uses `uv` with `pyproject.toml` and `uv.lock`. Runtime dependencies are LiteLLM with its proxy extra, Prisma, python-dotenv, and PyYAML. Ruff is the development linter/formatter.

## Architecture overview

This repository is an engineered deployment wrapper for a LiteLLM Gateway, not a custom application server.

- `config/litellm.yaml` is the active LiteLLM proxy configuration. It reads `LITELLM_MASTER_KEY`, `DATABASE_URL`, `ICA_BASE`, and `ICA_KEY` from the environment and defines Claude-compatible aliases, existing custom aliases, plus router settings. Preserve the existing model mapping semantics unless the user asks to change routing.
- `config/litellm.backup.yaml` is a historical/alternate LiteLLM config. Treat `config/litellm.yaml` as the runtime source.
- `.env` is committed as a placeholder environment template. Do not commit real local secrets; keep them in `.env.local` or another ignored file when needed.
- `deploy/scripts/start.sh` locates the repo root dynamically, loads `.env`, starts `litellm --config config/litellm.yaml` on `LITELLM_HOST`/`LITELLM_PORT` (default `4001`), writes logs to `logs/litellm.log`, and records `logs/litellm.pid`.
- `deploy/scripts/status.sh` reports the PID/port state and calls `/health` and `/v1/models`. It uses `LITELLM_MASTER_KEY` from `.env` when available and does not contain a fallback secret.
- `deploy/scripts/stop.sh` stops by `logs/litellm.pid` first and falls back to the configured port.
- `deploy/Dockerfile` and `deploy/docker-compose.yml` provide container deployment. Compose uses `.env`, exposes host `${LITELLM_PORT:-4001}` to the same container port, mounts `config/litellm.yaml` read-only, and maps `litellm.top` to the host gateway for local database access. `Makefile` prefers `podman compose` and falls back to `docker compose`.
- `tools/check_prisma.py` is an async Prisma connectivity check. It loads `.env`, reads `DATABASE_URL`, masks credentials in output, and runs `SELECT 1`.
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
