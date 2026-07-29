#!/usr/bin/env sh
set -eu

LITELLM_CONFIG="${LITELLM_CONFIG:-/app/config/litellm.yaml}"
LITELLM_RUNTIME_CONFIG="${LITELLM_RUNTIME_CONFIG:-/tmp/litellm-runtime.yaml}"
LITELLM_HOST="${LITELLM_HOST:-0.0.0.0}"
LITELLM_PORT="${LITELLM_PORT:-4001}"
LITELLM_USE_ICA_PROXY="${LITELLM_USE_ICA_PROXY:-false}"
ICA_PROXY_HOST="${ICA_PROXY_HOST:-127.0.0.1}"
ICA_PROXY_PORT="${ICA_PROXY_PORT:-$((LITELLM_PORT + 100))}"
ICA_PROXY_BASE="${ICA_PROXY_BASE:-http://${ICA_PROXY_HOST}:${ICA_PROXY_PORT}}"
export LITELLM_CONFIG LITELLM_RUNTIME_CONFIG LITELLM_HOST LITELLM_PORT
export LITELLM_USE_ICA_PROXY ICA_PROXY_HOST ICA_PROXY_PORT ICA_PROXY_BASE

case "$LITELLM_USE_ICA_PROXY" in
  1|true|TRUE|yes|YES|on|ON)
    if [ -z "${ICA_BASE:-}" ]; then
      echo "WARNING: ICA_BASE is not set; ICA proxy will not start"
    else
      export ICA_PROXY_TARGET_BASE="${ICA_PROXY_TARGET_BASE:-$ICA_BASE}"
      python /app/deploy/scripts/ica-responses-proxy.py &
      echo "ICA proxy started on $ICA_PROXY_BASE -> $ICA_PROXY_TARGET_BASE"
    fi
    ;;
esac

python /app/deploy/scripts/prepare-litellm-config.py "$LITELLM_CONFIG" "$LITELLM_RUNTIME_CONFIG"
exec litellm --config "$LITELLM_RUNTIME_CONFIG" --host "$LITELLM_HOST" --port "$LITELLM_PORT"
