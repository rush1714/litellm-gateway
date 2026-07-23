#!/usr/bin/env python3
"""Fast local quality checks for hooks and Claude review reports."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

SECRET_PATTERNS = [
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b")),
    (
        "PostgreSQL credentials",
        re.compile(r"postgres(?:ql)?://[^\s:@/]+:[^\s:@]+@[^\s]+", re.I),
    ),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----")),
    ("JWT token", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")),
]

ALLOWED_SECRET_VALUES = {
    "sk-change-me",
    "postgresql://user:password@host:5432/litellm?sslmode=disable",
}

BLOCKED_STAGE_PATTERNS = [
    re.compile(r"^\.env\.local$"),
    re.compile(r"^\.env\.[^.].*"),
    re.compile(r"^logs/"),
    re.compile(r"^\.venv/"),
    re.compile(r"^\.idea/"),
    re.compile(r"^\.vscode/"),
    re.compile(r"^\.claude/settings\.local\.json$"),
    re.compile(r"^\.claude/plan-.*\.md$"),
]

TEXT_SUFFIXES = {
    ".cfg",
    ".conf",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: list[str]


def run(command: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT_DIR,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def git_lines(args: list[str]) -> list[str]:
    proc = run(["git", *args])
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line]


def staged_files() -> list[str]:
    return git_lines(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])


def tracked_files() -> list[str]:
    return git_lines(["ls-files", "--cached", "--others", "--exclude-standard"])


def is_text_path(path: str) -> bool:
    p = Path(path)
    return p.name == ".env" or p.suffix.lower() in TEXT_SUFFIXES


def read_staged(path: str) -> str | None:
    proc = run(["git", "show", f":{path}"])
    if proc.returncode != 0:
        return None
    return proc.stdout


def read_worktree(path: str) -> str | None:
    try:
        return (ROOT_DIR / path).read_text(errors="replace")
    except OSError:
        return None


def normalize_match(value: str) -> str:
    return value.strip().strip('"\'')


def check_blocked_staged(files: list[str]) -> CheckResult:
    blocked = []
    for path in files:
        for pattern in BLOCKED_STAGE_PATTERNS:
            if pattern.search(path):
                blocked.append(path)
                break
    return CheckResult(
        "blocked local-only files",
        not blocked,
        blocked or ["No local-only files staged."],
    )


def check_secrets(files: list[str], *, staged: bool) -> CheckResult:
    findings: list[str] = []
    for path in files:
        if not is_text_path(path):
            continue
        text = read_staged(path) if staged else read_worktree(path)
        if text is None:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in SECRET_PATTERNS:
                for match in pattern.finditer(line):
                    value = normalize_match(match.group(0))
                    if value in ALLOWED_SECRET_VALUES:
                        continue
                    # Placeholder forms are allowed in docs/templates.
                    placeholder_tokens = ["change-me", "example", "password@host"]
                    if any(token in value.lower() for token in placeholder_tokens):
                        continue
                    findings.append(f"{path}:{line_number}: possible {label}")
    return CheckResult("secret scan", not findings, findings or ["No likely secrets found."])


def check_shell_syntax(files: list[str]) -> CheckResult:
    shell_files = [path for path in files if path.endswith(".sh")]
    details: list[str] = []
    ok = True
    for path in shell_files:
        proc = run(["bash", "-n", path])
        if proc.returncode != 0:
            ok = False
            details.append(f"{path}: {proc.stderr.strip() or proc.stdout.strip()}")
    return CheckResult("shell syntax", ok, details or ["No shell syntax errors."])


def check_yaml_parse(files: list[str]) -> CheckResult:
    yaml_files = [path for path in files if Path(path).suffix.lower() in {".yaml", ".yml"}]
    if not yaml_files:
        return CheckResult("YAML parse", True, ["No YAML files to parse."])
    script = """
from pathlib import Path
import sys
import yaml
ok = True
for raw in sys.argv[1:]:
    path = Path(raw)
    try:
        with path.open() as f:
            yaml.safe_load(f)
    except Exception as exc:
        ok = False
        print(f"{path}: {exc}")
if not ok:
    raise SystemExit(1)
""".strip()
    proc = run(["uv", "run", "python", "-c", script, *yaml_files])
    ok = proc.returncode == 0
    details = (proc.stdout + proc.stderr).strip().splitlines()
    return CheckResult("YAML parse", ok, details or [f"Parsed {len(yaml_files)} YAML file(s)."])


def check_ruff(files: list[str]) -> CheckResult:
    python_files = [path for path in files if path.endswith(".py")]
    if not python_files:
        return CheckResult("ruff", True, ["No Python files changed."])
    proc = run(["uv", "run", "ruff", "check", "."])
    ok = proc.returncode == 0
    details = (proc.stdout + proc.stderr).strip().splitlines()
    return CheckResult("ruff", ok, details or ["Ruff passed."])


def check_env_placeholder(files: list[str], *, staged: bool) -> CheckResult:
    if ".env" not in files:
        return CheckResult(".env placeholder", True, [".env not in scope."])
    text = read_staged(".env") if staged else read_worktree(".env")
    if text is None:
        return CheckResult(".env placeholder", True, [".env not readable; skipped."])
    required = ["LITELLM_MASTER_KEY=sk-change-me", "ICA_KEY=change-me", "LITELLM_PORT=4001"]
    missing = [item for item in required if item not in text]
    realish = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ICA_BASE=") and "example.com" not in stripped:
            realish.append("ICA_BASE is not placeholder")
        if stripped.startswith("DATABASE_URL=") and "user:password@host" not in stripped:
            realish.append("DATABASE_URL is not placeholder")
    ok = not missing and not realish
    details = missing + realish or [".env contains only expected placeholders."]
    return CheckResult(".env placeholder", ok, details)


def run_checks(files: list[str], *, staged: bool) -> list[CheckResult]:
    blocked_result = (
        check_blocked_staged(files)
        if staged
        else CheckResult("blocked local-only files", True, ["Skipped outside staged mode."])
    )
    return [
        blocked_result,
        check_env_placeholder(files, staged=staged),
        check_secrets(files, staged=staged),
        check_shell_syntax(files),
        check_yaml_parse(files),
        check_ruff(files),
    ]


def render(results: list[CheckResult], *, files: list[str], mode: str) -> str:
    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        "# LiteLLM Gateway Quality Report",
        "",
        f"- Generated: {now}",
        f"- Mode: `{mode}`",
        f"- Files checked: {len(files)}",
        "",
        "## Summary",
        "",
    ]
    for result in results:
        icon = "✅" if result.ok else "❌"
        lines.append(f"- {icon} {result.name}")
    lines.extend(["", "## Details", ""])
    for result in results:
        icon = "✅" if result.ok else "❌"
        lines.extend([f"### {icon} {result.name}", ""])
        for detail in result.details:
            lines.append(f"- {detail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fast local quality checks.")
    parser.add_argument("--staged", action="store_true", help="check staged files")
    parser.add_argument("--report", type=Path, help="write Markdown report")
    args = parser.parse_args()

    files = staged_files() if args.staged else tracked_files()
    mode = "staged" if args.staged else "full"
    results = run_checks(files, staged=args.staged)
    output = render(results, files=files, mode=mode)

    if args.report:
        report_path = args.report if args.report.is_absolute() else ROOT_DIR / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(output)
        print(f"Wrote report: {report_path.relative_to(ROOT_DIR)}")
    else:
        print(output)

    failed = [result.name for result in results if not result.ok]
    if failed:
        print("Failed checks: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
