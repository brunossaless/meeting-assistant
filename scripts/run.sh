#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "Ambiente virtual não encontrado. Rode ./scripts/setup.sh primeiro."
  exit 1
fi

set -a
[ -f .env ] && source .env
set +a

exec ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8756}"
