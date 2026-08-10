# LiteLLM Gateway

工程化的 LiteLLM Gateway 部署项目，用于通过 LiteLLM Proxy 暴露统一的模型别名，并将请求转发到 OpenAI-compatible 上游。

## 目录结构

```text
config/                 LiteLLM 运行配置
deploy/                 本机脚本与 Podman/Docker 部署文件
  scripts/              本机启动、停止、状态检查脚本
tools/                  运维/诊断工具
docs/database.md        PostgreSQL 安装、数据库开关和 4001 验证说明
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
- `LITELLM_ENABLE_DATABASE`：是否启用 LiteLLM PostgreSQL 持久化，默认 `true`。
- `DATABASE_URL`：本机运行时使用的 PostgreSQL 连接串；仅在 `LITELLM_ENABLE_DATABASE=true` 时需要。
- `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`：Compose PostgreSQL 服务的数据库、用户和密码。
- `LITELLM_DOCKER_DATABASE_URL`：容器内 LiteLLM 连接 Compose PostgreSQL 的连接串。
- `ICA_BASE`：OpenAI-compatible 上游 base URL。
- `ICA_KEY`：上游 API key。
- `LITELLM_HOST` / `LITELLM_PORT`：本机脚本使用的监听地址和端口，默认 `0.0.0.0:4001`。

数据库安装与初始化见 [`docs/database.md`](docs/database.md)。

## 本机开发与运行

本项目使用 uv 管理 Python 依赖，要求 Python `>=3.12,<3.13`。

安装 uv：

```bash
# macOS（推荐）
brew install uv

# 或使用官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装后确认 uv 可用：

```bash
uv --version
```

如果本机没有项目需要的 Python 版本，可以让 uv 安装 Python 3.12：

```bash
uv python install 3.12
uv sync --python 3.12
```

如果已经有可用的 Python 3.12，直接同步依赖即可：

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
make db-up
make prisma-check
make docker-up
make docker-logs
make docker-down
```

检查 compose 配置：

```bash
make docker-config
```

`Makefile` 会优先使用 `podman compose`，如果没有 Podman 则回退到 `docker compose`。Compose 默认将宿主机 `${LITELLM_PORT:-4001}` 映射到容器内相同端口，并只读挂载 `./config/litellm.yaml`。`make docker-up` 会根据 `LITELLM_ENABLE_DATABASE` 决定是否启动 Compose PostgreSQL；启用数据库时，容器内 LiteLLM 使用 `LITELLM_DOCKER_DATABASE_URL` 连接 `postgres` 服务。通过 Makefile 使用 `COMPOSE_ENV_FILE=.env.local` 时，容器也会加载同一个 env 文件。

也可以直接执行：

```bash
podman compose -f deploy/docker-compose.yml --env-file .env up -d postgres
podman compose -f deploy/docker-compose.yml --env-file .env up -d --build litellm
podman compose -f deploy/docker-compose.yml --env-file .env down
```

## 配置说明

`config/litellm.yaml` 通过 `os.environ/...` 读取敏感配置：

- `LITELLM_MASTER_KEY`
- `DATABASE_URL`（仅在 `LITELLM_ENABLE_DATABASE=true` 的运行时配置中保留）
- `ICA_BASE`
- `ICA_KEY`
- `LITELLM_USE_ICA_PROXY`（设为 `true` 时启动本地 ICA 代理）
- `ICA_PROXY_BASE`（例如 `http://127.0.0.1:4101`，供 YAML 中需要代理的模型显式引用）
- `ICA_RESPONSES_API_VERSION`（默认 `2025-03-01-preview`）
- `ICA_PROXY_HOST` / `ICA_PROXY_PORT`（默认 `127.0.0.1:${LITELLM_PORT + 100}`，例如 `4001 -> 4101`）
- `OLLAMA_API_BASE`（本机 Ollama 地址，默认 `http://127.0.0.1:11434`）
- `OLLAMA_DOCKER_API_BASE`（容器访问宿主机 Ollama 的地址，默认 `http://host.docker.internal:11434`）

启动脚本在 `LITELLM_USE_ICA_PROXY=true` 时启动本地 ICA 代理。是否走代理由 YAML 显式决定：只有 `api_base: "os.environ/ICA_PROXY_BASE"` 的模型会走代理，其他模型继续使用 `api_base: "os.environ/ICA_BASE"`。代理只在 `/responses` 请求缺少 `api-version` 时追加 `ICA_RESPONSES_API_VERSION`，用于兼容 Claude Code 的 `/v1/messages` 到 OpenAI Responses API 转换；`/chat/completions` 会原样转发。

本地 Ollama 模型使用 `local-*` 别名，需要先启动 Ollama 并下载对应模型：

```bash
ollama serve
ollama pull qwen3:8b
ollama pull qwen3:14b
```

`local-translator` 用于中英技术文档翻译；`local-qwen-14b` 和 `local-qwen3-14b` 适合高质量翻译与通用文本任务；`local-qwen-fast`、`local-qwen3-fast` 和 `local-qwen3-4b` 适合短文本或轻量任务；`local-qwen-coder`、`local-qwen-coder-base` 和 `local-deepseek-coder-6-7b` 用于本地代码任务；`local-deepseek-r1-8b`、`local-phi4`、`local-mistral-7b` 和 `local-llama-8b` 用于本地推理或通用对话；`local-gemma3-12b`、`local-gemma4-12b` 和 `local-minicpm-v` 用于图像理解等多模态任务；`local-nomic-embed` 只用于 `/v1/embeddings`。

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
- `gemini-best`：高能力 Gemini 通用与编码 fallback
- `llama`：长引导任务与 OSS-style fallback
- `IBM-Consulting-Banking-BIAN-llama3.1-8b`：银行 BIAN 领域任务
- `IBM-Consulting-TMF-llama3.1-8b`：TM Forum 领域任务
- `granite`：小模型稳定 fallback
- `gemma`：Gemma preview 试验别名
- `local-translator`：本地中英技术翻译
- `local-qwen-14b` / `local-qwen3-14b`：本地高质量翻译与通用任务
- `local-qwen-fast` / `local-qwen3-fast` / `local-qwen3-4b`：本地快速或轻量文本任务
- `local-qwen-coder` / `local-qwen-coder-base` / `local-deepseek-coder-6-7b`：本地代码任务
- `local-deepseek-r1-8b` / `local-phi4` / `local-mistral-7b` / `local-llama-8b`：本地推理或通用对话
- `local-gemma3-12b` / `local-gemma4-12b` / `local-minicpm-v`：本地图像理解与多模态任务
- `local-nomic-embed`：本地 embedding

## 常用运维命令

```bash
make install       # uv sync
make start         # 启动本机 LiteLLM
make stop          # 停止本机 LiteLLM
make status        # 查看进程、health、models
make health        # 等待 health 通过
make db-up         # 启动 Compose PostgreSQL
make db-shell      # 进入 Compose PostgreSQL psql
make prisma-check  # 数据库启用时检查 DATABASE_URL 连通性
make docker-up     # 按数据库开关启动 Compose 服务
make lint          # ruff check
make format        # ruff format
```

## 数据库用量查询

LiteLLM 使用量统计 SQL 在：

```text
docs/sql/litellm-usage-queries.sql
```

这些查询针对 PostgreSQL 的 `"LiteLLM_SpendLogs"` 表。LiteLLM 的 camelCase 时间列需要在 PostgreSQL 中加双引号，例如 `"startTime"`、`"endTime"`。
