#!/usr/bin/env bash
# Run cmd/benchmark for ONE model on the full dataset:
#   8 repos × 6 ablation configs × N runs = 8*6*N entries per model.
#
# Usage: bash scripts/run-model.sh <model-id> [<runs>] [<test-timeout-sec>]
# Example:
#   bash scripts/run-model.sh qwen/qwen-2.5-7b-instruct 3 60
#
# Provider pinning (recommended for reproducibility):
#   PROVIDER=Phala bash scripts/run-model.sh qwen/qwen-2.5-7b-instruct
#   PROVIDER="Phala,DeepInfra" PROVIDER_ALLOW_FALLBACKS=1 bash scripts/run-model.sh ...
# When PROVIDER is set, every request to OpenRouter is constrained to that
# provider list (provider.only); allow_fallbacks defaults to false (strict
# pin) unless PROVIDER_ALLOW_FALLBACKS=1.
#
# Output goes to результаты/raw/<sanitized-model>/<repo>/<config>-runN.json.
# Logs are streamed to логи/<sanitized-model>.log so the run can be
# detached with nohup and progress watched with `tail -f`.
set -eu

MODEL="${1:?usage: run-model.sh <model-id> [<runs>] [<test-timeout-sec>]}"
RUNS="${2:-3}"
TEST_TIMEOUT="${3:-60}"
SEED_BASE="${SEED_BASE:-42}"
PROVIDER="${PROVIDER:-}"
PROVIDER_ALLOW_FALLBACKS="${PROVIDER_ALLOW_FALLBACKS:-0}"

EXP_ROOT="$HOME/testgen-experiments"
AGENT_REPO_URL="https://github.com/Klagvar/testgen-agent.git"
AGENT_REPO_DIR="$EXP_ROOT/agent"

# Locate this experiments repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Sanitize model id for use as a path component (slash, colon → dash).
MODEL_TAG="$(echo "$MODEL" | sed -e 's|/|-|g' -e 's|:|-|g')"
RESULTS_DIR="$REPO_ROOT/результаты/raw/$MODEL_TAG"
LOG_DIR="$REPO_ROOT/логи"
LOG_FILE="$LOG_DIR/$MODEL_TAG.log"

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

# ─── 4. Materialize a runtime dataset.yaml on the native Linux fs ────────
#
# The repo lives on /mnt/d/... (NTFS bridged into WSL). cmd/benchmark
# resolves workdir relative to the dataset file, so a literal copy of
# dataset.yaml from the repo would clone every test repository onto
# /mnt/d, where every git op and every `go build` is 5–10× slower than
# on the native Linux filesystem (no inode caching, no fsync coalescing,
# defender scans .go files synchronously).
#
# We therefore materialise a runtime copy of the YAML in $EXP_ROOT and
# overwrite its `workdir:` line with the native path. The repo's
# dataset.yaml stays portable; only the runtime copy is WSL-specific.
DATASET_SRC="$REPO_ROOT/dataset.yaml"
# Per-model runtime dataset + workdir so multiple models can run in parallel
# without colliding on git clones / merger output.
DATASET_RT="$EXP_ROOT/dataset-runtime-$MODEL_TAG.yaml"
WORKDIR_RT="$EXP_ROOT/workdir-$MODEL_TAG"
[[ -f "$DATASET_SRC" ]] || { echo "ERROR: dataset not found at $DATASET_SRC" >&2; exit 1; }

{
  echo "workdir: $WORKDIR_RT"
  sed -e 's/\r$//' -e '/^[[:space:]]*workdir:.*/d' "$DATASET_SRC"
} > "$DATASET_RT"

DATASET_ABS="$DATASET_RT"
echo "─── runtime dataset: $DATASET_RT (workdir → $WORKDIR_RT) ───" | tee -a "$LOG_FILE"

# ─── 5. Build agent --extra flags ────────────────────────────────────────
EXTRA_FLAGS="--temperature 0 --test-timeout $TEST_TIMEOUT"
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
echo " model      : $MODEL"
echo " model tag  : $MODEL_TAG"
echo " runs/cfg   : $RUNS"
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
  --runs "$RUNS" \
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
