# OpenSpec 命令行跟练脚本

这份文档用于边学边操作。所有 `openspec ...` 都在终端输入；所有 `/opsx:...` 都在 Claude Code 对话框输入。

## 练习目标

通过一个安全的小练习完整掌握：

1. 终端确认 OpenSpec 安装与项目状态。
2. 在 AI Chat 中创建 change。
3. 用终端查看、校验 change。
4. 审查 artifacts。
5. 用 AI Chat 应用任务。
6. 用终端再次验证。
7. 用 AI Chat 归档。

建议练习 change 名称：

```text
practice-openspec-doc-note
```

建议练习内容：

```text
在 docs/workflow/ 中补充一小段 OpenSpec 使用入口说明，只改文档，不改运行时配置。
```

## 第 0 步：确认你在哪输入

终端输入：

```bash
pwd
```

你应该在本仓库根目录：

```text
/Users/guobiao/PRO/me/litellm-gateway
```

## 第 1 步：确认 OpenSpec CLI 可用

终端输入：

```bash
openspec --version
```

如果提示 `command not found`，先安装：

```bash
npm install -g @fission-ai/openspec@latest
```

再重试：

```bash
openspec --version
```

## 第 2 步：查看项目 OpenSpec 配置

终端输入：

```bash
openspec config list
```

然后查看仓库配置文件：

```bash
cat openspec/config.yaml
```

本仓库应能看到 `schema: spec-driven`。

## 第 3 步：查看当前 changes 和 specs

终端输入：

```bash
openspec list
```

再输入：

```bash
openspec list --specs
```

如果显示没有 active changes 或 specs 很少，这是正常的；OpenSpec 可以从 delta-first 开始逐步积累。

## 第 4 步：先让 AI 探索，不创建文件

在 Claude Code 对话框输入：

```text
/opsx:explore 我想做一个安全的 OpenSpec 练习，只更新 docs/workflow/ 下的一小段说明，不改运行时配置。请帮我判断最小合适范围。
```

你要重点看 AI 是否做到：

- 范围足够小。
- 不碰 `config/litellm.yaml`、部署脚本或密钥。
- 明确这是文档练习。

## 第 5 步：创建 change 和 artifacts

在 Claude Code 对话框输入：

```text
/opsx:propose practice-openspec-doc-note
```

如果 AI 需要你补充 intent，可以告诉它：

```text
目标是在 docs/workflow/ 中补充 OpenSpec 入门入口说明，帮助以后知道终端命令和 /opsx 命令分别在哪里输入。只改文档，不改运行时配置。
```

## 第 6 步：用终端查看 change

终端输入：

```bash
openspec list
```

然后输入：

```bash
openspec show practice-openspec-doc-note
```

如果需要机器可读状态：

```bash
openspec status --change practice-openspec-doc-note --json
```

## 第 7 步：校验 change

终端输入：

```bash
openspec validate practice-openspec-doc-note
```

如果有错误，不要急着 apply；先让 AI 修 artifacts：

```text
/opsx:update practice-openspec-doc-note 修复 openspec validate 报告的问题，并保持只改文档的范围。
```

然后再次运行：

```bash
openspec validate practice-openspec-doc-note
```

## 第 8 步：人工审查 artifacts

终端输入：

```bash
find openspec/changes/practice-openspec-doc-note -maxdepth 3 -type f | sort
```

按顺序读这些文件：

```bash
cat openspec/changes/practice-openspec-doc-note/proposal.md
cat openspec/changes/practice-openspec-doc-note/specs/*/spec.md
cat openspec/changes/practice-openspec-doc-note/design.md
cat openspec/changes/practice-openspec-doc-note/tasks.md
```

审查重点：

- `proposal.md` 是否明确“只改文档”。
- delta spec 是否描述行为，而不是代码实现。
- `design.md` 是否没有过度设计。
- `tasks.md` 是否能清楚完成。

## 第 9 步：让 AI 执行实现

在 Claude Code 对话框输入：

```text
/opsx:apply practice-openspec-doc-note
```

如果 AI 没识别 change，可以补充：

```text
请应用 openspec/changes/practice-openspec-doc-note/tasks.md，只完成文档更新，不修改运行时配置。
```

## 第 10 步：终端验证结果

终端输入：

```bash
git status --short
```

然后输入：

```bash
openspec validate practice-openspec-doc-note
```

如果项目有文档或格式检查，也可以运行仓库常规检查：

```bash
make lint
```

## 第 11 步：归档

确认代码和 artifacts 都没问题后，在 Claude Code 对话框输入：

```text
/opsx:archive practice-openspec-doc-note
```

归档后终端检查：

```bash
openspec list
openspec list --specs
find openspec/changes/archive -maxdepth 2 -type d | sort
```

## 第 12 步：复盘你掌握了什么

你应该能说清楚：

- `openspec ...` 和 `/opsx:...` 的输入位置不同。
- `specs/` 是当前事实来源，`changes/` 是待完成变更。
- delta spec 用 `ADDED`、`MODIFIED`、`REMOVED` 描述变化。
- archive 会把 delta spec 合并进主 spec，并归档 change。
- OpenSpec 不替你提交 git。

掌握后，再把同样流程用于真实改动。
