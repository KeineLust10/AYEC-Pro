#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/set_super_admin_password.py" ]]; then
  echo "ERROR: set_super_admin_password.py was not found. Extract the complete server package first." >&2
  exit 1
fi
if [[ ! -f "$ROOT/data/ayecpro.db" ]]; then
  echo "ERROR: data/ayecpro.db was not found. Run this script in the deployed AYEC server folder." >&2
  exit 1
fi

PYTHON="$ROOT/.venv-server/bin/python"
if [[ ! -x "$PYTHON" ]]; then PYTHON="$ROOT/.venv/bin/python"; fi
if [[ ! -x "$PYTHON" ]]; then PYTHON="$(command -v python3 || true)"; fi
if [[ -z "$PYTHON" || ! -x "$PYTHON" ]]; then
  echo "ERROR: Python was not found. Run the AYEC server installer first." >&2
  exit 1
fi

read -r -s -p "New AYEC admin password (minimum 8 characters): " AYEC_ADMIN_RESET_PASSWORD
echo
if [[ ${#AYEC_ADMIN_RESET_PASSWORD} -lt 8 ]]; then
  unset AYEC_ADMIN_RESET_PASSWORD
  echo "ERROR: Password must contain at least 8 characters." >&2
  exit 1
fi

export AYEC_ADMIN_EMAIL="ayecpro@gmail.com"
export AYEC_ADMIN_RESET_PASSWORD
export AYEC_DB_PATH="$ROOT/data/ayecpro.db"
"$PYTHON" "$ROOT/set_super_admin_password.py"
unset AYEC_ADMIN_RESET_PASSWORD AYEC_ADMIN_EMAIL AYEC_DB_PATH
echo "Admin password reset completed. Sign in as ayecpro@gmail.com."
