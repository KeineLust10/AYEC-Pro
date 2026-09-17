#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${AYEC_PYTHON:-python3}"
VENV="${AYEC_VENV:-$ROOT/.venv-server}"

"$PYTHON_BIN" -c 'import sys; assert (3, 11) <= sys.version_info[:2] < (3, 14), "Python 3.11-3.13 gerekli (3.11/3.12 önerilir)."'
if [[ "${PADDLE_OCR:-0}" == "1" ]]; then
  "$PYTHON_BIN" -c 'import sys; assert sys.version_info[:2] < (3, 13), "PaddleOCR 2.x için Python 3.11 veya 3.12 gerekli."'
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi
if [[ "${PADDLE_OCR:-0}" == "1" ]]; then
  "$VENV/bin/python" -c 'import sys; assert sys.version_info[:2] < (3, 13), "Mevcut sanal ortam PaddleOCR için Python 3.11/3.12 kullanmalıdır."'
fi

"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel

requirements="requirements-ocr.txt"
if [[ "${PADDLE_OCR:-0}" == "1" ]]; then
  requirements="requirements-paddle.txt"
elif [[ "${CORE_ONLY:-0}" == "1" ]]; then
  requirements="requirements.txt"
fi

"$VENV/bin/python" -m pip install --requirement "$ROOT/$requirements"
"$VENV/bin/python" "$ROOT/tools/verify_runtime.py"

if ! command -v tesseract >/dev/null 2>&1; then
  echo "UYARI: Görsel OCR için tesseract-ocr ve tesseract-ocr-tur sistem paketlerini kurun." >&2
fi

echo "AYEC Pro Web kurulumu tamamlandı: $requirements"
