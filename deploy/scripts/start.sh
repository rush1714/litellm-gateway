#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

load_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "WARNING: $ENV_FILE not found. Create .env from the committed placeholder and fill in values."
    return
  fi

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#${line%%[![:space:]]*}}"
    line="${line%${line##*[![:space:]]}}"
    [[ -z "$line" || "${line:0:1}" == "#" ]] && continue

    if [[ "$line" == export[[:space:]]* ]]; then
      line="${line#export}"
      line="${line#${line%%[![:space:]]*}}"
    fi

    [[ "$line" == *=* ]] || continue
    local key="${line%%=*}"
    local value="${line#*=}"
    key="${key%${key##*[![:space:]]}}"
    value="${value#${value%%[![:space:]]*}}"
    value="${value%${value##*[![:space:]]}}"

    if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      if [[ ${#value} -ge 2 ]]; then
        local first="${value:0:1}"
        local last="${value: -1}"
        if [[ ( "$first" == '"' && "$last" == '"' ) || ( "$first" == "'" && "$last" == "'" ) ]]; then
          value="${value:1:${#value}-2}"
        fi
      fi
      export "$key=$value"
    fi
  done < "$ENV_FILE"

  echo "Loaded environment from $ENV_FILE"
}

require_command() {
  if [[ -x "$ROOT_DIR/.venv/bin/litellm" ]]; then
    LITELLM_BIN="$ROOT_DIR/.venv/bin/litellm"
    return
  fi

  if command -v litellm >/dev/null 2>&1; then
    LITELLM_BIN="$(command -v litellm)"
    return
  fi

  echo "ERROR: litellm executable not found. Run: uv sync" >&2
  exit 1
}

load_env

LITELLM_CONFIG="${LITELLM_CONFIG:-$ROOT_DIR/config/litellm.yaml}"
LITELLM_HOST="${LITELLM_HOST:-0.0.0.0}"
LITELLM_PORT="${LITELLM_PORT:-4001}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/litellm.log}"
PID_FILE="${PID_FILE:-$LOG_DIR/litellm.pid}"

if [[ -d "$ROOT_DIR/.venv/bin" ]]; then
  export PATH="$ROOT_DIR/.venv/bin:$PATH"
fi

NO_PROXY_DEFAULT="localhost,127.0.0.1,::1"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}$NO_PROXY_DEFAULT"
export no_proxy="${no_proxy:+$no_proxy,}$NO_PROXY_DEFAULT"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "LiteLLM is already running with PID $(cat "$PID_FILE")"
  exit 0
fi

require_command
mkdir -p "$LOG_DIR"

if [[ ! -f "$LITELLM_CONFIG" ]]; then
  echo "ERROR: config file not found: $LITELLM_CONFIG" >&2
  exit 1
fi

for required_var in LITELLM_MASTER_KEY DATABASE_URL ICA_BASE ICA_KEY; do
  if [[ -z "${!required_var:-}" ]]; then
    echo "WARNING: $required_var is not set"
  fi
done

echo "================================="
echo " Starting LiteLLM Gateway"
echo " Root:   $ROOT_DIR"
echo " Config: $LITELLM_CONFIG"
echo " Host:   $LITELLM_HOST"
echo " Port:   $LITELLM_PORT"
echo " Logs:   $LOG_FILE"
echo "================================="

nohup "$LITELLM_BIN" \
  --config "$LITELLM_CONFIG" \
  --host "$LITELLM_HOST" \
  --port "$LITELLM_PORT" \
  > "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "LiteLLM started with PID $(cat "$PID_FILE")"
