# Git hooks and commit workflow

This project uses lightweight, fast Git hooks to catch common mistakes before commits and pushes.

## Enable hooks

Run once per clone:

```bash
make hooks-install
```

This sets:

```bash
git config core.hooksPath .githooks
```

## Hooks

### `pre-commit`

Runs:

```bash
uv run python tools/quality_checks.py --staged
```

Checks:

- blocked local-only files are not staged (`.env.local`, logs, `.venv`, IDE state, local Claude settings/plans)
- committed `.env` still contains placeholder values only
- staged text files do not contain likely real secrets
- changed shell scripts pass `bash -n`
- changed YAML files parse with PyYAML
- Python changes pass `uv run ruff check .`

### `commit-msg`

Enforces Conventional Commits:

```text
type(scope): short summary
```

Allowed types:

- `feat`
- `fix`
- `docs`
- `chore`
- `refactor`
- `test`
- `build`
- `ci`
- `perf`
- `style`
- `revert`
- `ops`

Examples:

```text
chore: add project quality hooks
fix(deploy): resolve Podman database host mapping
docs(workflow): document review report process
ops(litellm): update gateway aliases
```

### `pre-push`

Runs the full fast review:

```bash
uv run python tools/quality_checks.py
```

This intentionally does **not** run Podman builds or service startup tests because those are slower and require valid local credentials. Use them manually when deployment behavior changes.

## Claude Code commit behavior

Claude should not commit or push without asking first. The preferred handoff is:

1. Summary of changed files.
2. Checks that were run.
3. Proposed commit message.
4. Exact commit command.
5. Exact push command.
6. Ask for confirmation.

Example:

```bash
git add .
git commit -m "chore: add project quality hooks" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

If Claude Code is blocked from pushing by safety policy, the user should run the printed `git push` command.

## Local environment convention

- `.env` is committed as a placeholder template.
- Put real local secrets in `.env.local` or another ignored file.
- Run local checks with real values when needed:

```bash
ENV_FILE=.env.local uv run python tools/check_prisma.py
make docker-up COMPOSE_ENV_FILE=.env.local
```
