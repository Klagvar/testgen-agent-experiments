#!/usr/bin/env bash
# Launch mutation-testing micro-experiment in parallel for all 7 models.
# Each model is detached via nohup; logs in логи/mutation-launch-<model>.out.
#
# Usage: bash scripts/launch-mutation-microexp.sh

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
mkdir -p логи

# (model-id, provider) — providers pinned same as in main cube
declare -a MODELS=(
  "qwen/qwen-2.5-7b-instruct|Phala"
  "qwen/qwen3-coder-30b-a3b-instruct|Novita"
  "meta-llama/llama-3.3-70b-instruct|DeepInfra"
  "deepseek/deepseek-chat|DeepSeek"
  "openai/gpt-4o-mini|OpenAI"
  "anthropic/claude-3.5-haiku|Amazon Bedrock"
  "google/gemini-3-flash-preview|Google AI Studio"
)

# Refuse to launch if anything is already running.
if pgrep -af "run-mutation-microexp.sh|run-model.sh" >/dev/null 2>&1; then
  echo "ERROR: another run is in progress:" >&2
  pgrep -af "run-mutation-microexp.sh|run-model.sh" >&2
  exit 1
fi

echo "── launching mutation micro-experiment in parallel ──"
echo "  models: 7"
echo "  configs: full only"
echo "  runs:    1 per (model × repo)"
echo "  total:   8 repos × 7 models = 56 runs"
echo

for entry in "${MODELS[@]}"; do
  MODEL="${entry%%|*}"
  PROVIDER="${entry#*|}"
  TAG="$(echo "$MODEL" | sed -e 's|/|-|g' -e 's|:|-|g')"
  OUT_FILE="логи/mutation-launch-${TAG}.out"

  echo "  ──> $MODEL  (provider: $PROVIDER)"
  echo "      log: $OUT_FILE"

  nohup env \
      PROVIDER="$PROVIDER" \
      PROVIDER_ALLOW_FALLBACKS=0 \
      SEED_BASE=42 \
    bash scripts/run-mutation-microexp.sh "$MODEL" 120 \
    >"$OUT_FILE" 2>&1 </dev/null &
  disown
  sleep 1
done

echo
echo "── status after 5s ──"
sleep 5
pgrep -af "run-mutation-microexp.sh|testgen-bench" || echo "  WARNING: no processes found"

echo
echo "Monitor with:"
echo "  tail -f ~/exp/логи/mutation-*.log"
echo "  pgrep -af 'run-mutation-microexp.sh|testgen-bench'"
echo
echo "Estimate: ~1-2h wall-clock, ~\$1-2 USD total."
