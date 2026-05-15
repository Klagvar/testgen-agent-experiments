#!/usr/bin/env bash
# Detached launcher for rerun-repos.sh, designed to be called from
# PowerShell via `wsl -d Ubuntu -- bash scripts/launch-rerun.sh <model> "<repos>"`.
#
# Same idea as launch.sh, but wraps rerun-repos.sh for partial re-runs.
#
# Usage:
#   PROVIDER=Novita bash scripts/launch-rerun.sh deepseek/deepseek-chat \
#       "gorilla-mux spf13-cobra burntsushi-toml etcd-io-bbolt gin-gonic-gin hashicorp-raft restic-restic"

set -eu

MODEL="${1:?usage: launch-rerun.sh <model-id> \"<repo1> <repo2> ...\" [runs] [test-timeout]}"
REPOS="${2:?usage: launch-rerun.sh <model-id> \"<repos>\" ...}"
RUNS="${3:-3}"
TIMEOUT="${4:-60}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
mkdir -p логи

MODEL_TAG="$(echo "$MODEL" | sed -e 's|/|-|g' -e 's|:|-|g')"
OUT_FILE="логи/${MODEL_TAG}-rerun.out"

if pgrep -af "rerun-repos.sh $MODEL" >/dev/null 2>&1; then
  echo "ERROR: rerun already running for $MODEL" >&2
  pgrep -af "rerun-repos.sh $MODEL" >&2
  exit 1
fi
if pgrep -af "run-model.sh $MODEL" >/dev/null 2>&1; then
  echo "ERROR: full run-model.sh already running for $MODEL" >&2
  pgrep -af "run-model.sh $MODEL" >&2
  exit 1
fi

echo "── launching rerun ──"
echo "  model:    $MODEL"
echo "  repos:    $REPOS"
echo "  provider: ${PROVIDER:-<auto>}"
echo "  runs:     $RUNS"
echo "  timeout:  ${TIMEOUT}s"
echo "  log:      $OUT_FILE"
echo

nohup env \
    PROVIDER="${PROVIDER:-}" \
    PROVIDER_ALLOW_FALLBACKS="${PROVIDER_ALLOW_FALLBACKS:-0}" \
    SEED_BASE="${SEED_BASE:-42}" \
  bash scripts/rerun-repos.sh "$MODEL" "$REPOS" "$RUNS" "$TIMEOUT" \
  >"$OUT_FILE" 2>&1 </dev/null &
disown

sleep 3
echo "── status after 3s ──"
pgrep -af "rerun-repos.sh|testgen-bench" || echo "  WARNING: no process found, check $OUT_FILE"
echo
ls -la "$OUT_FILE" 2>/dev/null || echo "  (file not yet created)"
echo
echo "Done. Monitor with:"
echo "  tail -f ~/exp/$OUT_FILE"
echo "or the internal log:"
echo "  tail -f ~/exp/логи/${MODEL_TAG}-rerun.log"
