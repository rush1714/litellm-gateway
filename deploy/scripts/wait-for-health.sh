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
LITELLM_HOST="${LITELLM_HOST:-localhost}"
BASE_URL="${LITELLM_BASE_URL:-http://$LITELLM_HOST:$LITELLM_PORT}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-60}"
NO_PROXY_DEFAULT="localhost,127.0.0.1,::1"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}$NO_PROXY_DEFAULT"
export no_proxy="${no_proxy:+$no_proxy,}$NO_PROXY_DEFAULT"

AUTH_ARGS=()
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
  AUTH_ARGS=(-H "Authorization: Bearer $LITELLM_MASTER_KEY")
fi

end=$((SECONDS + TIMEOUT_SECONDS))
while (( SECONDS < end )); do
  if [[ ${#AUTH_ARGS[@]} -gt 0 ]]; then
    health_status=$(curl -fsS "$BASE_URL/health" "${AUTH_ARGS[@]}" >/dev/null 2>&1; echo $?)
  else
    health_status=$(curl -fsS "$BASE_URL/health" >/dev/null 2>&1; echo $?)
  fi

  if [[ "$health_status" == "0" ]]; then
    echo "LiteLLM is healthy at $BASE_URL"
    exit 0
  fi
  sleep 2
done

echo "Timed out waiting for LiteLLM health at $BASE_URL" >&2
exit 1
