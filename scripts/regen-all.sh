#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
for m in результаты/raw/*/; do
  echo "── $m ──"
  python3 scripts/rebuild-benchmark-index.py "$m" 2>&1 | tail -1
  python3 scripts/generate-run-info.py "$m" 2>&1 | tail -1
done
