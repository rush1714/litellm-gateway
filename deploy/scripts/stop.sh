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
      if [[ -z "${!key+x}" ]]; then
        export "$key=$value"
      fi
    fi
  done < "$ENV_FILE"
}

load_env

LITELLM_PORT="${LITELLM_PORT:-4001}"
ICA_PROXY_PORT="${ICA_PROXY_PORT:-$((LITELLM_PORT + 100))}"
PID_FILE="${PID_FILE:-$ROOT_DIR/logs/litellm-$LITELLM_PORT.pid}"
ICA_PROXY_PID_FILE="${ICA_PROXY_PID_FILE:-$ROOT_DIR/logs/ica-proxy-$ICA_PROXY_PORT.pid}"
NO_PROXY_DEFAULT="localhost,127.0.0.1,::1"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}$NO_PROXY_DEFAULT"
export no_proxy="${no_proxy:+$no_proxy,}$NO_PROXY_DEFAULT"

stop_pid_on_port() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return 1
  fi

  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "LiteLLM stopped on port $LITELLM_PORT (PID $pid)"
    return 0
  fi

  return 1
}

stopped=false

if command -v lsof >/dev/null 2>&1; then
  PID=$(lsof -tiTCP:"$LITELLM_PORT" -sTCP:LISTEN || true)
  if [[ -n "$PID" ]]; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      stop_pid_on_port "$pid"
      stopped=true
    done <<< "$PID"
    rm -f "$PID_FILE"
  fi

  PROXY_PID=$(lsof -tiTCP:"$ICA_PROXY_PORT" -sTCP:LISTEN || true)
  if [[ -n "$PROXY_PID" ]]; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        echo "ICA proxy stopped on port $ICA_PROXY_PORT (PID $pid)"
        stopped=true
      fi
    done <<< "$PROXY_PID"
    rm -f "$ICA_PROXY_PID_FILE"
  fi
else
  echo "WARNING: lsof not found; cannot locate listeners" >&2
fi

if [[ -f "$PID_FILE" ]]; then
  rm -f "$PID_FILE"
fi
if [[ -f "$ICA_PROXY_PID_FILE" ]]; then
  rm -f "$ICA_PROXY_PID_FILE"
fi

if [[ "$stopped" == "false" ]]; then
  echo "LiteLLM is not running on port $LITELLM_PORT"
fi
