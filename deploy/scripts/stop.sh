#!/usr/bin/env bash
set -euo pipefail

SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  SOURCE_DIR=$(cd -P "$(dirname "$SOURCE")" && pwd)
  SOURCE=$(readlink "$SOURCE")
  [[ "$SOURCE" != /* ]] && SOURCE="$SOURCE_DIR/$SOURCE"
done
SCRIPT_DIR=$(cd -P "$(dirname "$SOURCE")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

load_env() {
  [[ -f "$ENV_FILE" ]] || return

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
}

load_env

LITELLM_PORT="${LITELLM_PORT:-4001}"
PID_FILE="${PID_FILE:-$ROOT_DIR/logs/litellm.pid}"
NO_PROXY_DEFAULT="localhost,127.0.0.1,::1"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}$NO_PROXY_DEFAULT"
export no_proxy="${no_proxy:+$no_proxy,}$NO_PROXY_DEFAULT"

stop_pid() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return 1
  fi

  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "LiteLLM stopped (PID $pid)"
    return 0
  fi

  return 1
}

if [[ -f "$PID_FILE" ]]; then
  if stop_pid "$(cat "$PID_FILE")"; then
    rm -f "$PID_FILE"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if command -v lsof >/dev/null 2>&1; then
  PID=$(lsof -tiTCP:"$LITELLM_PORT" -sTCP:LISTEN || true)
  if [[ -n "$PID" ]]; then
    stop_pid "$PID"
    exit 0
  fi
fi

echo "LiteLLM is not running"
