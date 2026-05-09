#!/usr/bin/env bash
# scripts/smoke.sh — End-to-end smoke test on a single repo and the
# cheapest model from the experimental cube.
#
# Goals:
#   1. Verify that cmd/benchmark builds, clones, resets between runs,
#      and produces a valid JSON report for every ablation configuration.
#   2. Measure realistic per-run token usage so the budget in план.md
#      §9.1 can be calibrated against actual numbers (rather than the
#      a-priori 30K prompt + 10K completion estimate).
#
# Cost: 1 repo (google-uuid) × 6 ablation configs × 1 run on
#       qwen/qwen-2.5-7b-instruct ≈ $0.01.
set -euo pipefail

# ─── 1. Configuration ───────────────────────────────────────────────────
EXP_ROOT="$HOME/testgen-experiments"
AGENT_REPO_URL="https://github.com/Klagvar/testgen-agent.git"
AGENT_REPO_DIR="$EXP_ROOT/agent"
WORKDIR="$EXP_ROOT/workdir"
RESULTS_DIR="$EXP_ROOT/results-smoke"

MODEL="qwen/qwen-2.5-7b-instruct"
SMOKE_REPO_NAME="google-uuid"
SMOKE_REPO_URL="https://github.com/google/uuid.git"
SMOKE_BASE="c58770eb495f55fe2ced6284f93c5158a62e53e3"
SMOKE_HEAD="a2b2b32373ff0b1a312b7fdf6d38a977099698a6"

# ─── 2. Locate the experiments repo and load .env ───────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found." >&2
  echo "Create it with: TESTGEN_API_KEY=...; TESTGEN_API_URL=https://openrouter.ai/api/v1" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
# .env is often edited from Windows; strip stray CRs that would otherwise
# end up appended to URLs and tokens (causing "invalid control character
# in URL" deep inside net/http).
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"
: "${TESTGEN_API_KEY:?must be set in .env}"
: "${TESTGEN_API_URL:?must be set in .env}"

# ─── 3. PATH for Go ─────────────────────────────────────────────────────
export PATH="$HOME/.local/go/bin:$HOME/go/bin:$PATH"
command -v go >/dev/null || { echo "go not on PATH; install Go first" >&2; exit 1; }

# ─── 4. Sync testgen-agent and build the binaries we need ───────────────
mkdir -p "$EXP_ROOT"
if [[ ! -d "$AGENT_REPO_DIR/.git" ]]; then
  echo "─── Cloning testgen-agent into $AGENT_REPO_DIR ───"
  git clone "$AGENT_REPO_URL" "$AGENT_REPO_DIR"
else
  echo "─── Updating testgen-agent ───"
  git -C "$AGENT_REPO_DIR" fetch --quiet origin
  git -C "$AGENT_REPO_DIR" checkout --quiet origin/main
fi

echo "─── Building binaries ───"
( cd "$AGENT_REPO_DIR" && \
    go build -o "$EXP_ROOT/testgen-agent" ./cmd/agent && \
    go build -o "$EXP_ROOT/testgen-bench" ./cmd/benchmark && \
    go build -o "$EXP_ROOT/testgen-ablate-report" ./cmd/ablate-report )

# ─── 5. Smoke dataset (one repo only) ───────────────────────────────────
SMOKE_DATASET="$EXP_ROOT/smoke-dataset.yaml"
cat > "$SMOKE_DATASET" <<EOF
workdir: $WORKDIR
repos:
  - name: $SMOKE_REPO_NAME
    url: $SMOKE_REPO_URL
    base: $SMOKE_BASE
    head: $SMOKE_HEAD
EOF
echo "─── Smoke dataset: $SMOKE_DATASET ───"
cat "$SMOKE_DATASET"

# ─── 6. Run cmd/benchmark ───────────────────────────────────────────────
rm -rf "$RESULTS_DIR"
mkdir -p "$RESULTS_DIR"

echo
echo "═════════════════════════════════════════════════════════"
echo " smoke run: 1 repo × 6 configs × 1 run on $MODEL"
echo "═════════════════════════════════════════════════════════"
echo

START=$(date +%s)
"$EXP_ROOT/testgen-bench" \
  --agent "$EXP_ROOT/testgen-agent" \
  --dataset "$SMOKE_DATASET" \
  --out "$RESULTS_DIR" \
  --model "$MODEL" \
  --runs 1 \
  --extra "--temperature 0 --seed 42 --test-timeout 60"
END=$(date +%s)
DURATION=$((END - START))

echo
echo "═════════════════════════════════════════════════════════"
echo " smoke completed in ${DURATION}s"
echo "═════════════════════════════════════════════════════════"
ls -la "$RESULTS_DIR/$SMOKE_REPO_NAME/"

# ─── 7. Token / coverage / cost summary ─────────────────────────────────
echo
echo "─── Per-config summary ───"
python3 - "$RESULTS_DIR/$SMOKE_REPO_NAME" <<'PY'
import sys, json, glob, os

d = sys.argv[1]
# Qwen 2.5 7B Instruct on OpenRouter (verified 2026-05-09).
PROMPT_USD_PER_M = 0.04
COMPL_USD_PER_M  = 0.10

reports = sorted(p for p in glob.glob(os.path.join(d, "*.json"))
                 if os.path.basename(p) != "repo.json")
if not reports:
    print("  (no reports)")
    sys.exit(1)

total_p = total_c = 0
print(f"  {'config':24s} {'prompt':>7s} {'compl':>7s} {'cov':>7s} {'mut':>7s} {'pass':>7s} {'cost':>7s}")
print(f"  {'─'*24} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7}")
for f in reports:
    with open(f) as fp:
        r = json.load(fp)
    cfg = r.get("config", {}).get("ablation_config") or os.path.basename(f).replace(".json", "")
    t = r.get("totals", {})
    p = t.get("prompt_tokens", 0)
    c = t.get("completion_tokens", 0)
    cov = t.get("diff_coverage_pct")
    mut = t.get("mutation_score_pct")
    gen = t.get("tests_generated", 0)
    val = t.get("tests_validated", 0)
    pass_pct = (100.0 * val / gen) if gen else None
    cost = p * PROMPT_USD_PER_M / 1e6 + c * COMPL_USD_PER_M / 1e6
    cov_s = f"{cov:5.1f}%" if cov is not None else "  —  "
    mut_s = f"{mut:5.1f}%" if mut is not None else "  —  "
    pas_s = f"{pass_pct:5.1f}%" if pass_pct is not None else "  —  "
    print(f"  {cfg:24s} {p:7d} {c:7d} {cov_s:>7s} {mut_s:>7s} {pas_s:>7s}  ${cost:.4f}")
    total_p += p
    total_c += c

cost = total_p * PROMPT_USD_PER_M / 1e6 + total_c * COMPL_USD_PER_M / 1e6
print(f"  {'─'*24} {'─'*7} {'─'*7}")
print(f"  {'TOTAL':24s} {total_p:7d} {total_c:7d}                      ${cost:.4f}")

n = len(reports)
print(f"\n  Per-run averages: prompt≈{total_p//n}, completion≈{total_c//n}.")
print(f"  Extrapolated full cube cost on this model (8 repos × 6 configs × 3 runs = 144 runs):")
full_cost = (total_p / n) * 144 * PROMPT_USD_PER_M / 1e6 \
          + (total_c / n) * 144 * COMPL_USD_PER_M / 1e6
print(f"    ≈ ${full_cost:.2f}")
PY

echo
echo "Done. Compare these numbers to план.md §9.1 (estimated 30K/10K per run)."
