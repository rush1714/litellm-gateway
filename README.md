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

先编辑根目录 `.env`，把占位值替换为真实配置。

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

当前配置包含 Claude-compatible 别名、现有自定义模型别名和 router fallback。修改模型、上游或 fallback 时，优先改 `config/litellm.yaml`，然后重启服务。

当前主要模型别名：

- `claude-sonnet-5`
- `claude-sonnet-4-5`
- `claude-opus-4-8`
- `claude-opus-4-5`
- `claude-haiku-4-5`
- `gpt-best`
- `gpt-coding`
- `gpt-fast`
- `gemini`
- `llama`
- `granite`

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
