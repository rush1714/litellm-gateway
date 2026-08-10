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
      if [[ -z "${!key+x}" ]]; then
        export "$key=$value"
      fi
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

truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_python() {
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "ERROR: python executable not found. Run: uv sync" >&2
    exit 1
  fi
}

prepare_config() {
  RUNTIME_CONFIG="$LOG_DIR/litellm-$LITELLM_PORT.runtime.yaml"
  resolve_python
  "$PYTHON_BIN" "$ROOT_DIR/deploy/scripts/prepare-litellm-config.py" "$LITELLM_CONFIG" "$RUNTIME_CONFIG"
  LITELLM_CONFIG="$RUNTIME_CONFIG"
}

ensure_prisma_engine_binary() {
  # prisma-client-py generated client.py may reference BINARY_PATHS pointing to
  # node_modules/prisma/query-engine-* while the actual binary lives under
  # node_modules/@prisma/engines/query-engine-*.  Auto-create a symlink if needed.
  resolve_python

  # Find client.py and extract the expected binary path without importing prisma
  local expected_path
  expected_path=$("$PYTHON_BIN" -c "
import re, platform
from pathlib import Path

# Locate the generated prisma/client.py
try:
    import prisma
    client_py = Path(prisma.__file__).parent / 'client.py'
except Exception:
    exit(0)

if not client_py.is_file():
    exit(0)

text = client_py.read_text()

# Parse BINARY_PATHS dict from the generated file
m = re.search(r\"BINARY_PATHS\s*=\s*model_parse\(BinaryPaths,\s*(\{.*?\})\)\", text, re.DOTALL)
if not m:
    exit(0)

import ast
paths_dict = ast.literal_eval(m.group(1))
qe = paths_dict.get('queryEngine') or {}
if not qe:
    exit(0)

uname = platform.uname()
key = f'{uname.system.lower()}-{uname.machine}'
print(qe.get(key) or next(iter(qe.values()), ''))
" 2>/dev/null) || return 0
  [[ -z "$expected_path" ]] && return 0

  # If the expected path already exists, nothing to do
  [[ -e "$expected_path" ]] && return 0

  local expected_dir
  expected_dir=$(dirname "$expected_path")
  local engine_name
  engine_name=$(basename "$expected_path")

  # Look for the binary under @prisma/engines/ (sibling of prisma/)
  local alt_path="$expected_dir/../@prisma/engines/$engine_name"

  if [[ -x "$alt_path" ]]; then
    echo "Auto-fix: creating symlink for Prisma query engine binary"
    echo "  $expected_path -> $alt_path"
    mkdir -p "$expected_dir"
    ln -sf "$alt_path" "$expected_path"
  fi
}

start_ica_proxy() {
  if ! truthy "$LITELLM_USE_ICA_PROXY"; then
    return
  fi

  if [[ -z "${ICA_BASE:-}" ]]; then
    echo "WARNING: ICA_BASE is not set; ICA proxy will not start"
    return
  fi

  if command -v lsof >/dev/null 2>&1; then
    local existing_pid
    existing_pid=$(lsof -tiTCP:"$ICA_PROXY_PORT" -sTCP:LISTEN || true)
    if [[ -n "$existing_pid" ]]; then
      echo "ICA proxy is already running on port $ICA_PROXY_PORT (PID $(tr '\n' ' ' <<< "$existing_pid"))"
      return
    fi
  fi

  resolve_python
  export ICA_PROXY_TARGET_BASE="$ICA_BASE"
  export ICA_PROXY_BASE
  nohup "$PYTHON_BIN" "$ROOT_DIR/deploy/scripts/ica-responses-proxy.py" \
    > "$ICA_PROXY_LOG_FILE" 2>&1 &
  echo $! > "$ICA_PROXY_PID_FILE"
  echo "ICA proxy started with PID $(cat "$ICA_PROXY_PID_FILE") on $ICA_PROXY_BASE"
}

load_env

LITELLM_CONFIG="${LITELLM_CONFIG:-$ROOT_DIR/config/litellm.yaml}"
LITELLM_ENABLE_DATABASE="${LITELLM_ENABLE_DATABASE:-true}"
LITELLM_HOST="${LITELLM_HOST:-0.0.0.0}"
LITELLM_PORT="${LITELLM_PORT:-4001}"
ICA_PROXY_HOST="${ICA_PROXY_HOST:-127.0.0.1}"
ICA_PROXY_PORT="${ICA_PROXY_PORT:-$((LITELLM_PORT + 100))}"
ICA_RESPONSES_API_VERSION="${ICA_RESPONSES_API_VERSION:-2025-03-01-preview}"
ICA_PROXY_BASE="${ICA_PROXY_BASE:-http://$ICA_PROXY_HOST:$ICA_PROXY_PORT}"
OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://127.0.0.1:11434}"
LITELLM_USE_ICA_PROXY="${LITELLM_USE_ICA_PROXY:-false}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/litellm-$LITELLM_PORT.log}"
PID_FILE="${PID_FILE:-$LOG_DIR/litellm-$LITELLM_PORT.pid}"
ICA_PROXY_LOG_FILE="${ICA_PROXY_LOG_FILE:-$LOG_DIR/ica-proxy-$ICA_PROXY_PORT.log}"
ICA_PROXY_PID_FILE="${ICA_PROXY_PID_FILE:-$LOG_DIR/ica-proxy-$ICA_PROXY_PORT.pid}"
export ICA_PROXY_BASE ICA_RESPONSES_API_VERSION OLLAMA_API_BASE

if [[ -d "$ROOT_DIR/.venv/bin" ]]; then
  export PATH="$ROOT_DIR/.venv/bin:$PATH"
fi

NO_PROXY_DEFAULT="localhost,127.0.0.1,::1"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}$NO_PROXY_DEFAULT"
export no_proxy="${no_proxy:+$no_proxy,}$NO_PROXY_DEFAULT"

if command -v lsof >/dev/null 2>&1; then
  PID=$(lsof -tiTCP:"$LITELLM_PORT" -sTCP:LISTEN || true)
  if [[ -n "$PID" ]]; then
    echo "LiteLLM is already running on port $LITELLM_PORT (PID $(tr '\n' ' ' <<< "$PID"))"
    exit 0
  fi
fi

if [[ -f "$PID_FILE" ]]; then
  rm -f "$PID_FILE"
fi

require_command
mkdir -p "$LOG_DIR"

if [[ ! -f "$LITELLM_CONFIG" ]]; then
  echo "ERROR: config file not found: $LITELLM_CONFIG" >&2
  exit 1
fi

required_vars=(LITELLM_MASTER_KEY ICA_BASE ICA_KEY)
if truthy "$LITELLM_ENABLE_DATABASE"; then
  required_vars+=(DATABASE_URL)
fi

for required_var in "${required_vars[@]}"; do
  if [[ -z "${!required_var:-}" ]]; then
    echo "WARNING: $required_var is not set"
  fi
done

start_ica_proxy
ensure_prisma_engine_binary
prepare_config

echo "================================="
echo " Starting LiteLLM Gateway"
echo " Root:   $ROOT_DIR"
echo " Config: $LITELLM_CONFIG"
echo " DB:     $LITELLM_ENABLE_DATABASE"
echo " Host:   $LITELLM_HOST"
echo " Port:   $LITELLM_PORT"
echo " Logs:   $LOG_FILE"
if truthy "$LITELLM_USE_ICA_PROXY"; then
  echo " ICA:    $ICA_PROXY_BASE -> $ICA_BASE"
fi
echo "================================="

nohup "$LITELLM_BIN" \
  --config "$LITELLM_CONFIG" \
  --host "$LITELLM_HOST" \
  --port "$LITELLM_PORT" \
  > "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "LiteLLM started with PID $(cat "$PID_FILE")"
