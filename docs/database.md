# LiteLLM PostgreSQL database

LiteLLM 持久化数据库由 `.env` 里的 `LITELLM_ENABLE_DATABASE` 控制：

```bash
LITELLM_ENABLE_DATABASE=true
DATABASE_URL=postgresql://litellm:litellm-change-me@localhost:5432/litellm?sslmode=disable
```

- `true`：启用 PostgreSQL，启动脚本会保留 `config/litellm.yaml` 里的 `database_url`。
- `false`：不启用 PostgreSQL，启动脚本会生成运行时配置并移除 `database_url`。

## 方式一：Docker / Podman Compose

`.env` 里保留默认数据库变量即可：

```bash
POSTGRES_HOST_PORT=5432
POSTGRES_DB=litellm
POSTGRES_USER=litellm
POSTGRES_PASSWORD=litellm-change-me
LITELLM_DOCKER_DATABASE_URL=postgresql://litellm:litellm-change-me@postgres:5432/litellm?sslmode=disable
```

启动数据库并等待 PostgreSQL ready：

```bash
make db-up
make prisma-check
```

进入数据库：

```bash
make db-shell
```

查看数据库日志：

```bash
make db-logs
```

停止数据库容器：

```bash
make db-down
```

启动 LiteLLM 和数据库：

```bash
make docker-up
make docker-logs
make docker-down
```

`make docker-up` 会读取 `COMPOSE_ENV_FILE`，默认是 `.env`。如果 `LITELLM_ENABLE_DATABASE=false`，它只启动 LiteLLM 服务；否则会先启动 PostgreSQL，再启动 LiteLLM。通过 Makefile 运行时，`COMPOSE_ENV_FILE=.env.local` 也会同步传给容器的 `env_file`。

使用本机私有配置时：

```bash
make docker-up COMPOSE_ENV_FILE=.env.local
make docker-logs COMPOSE_ENV_FILE=.env.local
make docker-down COMPOSE_ENV_FILE=.env.local
```

## 方式二：Homebrew PostgreSQL

安装 PostgreSQL：

```bash
brew install postgresql@16
brew services start postgresql@16
```

如果 `psql` 不在 PATH 中：

```bash
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
```

创建数据库和用户：

```bash
createuser litellm
createdb -O litellm litellm
psql postgres -c "ALTER USER litellm WITH PASSWORD 'litellm-change-me';"
```

`.env.local` 使用本机连接串：

```bash
LITELLM_ENABLE_DATABASE=true
DATABASE_URL=postgresql://litellm:litellm-change-me@localhost:5432/litellm?sslmode=disable
```

检查连通性：

```bash
ENV_FILE=.env.local make prisma-check
```

## 4001 端口验证

4000 端口如果被其他服务使用，不需要改动；本项目默认使用 4001：

```bash
ENV_FILE=.env.local LITELLM_PORT=4001 make start
ENV_FILE=.env.local LITELLM_PORT=4001 TIMEOUT_SECONDS=180 make health
ENV_FILE=.env.local LITELLM_PORT=4001 make status
ENV_FILE=.env.local LITELLM_PORT=4001 make stop
```

容器方式验证：

```bash
make docker-config COMPOSE_ENV_FILE=.env.local
make docker-up COMPOSE_ENV_FILE=.env.local
make docker-logs COMPOSE_ENV_FILE=.env.local
make docker-down COMPOSE_ENV_FILE=.env.local
```
