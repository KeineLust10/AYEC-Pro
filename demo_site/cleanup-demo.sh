#!/bin/sh
set -eu

DEMO_ENV_FILE="${AYEC_DEMO_ENV_FILE:-/etc/ayecpro/demo.env}"
DEMO_CLEANUP_SCRIPT="${AYEC_DEMO_CLEANUP_SCRIPT:-/srv/ayecpro-demo/demo_site/reset_demo_sessions.py}"

if [ ! -f "$DEMO_ENV_FILE" ]; then
  echo "Demo environment file not found" >&2
  exit 2
fi

set -a
. "$DEMO_ENV_FILE"
set +a

exec python3 "$DEMO_CLEANUP_SCRIPT" --age-hours 3
