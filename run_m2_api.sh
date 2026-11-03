#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
api_host="${GUARDIAN_HOST:-127.0.0.1}"
api_port="${PORT:-8000}"
# An intentional nonlocal deployment must configure an API key. TLS/access policy
# is handled by the eventual hosting environment, not by this local launcher.
case "$api_host" in
  127.0.0.1|localhost|::1) ;;
  *) if [ -z "${GUARDIAN_API_KEY:-}" ]; then
       echo 'Set GUARDIAN_API_KEY before binding the API beyond localhost.' >&2
       exit 1
     fi ;;
esac
exec .venv/bin/python -m uvicorn m2_guardian.api:app --host "$api_host" --port "$api_port" --no-access-log
