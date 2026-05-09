#!/usr/bin/env bash
# Re-run cmd/benchmark for a SUBSET of repos for an existing model.
# Useful when only a few repos failed (e.g. dataset SHAs needed swapping)
# and we don't want to re-do already-valid runs.
#
# Usage: bash scripts/rerun-repos.sh <model-id> "<repo1> <repo2> ..." [<runs>] [<test-timeout-sec>]
# Example:
#   PROVIDER=Phala bash scripts/rerun-repos.sh qwen/qwen-2.5-7b-instruct "burntsushi-toml hashicorp-raft" 3 60
#
# What it does:
#   1. Builds a temporary dataset.yaml containing only the requested repos
#      (their SHAs are taken from the canonical dataset.yaml at REPO_ROOT).
#   2. Wipes those repos' result directories so the harness writes fresh JSON.
#   3. Force-resets the repo's working directory to the new HEAD SHA, since the
#      previous run may have left it on the old SHA.
#   4. Calls scripts/run-model.sh internals on the temporary dataset.
set -eu

MODEL="${1:?usage: rerun-repos.sh <model-id> \"<repo1> <repo2> ...\" [<runs>] [<test-timeout-sec>]}"
REPOS_LIST="${2:?usage: rerun-repos.sh <model-id> \"<repo1> <repo2>\" ...}"
RUNS="${3:-3}"
TEST_TIMEOUT="${4:-60}"
SEED_BASE="${SEED_BASE:-42}"
PROVIDER="${PROVIDER:-}"
PROVIDER_ALLOW_FALLBACKS="${PROVIDER_ALLOW_FALLBACKS:-0}"

EXP_ROOT="$HOME/testgen-experiments"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

MODEL_TAG="$(echo "$MODEL" | sed -e 's|/|-|g' -e 's|:|-|g')"
RESULTS_DIR="$REPO_ROOT/результаты/raw/$MODEL_TAG"
LOG_DIR="$REPO_ROOT/логи"
LOG_FILE="$LOG_DIR/${MODEL_TAG}-rerun.log"

mkdir -p "$RESULTS_DIR" "$LOG_DIR"

# ─── 1. Load .env ────────────────────────────────────────────────────────
ENV_FILE="$REPO_ROOT/.env"
[[ -f "$ENV_FILE" ]] || { echo "ERROR: $ENV_FILE not found" >&2; exit 1; }
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"

# ─── 2. PATH + binaries ──────────────────────────────────────────────────
export PATH="$HOME/.local/go/bin:$HOME/go/bin:$PATH"
[[ -x "$EXP_ROOT/testgen-agent" && -x "$EXP_ROOT/testgen-bench" ]] || {
  echo "ERROR: binaries missing in $EXP_ROOT, run scripts/run-model.sh first" >&2
  exit 1
}

# ─── 3. Build temporary dataset filtered to selected repos ───────────────
DATASET_SRC="$REPO_ROOT/dataset.yaml"
DATASET_RT="$EXP_ROOT/dataset-rerun.yaml"

REPOS_LIST_NORMALIZED="$(echo "$REPOS_LIST" | tr ',' ' ' | xargs)"
echo "─── filtering dataset for repos: $REPOS_LIST_NORMALIZED ───" | tee -a "$LOG_FILE"

REPOS_LIST_NORMALIZED="$REPOS_LIST_NORMALIZED" python3 - "$DATASET_SRC" "$DATASET_RT" <<'PY'
import os
import re
import sys

src_path, dst_path = sys.argv[1:3]
keep = set(os.environ.get("REPOS_LIST_NORMALIZED", "").split())

text = open(src_path, encoding="utf-8").read().replace("\r", "")

