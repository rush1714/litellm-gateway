# Claude Code integrations

This project keeps Claude Code integrations conservative by default: use official plugins and local MCP servers that are broadly useful, and document third-party security tools before enabling them.

## Installed / recommended for this project

### Official `code-review` plugin

Purpose: invoke Claude Code's official code review skill for higher-confidence review before commits or pull requests.

Install/enable project scope:

```bash
claude plugins install code-review --scope project
claude plugins enable code-review --scope project
```

Use when:

- reviewing a non-trivial change set
- preparing a pull request
- checking deployment/config changes before push

### Official `skill-creator` plugin

Purpose: create or improve project-specific Claude Code skills if workflow repetition becomes high.

Install/enable project scope:

```bash
claude plugins install skill-creator --scope project
claude plugins enable skill-creator --scope project
```

Use when:

- a repeated repo workflow deserves a dedicated skill
- existing skills need evaluation or cleanup

### Context7 MCP

Purpose: retrieve current library/framework documentation from Context7 when implementing or reviewing code.

Local-scope install:

```bash
claude mcp add context7 --scope local -- npx -y @upstash/context7-mcp@latest
```

Use when:

- dependency behavior is version-sensitive
- writing code against APIs whose docs may have changed
- checking LiteLLM/Prisma/Podman examples against current docs

## Third-party options to consider later

These are not enabled by default because they may require accounts, extra binaries, network access, or introduce significant behavior changes.

| Plugin/tool | When to consider |
| --- | --- |
| `security-guidance` | Security review guidance during agent edits and commit review. |
| `claude-security` | Deep agentic vulnerability scanning inside Claude Code. |
| `semgrep` | Rule-based SAST for code/security patterns. |
| `sonarqube` | Organization-wide quality/security gates. |
| `aikido` | SAST, secrets, IaC scanning with Aikido. |
| `superpowers` | Stronger workflow discipline (brainstorming, TDD, debugging, review). |
| `pr-review-toolkit` | More specialized PR review workflows. |

## `cc-safe` note

`cc-safe` is installed locally, but currently fails under the detected Node runtime:

```text
node:fs/promises does not provide an export named 'glob'
```

That means this project should not enforce `cc-safe` in Git hooks until Node is upgraded to a version that supports `fs.promises.glob`, or `cc-safe` is replaced with a compatible scanner.

## Marketplace management

The official marketplace is configured by default. The third-party Superpowers marketplace is also present locally.

Useful commands:

```bash
claude plugins marketplace list
claude plugins marketplace update
claude plugins list --available --json
```

If adding a new third-party plugin, first document:

1. why it is needed,
2. whether it runs external services,
3. what permissions or secrets it needs,
4. how to disable/remove it,
5. whether it should be user, project, or local scope.
