#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${AYEC_VENV:-$ROOT/.venv-server}"

if [[ ! -x "$VENV/bin/python" ]]; then
  "$ROOT/setup_server.sh"
fi

export AYEC_HOST="${AYEC_HOST:-0.0.0.0}"
export AYEC_PORT="${AYEC_PORT:-8501}"
export AYEC_DB_PATH="${AYEC_DB_PATH:-data/ayecpro.db}"
mkdir -p "$(dirname "$AYEC_DB_PATH")"

cd "$ROOT"
exec "$VENV/bin/python" Main.py \
  --host "$AYEC_HOST" \
  --port "$AYEC_PORT" \
  --db "$AYEC_DB_PATH"
