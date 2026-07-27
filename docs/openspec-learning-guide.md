# OpenSpec 学习与命令行实操指南

> 基于 Fission-AI/OpenSpec 官方文档 `docs/getting-started.md` 及同目录文档整理，适用于本仓库当前的 `openspec/config.yaml`（`schema: spec-driven`）和 Claude Code 中的 `/opsx:*` 工作流。

## 1. 先建立正确心智模型

OpenSpec 的目标不是替你写代码，而是让你和 AI 在写代码前先对齐“要做什么、为什么做、怎样才算完成”。

最重要的区分：

- `openspec ...` 是终端命令，在 shell 里输入。
- `/opsx:...` 是 AI Chat 命令，在 Claude Code 对话框里输入。
- 不存在单独的 OpenSpec interactive mode；你在终端跑 CLI，在聊天框跑 slash command。
- OpenSpec 不操作 git；是否提交、推送、建 PR 仍由你和仓库流程控制。

官方默认推荐的核心路径是：

```text
/opsx:explore -> /opsx:propose -> /opsx:apply -> /opsx:sync -> /opsx:archive
```

含义：

1. `/opsx:explore`：可选，先把模糊想法想清楚，不生成变更目录。
2. `/opsx:propose <change-name>`：生成一个变更及其规划产物。
3. `/opsx:apply`：AI 按任务实现代码，并在必要时更新产物。
4. `/opsx:sync`：把 delta spec 合并到主 spec，通常可以由 archive 串起来。
5. `/opsx:archive`：完成变更，归档 change，并更新系统行为文档。

扩展工作流是：

```text
/opsx:new -> /opsx:ff 或 /opsx:continue -> /opsx:apply -> /opsx:verify -> /opsx:archive
```

扩展命令适合需要分步控制产物的场景，但本仓库当前优先使用核心路径。

## 2. OpenSpec 会创建什么

运行 `openspec init` 后，一个项目通常会有：

```text
openspec/
├── specs/                 # 当前系统行为的事实来源
│   └── <domain>/
│       └── spec.md
├── changes/               # 尚未归档的计划变更
│   └── <change-name>/
│       ├── proposal.md
│       ├── design.md
│       ├── tasks.md
│       └── specs/         # delta specs，只描述本次变化
│           └── <domain>/
│               └── spec.md
└── config.yaml            # 项目级配置
```

本仓库已经有 `openspec/config.yaml`，并使用：

```yaml
schema: spec-driven
```

因此做计划型改动时，不要手写猜测路径；优先通过 OpenSpec CLI 或 `/opsx:*` 命令让工具报告 `planningHome`、`changeRoot`、`artifactPaths`、`contextFiles`。

## 3. 四类核心产物

每个 change 目录通常包含：

| 产物 | 作用 | 你审查时重点看什么 |
| --- | --- | --- |
| `proposal.md` | 为什么做、做什么、范围是什么 | 问题是否正确、范围是否过大、是否有不该做的内容 |
| `specs/` | delta spec，定义完成标准 | 行为是否可验证、场景是否覆盖边界、ADDED/MODIFIED/REMOVED 是否用对 |
| `design.md` | 技术方案和架构决策 | 方案是否符合现有代码、是否过度设计、风险是否清楚 |
| `tasks.md` | 实施清单 | 任务是否能按顺序执行、是否遗漏测试/验证、是否包含无关工作 |

官方强调产物不是一次性写死的。实现过程中发现信息变化，可以回头更新 proposal、specs、design 或 tasks。

## 4. Delta spec 是关键

OpenSpec 不是要求你重写完整需求文档，而是写“相对当前系统行为，本次改了什么”。

基本格式：

```markdown
# Delta for Auth

## ADDED Requirements

### Requirement: Two-Factor Authentication
The system MUST require a second factor during login.

#### Scenario: OTP required
- GIVEN a user with 2FA enabled
- WHEN the user submits valid credentials
- THEN an OTP challenge is presented

## MODIFIED Requirements

### Requirement: Session Timeout
The system SHALL expire sessions after 30 minutes of inactivity.
(Previously: 60 minutes)

#### Scenario: Idle timeout
- GIVEN an authenticated session
- WHEN 30 minutes pass without activity
- THEN the session is invalidated

## REMOVED Requirements

### Requirement: Remember Me
(Deprecated in favor of 2FA)
```

