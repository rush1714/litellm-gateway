# LiteLLM Gateway

工程化的 LiteLLM Gateway 部署项目，用于通过 LiteLLM Proxy 暴露统一的模型别名，并将请求转发到 OpenAI-compatible 上游。

## 目录结构

```text
config/                 LiteLLM 运行配置
deploy/                 本机脚本与 Podman/Docker 部署文件
  scripts/              本机启动、停止、状态检查脚本
tools/                  运维/诊断工具
docs/sql/               LiteLLM PostgreSQL 用量查询 SQL
logs/                   本机运行日志和 PID 文件（日志不入库）
openspec/               OpenSpec 配置
```

关键文件：

- `config/litellm.yaml`：当前 LiteLLM Proxy 配置。
- `config/litellm.backup.yaml`：历史/备用配置。
- `.env`：环境变量模板；初始提交只包含占位值，部署前请填入真实值。
- `pyproject.toml` / `uv.lock`：Python 依赖声明与锁定文件。
- `deploy/Dockerfile` / `deploy/docker-compose.yml`：容器化部署。
- `Makefile`：常用命令入口。

## 环境变量

根目录 `.env` 是提交到仓库的环境变量模板；本机真实密钥建议放在不入库的 `.env.local`。

需要填写：

- `LITELLM_MASTER_KEY`：访问 LiteLLM Proxy 的 master key。
- `DATABASE_URL`：LiteLLM 持久化 PostgreSQL 连接串。
- `ICA_BASE`：OpenAI-compatible 上游 base URL。
- `ICA_KEY`：上游 API key。
- `LITELLM_HOST` / `LITELLM_PORT`：本机脚本使用的监听地址和端口，默认 `0.0.0.0:4001`。

## 本机开发与运行

本项目使用 uv 管理 Python 依赖。

```bash
uv sync
make start
make status
make stop
```

等价的直接命令：

```bash
./deploy/scripts/start.sh
./deploy/scripts/status.sh
./deploy/scripts/stop.sh
```

如果已在 `/Users/guobiao/bin` 配置本机快捷命令，可以直接运行：

```bash
litellm-start
litellm-status
litellm-stop
```

这些快捷命令是 wrapper，不修改仓库内原始 `deploy/scripts/*.sh`；默认使用：

```bash
ENV_FILE=/Users/guobiao/PRO/me/litellm-gateway/.env.local
```

因此本机真实环境变量可以放在 `.env.local`，仓库里的 `.env` 继续作为模板保留。需要临时切换环境文件时，也可以显式覆盖：

```bash
ENV_FILE=/path/to/other.env litellm-start
```

## Podman / Docker Compose 部署

```bash
# 编辑 .env
make docker-up
make docker-logs
make docker-down
```

检查 compose 配置：

```bash
make docker-config
```

`Makefile` 会优先使用 `podman compose`，如果没有 Podman 则回退到 `docker compose`。Compose 默认将宿主机 `${LITELLM_PORT:-4001}` 映射到容器内相同端口，并只读挂载 `./config/litellm.yaml`。本地 `DATABASE_URL` 如果通过 hosts 指向宿主机（例如 `litellm.top -> 127.0.0.1`），Compose 会把 `litellm.top` 映射到容器可访问的 host gateway。

也可以直接执行：

```bash
podman compose -f deploy/docker-compose.yml --env-file .env up -d --build
podman compose -f deploy/docker-compose.yml --env-file .env down
```

## 配置说明

`config/litellm.yaml` 通过 `os.environ/...` 读取敏感配置：

- `LITELLM_MASTER_KEY`
- `DATABASE_URL`
- `ICA_BASE`
- `ICA_KEY`

当前配置包含 Claude-compatible 别名、按用途优化的自定义模型别名和 router fallback。模型来源与路由策略见 `docs/model-routing.md`。修改模型、上游或 fallback 时，优先改 `config/litellm.yaml`，然后重启服务。

当前主要模型别名：

- `claude-sonnet-5`：默认 Claude Code-compatible 平衡编码/推理
- `claude-opus-4-8`：强多步骤/深度任务
- `claude-haiku-4-5`：快速轻量任务
- `gpt-best`：最高能力自定义别名
- `gpt-coding`：平衡编码与生产力
- `gpt-fast`：快速低成本
- `gpt-multimodal` / `gpt-4o`：多模态任务
- `gemini`：长上下文分析
- `gemini-fast`：快速 Gemini fallback
- `llama`：长引导任务与 OSS-style fallback
- `granite`：小模型稳定 fallback
- `gemma`：Gemma preview 试验别名

## 常用运维命令

```bash
make install       # uv sync
make start         # 启动本机 LiteLLM
make stop          # 停止本机 LiteLLM
make status        # 查看进程、health、models
make health        # 等待 health 通过
make prisma-check  # 检查 DATABASE_URL 对应 PostgreSQL 连通性
make lint          # ruff check
make format        # ruff format
```

## 数据库用量查询

LiteLLM 使用量统计 SQL 在：

```text
docs/sql/litellm-usage-queries.sql
```

这些查询针对 PostgreSQL 的 `"LiteLLM_SpendLogs"` 表。LiteLLM 的 camelCase 时间列需要在 PostgreSQL 中加双引号，例如 `"startTime"`、`"endTime"`。
