#!/usr/bin/env bash
# Mutation-testing micro-experiment: run cmd/benchmark for ONE model with
# only the 'full' ablation config and a single run, with mutation testing
# turned on (default true after the agent change). Used to fill the gap
# in the main cube where mutation_enabled was always false.
#
# Usage: PROVIDER=<provider> bash scripts/run-mutation-microexp.sh <model-id>
# Example:
#   PROVIDER=Phala bash scripts/run-mutation-microexp.sh qwen/qwen-2.5-7b-instruct
#
# Output goes to результаты/mutation-microexp/<sanitized-model>/<repo>/full-run1.json.
set -eu

MODEL="${1:?usage: run-mutation-microexp.sh <model-id>}"
TEST_TIMEOUT="${2:-120}"   # mutations re-execute the test set, give them more headroom
SEED_BASE="${SEED_BASE:-42}"
PROVIDER="${PROVIDER:-}"
PROVIDER_ALLOW_FALLBACKS="${PROVIDER_ALLOW_FALLBACKS:-0}"

EXP_ROOT="$HOME/testgen-experiments"
AGENT_REPO_URL="https://github.com/Klagvar/testgen-agent.git"
AGENT_REPO_DIR="$EXP_ROOT/agent"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

MODEL_TAG="$(echo "$MODEL" | sed -e 's|/|-|g' -e 's|:|-|g')"
RESULTS_DIR="$REPO_ROOT/результаты/mutation-microexp/$MODEL_TAG"
LOG_DIR="$REPO_ROOT/логи"
LOG_FILE="$LOG_DIR/mutation-${MODEL_TAG}.log"

mkdir -p "$RESULTS_DIR" "$LOG_DIR"

# ─── 1. Load .env (with stray-CR protection) ─────────────────────────────
ENV_FILE="$REPO_ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"
: "${TESTGEN_API_KEY:?must be set in .env}"
: "${TESTGEN_API_URL:?must be set in .env}"

# ─── 2. PATH for Go ──────────────────────────────────────────────────────
export PATH="$HOME/.local/go/bin:$HOME/go/bin:$PATH"
command -v go >/dev/null || { echo "go not on PATH" >&2; exit 1; }

# ─── 3. Sync agent and rebuild binaries ──────────────────────────────────
mkdir -p "$EXP_ROOT"
if [[ ! -d "$AGENT_REPO_DIR/.git" ]]; then
  echo "─── Cloning testgen-agent into $AGENT_REPO_DIR ───" | tee -a "$LOG_FILE"
  git clone "$AGENT_REPO_URL" "$AGENT_REPO_DIR" 2>&1 | tee -a "$LOG_FILE"
else
  echo "─── Updating testgen-agent ───" | tee -a "$LOG_FILE"
  git -C "$AGENT_REPO_DIR" fetch --quiet origin 2>&1 | tee -a "$LOG_FILE"
  git -C "$AGENT_REPO_DIR" checkout --quiet origin/main 2>&1 | tee -a "$LOG_FILE"
fi

echo "─── Building binaries ───" | tee -a "$LOG_FILE"
( cd "$AGENT_REPO_DIR" \
    && go build -o "$EXP_ROOT/testgen-agent" ./cmd/agent \
    && go build -o "$EXP_ROOT/testgen-bench" ./cmd/benchmark ) 2>&1 | tee -a "$LOG_FILE"

# ─── 4. Materialize a runtime dataset.yaml with isolated workdir ─────────
# Use a separate workdir for mutation runs to avoid colliding with main cube.
DATASET_SRC="$REPO_ROOT/dataset.yaml"
DATASET_RT="$EXP_ROOT/dataset-mutexp-$MODEL_TAG.yaml"
WORKDIR_RT="$EXP_ROOT/workdir-mutexp-$MODEL_TAG"
[[ -f "$DATASET_SRC" ]] || { echo "ERROR: dataset not found at $DATASET_SRC" >&2; exit 1; }

{
  echo "workdir: $WORKDIR_RT"
  sed -e 's/\r$//' -e '/^[[:space:]]*workdir:.*/d' "$DATASET_SRC"
} > "$DATASET_RT"

DATASET_ABS="$DATASET_RT"
echo "─── runtime dataset: $DATASET_RT (workdir → $WORKDIR_RT) ───" | tee -a "$LOG_FILE"

# ─── 5. Build agent extra flags ──────────────────────────────────────────
# Mutation testing is on by default after the agent change; we still pass
# --mutation explicitly to make it visible in the JSON config block.
EXTRA_FLAGS="--temperature 0 --test-timeout $TEST_TIMEOUT --mutation"
if [[ -n "$PROVIDER" ]]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --provider $PROVIDER"
  if [[ "$PROVIDER_ALLOW_FALLBACKS" == "1" || "$PROVIDER_ALLOW_FALLBACKS" == "true" ]]; then
    EXTRA_FLAGS="$EXTRA_FLAGS --provider-allow-fallbacks"
  fi
fi

# ─── 6. Run ──────────────────────────────────────────────────────────────
{
echo
echo "═════════════════════════════════════════════════════════"
echo " mutation micro-experiment"
echo " model      : $MODEL"
echo " model tag  : $MODEL_TAG"
echo " configs    : full"
echo " runs/cfg   : 1"
echo " seed-base  : $SEED_BASE"
echo " test-timeout: ${TEST_TIMEOUT}s"
echo " provider   : ${PROVIDER:-<auto>} (allow-fallbacks=$PROVIDER_ALLOW_FALLBACKS)"
echo " dataset    : $DATASET_ABS"
echo " out        : $RESULTS_DIR"
echo " agent extra: $EXTRA_FLAGS"
echo " started    : $(date -Iseconds)"
echo "═════════════════════════════════════════════════════════"
} | tee -a "$LOG_FILE"

START=$(date +%s)
"$EXP_ROOT/testgen-bench" \
  --agent "$EXP_ROOT/testgen-agent" \
  --dataset "$DATASET_ABS" \
  --out "$RESULTS_DIR" \
  --model "$MODEL" \
  --configs full \
  --runs 1 \
  --seed-base "$SEED_BASE" \
  --extra "$EXTRA_FLAGS" \
  2>&1 | tee -a "$LOG_FILE"
END=$(date +%s)
DURATION=$((END - START))

{
echo
echo "═════════════════════════════════════════════════════════"
echo " model $MODEL_TAG completed in $((DURATION / 60))m $((DURATION % 60))s"
echo " finished  : $(date -Iseconds)"
echo "═════════════════════════════════════════════════════════"
} | tee -a "$LOG_FILE"

# ─── 7. Quick aggregate ──────────────────────────────────────────────────
echo
echo "─── Per-repo summary ───" | tee -a "$LOG_FILE"
for repo_dir in "$RESULTS_DIR"/*/; do
  repo=$(basename "$repo_dir")
  json_count=$(ls "$repo_dir"*.json 2>/dev/null | wc -l)
  echo "  $repo: $json_count JSON files"
done | tee -a "$LOG_FILE"

echo
echo "Full results in: $RESULTS_DIR"
echo "Log:             $LOG_FILE"