归档时：

- `ADDED` 会追加进主 spec。
- `MODIFIED` 会替换主 spec 中已有 requirement。
- `REMOVED` 会从主 spec 删除对应 requirement。
- change 目录会移动到 `openspec/changes/archive/`，保留审计历史。

写 spec 的原则：

- spec 描述行为，不描述代码实现。
- requirement 应该是用户或系统可观察的能力。
- scenario 用 GIVEN / WHEN / THEN 表达，尽量可测试。
- 不要把内部函数名、文件路径、重构步骤塞进 spec；这些属于 design 或 tasks。

## 5. 官方 getting-started 的完整步骤

官方首页的 “Your First Five Minutes” 是：

```text
TERMINAL   $ npm install -g @fission-ai/openspec@latest
TERMINAL   $ cd your-project && openspec init
AI CHAT      /opsx:explore                    (optional: think it through first)
AI CHAT      /opsx:propose add-dark-mode      (AI drafts the plan; you review it)
AI CHAT      /opsx:apply                      (AI builds it)
AI CHAT      /opsx:archive                    (specs updated, change filed away)
```

在本仓库中，前两步大概率已经做过，因为已经存在 `openspec/` 和 `/opsx` 相关 Claude skill/command。你的学习重点应该放在：

1. 终端确认 CLI 状态。
2. 在 AI Chat 中创建一个小的练习 change。
3. 用终端查看、校验 change。
4. 审查产物。
5. 决定是否 apply。
6. 完成后 archive。

## 6. 常用终端命令

安装与升级：

```bash
npm install -g @fission-ai/openspec@latest
openspec --version
openspec update
```

初始化与更新 AI 工具配置：

```bash
openspec init
openspec init --tools claude,cursor
openspec init --tools all
openspec update
```

浏览：

```bash
openspec list
openspec list --specs
openspec show <change-name>
openspec show <spec-name>
openspec view
```

校验：

```bash
openspec validate <change-name>
openspec validate --all
openspec validate --all --json
```

生命周期：

```bash
openspec new change <change-name>
openspec status --change <change-name> --json
openspec instructions <artifact-id> --change <change-name> --json
openspec instructions apply --change <change-name> --json
openspec archive <change-name>
openspec archive <change-name> --yes
```

配置与 schema：

```bash
openspec config list
openspec config get profile
openspec config profile
openspec schemas
openspec templates
openspec schema fork spec-driven my-schema
openspec schema validate
openspec schema which spec-driven
```

排错：

```bash
openspec doctor
openspec context --json
```

## 7. Claude Code 中的 `/opsx:*` 命令

在 Claude Code 里输入这些命令，不要在 shell 里输入：

| 命令 | 用途 | 何时使用 |
| --- | --- | --- |
| `/opsx:explore` | 先探索想法，不创建 change | 需求不清、需要比较方案、怕 AI 做错方向 |
| `/opsx:propose <name>` | 创建 change 并生成规划产物 | 默认最快路径 |
| `/opsx:apply` | 按 tasks 实现 | 你已经审查并接受计划 |
| `/opsx:update` | 修改已有 change 的产物 | 范围、设计或需求变了 |
| `/opsx:sync` | 同步 delta specs 到主 specs | 需要显式合并 spec 时 |
| `/opsx:archive` | 完成并归档 change | 代码完成、验证通过、spec 已更新 |
| `/opsx:new` | 创建 change scaffold | 扩展工作流，想手动控制每一步 |
| `/opsx:continue` | 生成下一个产物 | 扩展工作流，逐步推进 |
| `/opsx:ff` | 一次生成后续产物 | 扩展工作流，需求清晰 |
| `/opsx:verify` | 对照产物验证实现 | 扩展工作流，归档前检查 |
| `/opsx:onboard` | 端到端引导 | 想让 OpenSpec 带你走完整流程 |

## 8. 审查一个 change 的顺序

官方建议先审查计划，再实现。顺序是：

