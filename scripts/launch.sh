#!/usr/bin/env bash
# Detached launcher for a single model run, designed to be called from
# PowerShell via `wsl -d Ubuntu -- bash scripts/launch.sh <model>`.
#
# Wraps scripts/run-model.sh in nohup + disown so that the run survives
# the WSL session closing when PowerShell returns. Avoids any shell
# special characters in the command line so it can be invoked through
# wsl.exe + PowerShell without escaping headaches.
#
# Usage:
#   PROVIDER=Novita bash scripts/launch.sh deepseek/deepseek-chat
#   PROVIDER=Novita bash scripts/launch.sh deepseek/deepseek-chat 3 60
#
# Env vars (forwarded to run-model.sh):
#   PROVIDER, PROVIDER_ALLOW_FALLBACKS, SEED_BASE

set -eu

MODEL="${1:?usage: launch.sh <model-id> [runs] [test-timeout-sec]}"
RUNS="${2:-3}"
TIMEOUT="${3:-60}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
mkdir -p логи

MODEL_TAG="$(echo "$MODEL" | sed -e 's|/|-|g' -e 's|:|-|g')"
OUT_FILE="логи/${MODEL_TAG}.out"

# Refuse to launch a duplicate.
if pgrep -af "run-model.sh $MODEL" >/dev/null 2>&1; then
  echo "ERROR: already running for $MODEL:" >&2
  pgrep -af "run-model.sh $MODEL" >&2
  exit 1
fi

echo "── launching ──"
echo "  model:    $MODEL"
echo "  provider: ${PROVIDER:-<auto>}"
echo "  runs:     $RUNS"
echo "  timeout:  ${TIMEOUT}s"
echo "  log:      $OUT_FILE"
echo

nohup env \
    PROVIDER="${PROVIDER:-}" \
    PROVIDER_ALLOW_FALLBACKS="${PROVIDER_ALLOW_FALLBACKS:-0}" \
    SEED_BASE="${SEED_BASE:-42}" \
  bash scripts/run-model.sh "$MODEL" "$RUNS" "$TIMEOUT" \
  >"$OUT_FILE" 2>&1 </dev/null &
disown

sleep 3
echo "── status after 3s ──"
pgrep -af "run-model.sh|testgen-bench" || echo "  WARNING: no process found, check $OUT_FILE"
echo
echo "── tail $OUT_FILE ──"
ls -la "$OUT_FILE" 2>/dev/null || echo "  (file not yet created)"
echo
echo "Done. Monitor with:"
echo "  tail -f ~/exp/$OUT_FILE"
echo "or the full internal log:"
echo "  tail -f ~/exp/логи/${MODEL_TAG}.log"
