#!/bin/bash
# build.sh - полный цикл обновления дашборда: sync (Ads) -> generate (рендер).
# Для крона/systemd: */30 * * * * /path/to/build.sh >> /path/to/build.log 2>&1
set -euo pipefail
cd "$(dirname "$0")"

echo "[$(date -u +%FT%TZ)] sync.py..."
python3 sync.py

echo "[$(date -u +%FT%TZ)] generate.py..."
python3 generate.py

echo "[$(date -u +%FT%TZ)] done."
