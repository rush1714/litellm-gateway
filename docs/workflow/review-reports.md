# Review reports

Review reports live under:

```text
docs/reports/
```

The directory is tracked with `.gitkeep`; generated reports can be committed when they are useful for audit/history, or left local for quick checks.

## Generate a fast quality report

```bash
make review-report
```

Default output:

```text
docs/reports/quality-report.md
```

Custom output:

```bash
make review-report REPORT_FILE=docs/reports/$(date +%Y%m%d)-quality-report.md
```

## Run checks without writing a report

```bash
make review
```

## What the report covers

`tools/quality_checks.py` reports:

- local-only files accidentally staged or included
- placeholder `.env` policy
- likely secret patterns in text files
- shell syntax checks
- YAML parse checks
- Ruff checks for Python files

## What it does not cover

The fast report is intentionally not a full security audit. For larger changes, add one or more of:

```bash
make prisma-check ENV_FILE=.env.local
make docker-up COMPOSE_ENV_FILE=.env.local
make docker-down COMPOSE_ENV_FILE=.env.local
```

If using Claude Code's official `code-review` plugin, run a review after implementation and summarize key findings in a report under `docs/reports/` when useful.

## Report naming suggestions

```text
docs/reports/YYYYMMDD-quality-report.md
docs/reports/YYYYMMDD-security-review.md
docs/reports/YYYYMMDD-deploy-validation.md
docs/reports/YYYYMMDD-pr-review.md
```