# Walk lines and segment into: comment-header (file-level docstrings) and
# repo blocks (each starting with "  - name:" up to the next such line or EOF).
# Drop any pre-existing "workdir:" or "repos:" lines because we emit our own
# in the runtime YAML.
lines = text.splitlines()
header = []
blocks = []
cur = None
for ln in lines:
    stripped = ln.lstrip()
    if ln.startswith("  - name:"):
        if cur is not None:
            blocks.append(cur)
        cur = [ln]
        continue
    if cur is not None:
        # Continue the current block until we see a top-level non-block line
        # (a top-level key or a blank-then-non-block transition).
        if ln.startswith("  ") or ln == "":
            cur.append(ln)
            continue
        # Top-level line ends the current block. Fall through to header logic.
        blocks.append(cur)
        cur = None
    # In the header section: keep only comments/blank lines, drop existing
    # workdir/repos keys so they cannot conflict with the ones we generate.
    if stripped.startswith("workdir:") or stripped.startswith("repos:"):
        continue
    header.append(ln)

if cur is not None:
    blocks.append(cur)

filtered = []
for blk in blocks:
    m = re.match(r"\s*-\s+name:\s+(\S+)", blk[0])
    if m and m.group(1) in keep:
        filtered.append(blk)

if len(filtered) != len(keep):
    found = {re.match(r"\s*-\s+name:\s+(\S+)", b[0]).group(1) for b in filtered}
    missing = keep - found
    raise SystemExit(f"missing repos in dataset.yaml: {sorted(missing)}")

with open(dst_path, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(header).rstrip() + "\n\n")
    f.write(f"workdir: {os.environ['HOME']}/testgen-experiments/workdir\n\nrepos:\n")
    for blk in filtered:
        f.write("\n".join(blk).rstrip() + "\n\n")
PY

# Sanity: ensure workdir line is correct
head "$DATASET_RT" | tee -a "$LOG_FILE"

# ─── 4. Wipe results & reset working trees for selected repos ────────────
for r in $REPOS_LIST_NORMALIZED; do
  echo "─── wiping previous results for $r ───" | tee -a "$LOG_FILE"
  rm -rf "$RESULTS_DIR/$r"
  D="$EXP_ROOT/workdir/$r"
  if [ -d "$D/.git" ]; then
    # Force-fetch new SHAs in case dataset was updated
    git -C "$D" fetch --quiet origin || true
    # Detach to avoid "branch X is checked out" errors on subsequent reset
    git -C "$D" checkout --quiet --detach 2>/dev/null || true
    git -C "$D" clean -fdx >/dev/null 2>&1 || true
  fi
done

# ─── 5. Build agent --extra ──────────────────────────────────────────────
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
echo " repos      : $REPOS_LIST_NORMALIZED"
echo " runs/cfg   : $RUNS"
echo " seed-base  : $SEED_BASE"
echo " test-timeout: ${TEST_TIMEOUT}s"
echo " provider   : ${PROVIDER:-<auto>} (allow-fallbacks=$PROVIDER_ALLOW_FALLBACKS)"
echo " agent extra: $EXTRA_FLAGS"
echo " started    : $(date -Iseconds)"
echo "═════════════════════════════════════════════════════════"
} | tee -a "$LOG_FILE"

START=$(date +%s)
"$EXP_ROOT/testgen-bench" \
  --agent "$EXP_ROOT/testgen-agent" \
  --dataset "$DATASET_RT" \
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
echo " rerun completed in $((DURATION / 60))m $((DURATION % 60))s"
echo " finished  : $(date -Iseconds)"
echo "═════════════════════════════════════════════════════════"
} | tee -a "$LOG_FILE"

echo
echo "─── per-repo summary after rerun ───" | tee -a "$LOG_FILE"
for r in $REPOS_LIST_NORMALIZED; do
  c=$(ls "$RESULTS_DIR/$r/"*.json 2>/dev/null | wc -l)
  echo "  $r: $c JSON files" | tee -a "$LOG_FILE"
done

echo
echo "Full results in: $RESULTS_DIR"
echo "Log:             $LOG_FILE"
