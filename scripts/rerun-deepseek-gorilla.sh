#!/usr/bin/env bash
# One-off: rerun mutation experiment only for DeepSeek × gorilla-mux,
# whose clone failed transiently during the parallel launch.
set -eu

WD=/home/gizat/testgen-experiments/workdir-mutexp-deepseek-deepseek-chat/gorilla-mux
OUT=/home/gizat/exp/результаты/mutation-microexp/deepseek-deepseek-chat/gorilla-mux
LOG=/home/gizat/exp/логи/mutation-deepseek-gorilla-rerun.log

ENV_FILE=/home/gizat/exp/.env
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"

export PATH=/home/gizat/.local/go/bin:/home/gizat/go/bin:$PATH

mkdir -p "$OUT"

echo "─── re-cloning gorilla-mux ───" | tee -a "$LOG"
rm -rf "$WD"
git clone https://github.com/gorilla/mux.git "$WD" 2>&1 | tee -a "$LOG"
( cd "$WD" && git checkout 525206d7c2b250ca658700448b3bf23ec4707115 ) 2>&1 | tee -a "$LOG"

echo "─── running agent ───" | tee -a "$LOG"
/home/gizat/testgen-experiments/testgen-agent \
  --repo "$WD" \
  --base de7178dc9dffadc3cf56bece3962737e8b0710b8 \
  --report json \
  --ablation-config full \
  --model deepseek/deepseek-chat \
  --seed 42 \
  --temperature 0 \
  --test-timeout 120 \
  --mutation \
  --provider novita \
  2>&1 | tee -a "$LOG"

# Copy resulting JSON report into the canonical location
LATEST=$(ls -t "$WD"/testgen-report-*.json 2>/dev/null | head -1 || true)
if [[ -n "$LATEST" ]]; then
  cp "$LATEST" "$OUT/full.json"
  echo "─── copied $LATEST → $OUT/full.json ───" | tee -a "$LOG"
else
  echo "─── ERROR: no testgen-report-*.json produced ───" | tee -a "$LOG"
  exit 1
fi