```text
proposal.md -> specs/**/*.md -> design.md -> tasks.md
```

审查问题：

- Proposal：这是正确的问题吗？范围是否过大？有没有隐藏假设？
- Delta specs：完成标准是否明确？场景是否能测试？有没有遗漏失败路径？
- Design：技术方案是否符合现有项目？有没有不必要的抽象？
- Tasks：任务是否可执行？是否包含验证？顺序是否合理？

归档前再审查一次：

- 所有 tasks 是否真的完成。
- 实现是否满足每个 requirement/scenario。
- 代码、spec、design 是否互相一致。
- 是否运行了必要测试或手动验证。

## 9. 什么时候 update，什么时候新开 change

继续更新同一个 change 的条件：

- 仍然是同一件事，只是更清楚了。
- 新内容和原 scope 高度重叠。
- 不更新就无法说原 change 已完成。
- change 的故事仍然连贯。

新开 change 的条件：

- 新内容可以独立完成。
- scope overlap 很低。
- 把它塞进当前 change 会让审查更混乱。
- 原 change 已经可以定义为完成。

一句话：update 保存上下文，new change 提供清晰边界。

## 10. 在已有项目中怎么开始

官方对 brownfield 项目的建议是 delta-first：不要试图先补全整个系统的完整 specs，再开始工作。更现实的做法是：

1. 对即将修改的领域建立最小上下文。
2. 只为本次改动写 delta spec。
3. 归档后让主 spec 慢慢积累成事实来源。

适合大项目的组织方式：

```text
openspec/specs/auth/spec.md
openspec/specs/billing/spec.md
openspec/specs/litellm-routing/spec.md
openspec/specs/deployment/spec.md
```

在本仓库中，可能的领域包括 LiteLLM 配置、部署脚本、Docker/Compose、Prisma 检查、质量工具、模型路由文档等。

## 11. 常见坑

- 把 `/opsx:propose` 输入到终端：错，它要输入到 Claude Code chat。
- 把 `openspec validate` 输入到 AI chat：错，它是终端命令。
- 没有先 explore 就让 AI 做模糊需求：容易得到自信但错误的实现。
- spec 写代码细节：spec 应写行为，技术细节放 design。
- change 太大：OpenSpec 适合聚焦变更；大范围工作拆多个 change。
- archive 前没验证：归档会把 delta 合进主 spec，应该先确保实现和 spec 对齐。
- 手改代码后忘了同步产物：用 `/opsx:update` 或手动更新 artifacts，再 validate。
- 认为 OpenSpec 会自动提交 git：不会，git 流程仍然单独执行。

## 12. 给本仓库的建议练习

为了学习 OpenSpec，不建议第一次就改 LiteLLM 路由或部署脚本。先做一个小而安全的文档型 change，例如：

```text
practice-openspec-doc-note
```

目标可以是：在 `docs/workflow/` 下增加一小段 OpenSpec 使用说明，或更新已有 workflow 文档中的 OpenSpec 入口说明。这样你能完整练习 propose、validate、apply、archive，而不会影响运行时配置。

完成练习后，再把同样流程用于真实改动，例如：

- 调整模型路由别名。
- 改进 `deploy/scripts/status.sh` 输出。
- 增强 `tools/check_prisma.py` 的诊断信息。
- 更新 Docker Compose 部署说明。

## 13. 下一步学习顺序

建议按这个顺序掌握：

1. `getting-started.md`：跑通五分钟流程。
2. `how-commands-work.md`：彻底分清终端和 AI Chat。
3. `concepts.md` / `overview.md`：理解 specs、changes、artifacts、delta specs。
4. `writing-specs.md`：学会写好 requirement 和 scenario。
5. `reviewing-changes.md`：学会审查 AI 生成的计划。
6. `editing-changes.md`：学会变更中途调整。
7. `workflows.md` / `commands.md`：理解核心路径和扩展路径。
8. `existing-projects.md`：把 OpenSpec 用在已有项目。
9. `customization.md` / `multi-language.md`：需要团队定制或中文输出时再看。
10. `troubleshooting.md`：命令找不到、schema 不对、artifact 不完整时查。
