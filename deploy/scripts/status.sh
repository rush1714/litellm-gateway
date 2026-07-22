#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
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
LITELLM_HOST="${LITELLM_HOST:-localhost}"
PID_FILE="${PID_FILE:-$ROOT_DIR/logs/litellm.pid}"
BASE_URL="${LITELLM_BASE_URL:-http://$LITELLM_HOST:$LITELLM_PORT}"
NO_PROXY_DEFAULT="localhost,127.0.0.1,::1"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}$NO_PROXY_DEFAULT"
export no_proxy="${no_proxy:+$no_proxy,}$NO_PROXY_DEFAULT"

print_json() {
  if command -v jq >/dev/null 2>&1; then
    jq "$@"
  else
    cat
  fi
}

auth_args=()
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
  auth_args=(-H "Authorization: Bearer $LITELLM_MASTER_KEY")
else
  echo "WARNING: LITELLM_MASTER_KEY is not set; authenticated endpoints may fail"
fi

echo "=============================="
echo " LiteLLM Gateway Status"
echo "=============================="

echo ""
echo "[Process]"
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "running (PID $(cat "$PID_FILE"))"
elif command -v lsof >/dev/null 2>&1 && lsof -tiTCP:"$LITELLM_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "running on port $LITELLM_PORT (PID $(lsof -tiTCP:"$LITELLM_PORT" -sTCP:LISTEN | tr '\n' ' '))"
else
  echo "not running"
fi

echo ""
echo "[Health]"
if [[ ${#auth_args[@]} -gt 0 ]]; then
  health_response=$(curl -fsS "$BASE_URL/health" "${auth_args[@]}" || true)
else
  health_response=$(curl -fsS "$BASE_URL/health" || true)
fi
if [[ -n "$health_response" ]]; then
  printf '%s' "$health_response" | print_json .
else
  echo "health check failed: $BASE_URL/health"
fi

echo ""
echo "[Models]"
if [[ ${#auth_args[@]} -gt 0 ]]; then
  models_response=$(curl -fsS "$BASE_URL/v1/models" "${auth_args[@]}" || true)
else
  models_response=$(curl -fsS "$BASE_URL/v1/models" || true)
fi
if [[ -n "$models_response" ]]; then
  printf '%s' "$models_response" | print_json '.data[].id'
else
  echo "models check failed: $BASE_URL/v1/models"
fi

echo ""
