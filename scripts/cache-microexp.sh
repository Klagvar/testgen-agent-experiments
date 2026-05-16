#!/usr/bin/env bash
# Micro-experiment: measure functional-cache effectiveness on incremental
# CI re-runs. Implements the design from план.md §8.5.
#
# Three runs, all on gorilla/mux with gpt-4o-mini, ablation-config=full:
#   A. Cold:        empty .testgen-cache.json, base=de7178d, head=525206d
#   B. Warm same:   keep .testgen-cache.json from A, base=de7178d, head=525206d
#   C. Warm shift:  keep .testgen-cache.json from A/B, base=525206d, head=db9d1d0
#
# Each run is invoked through testgen-agent directly (NOT testgen-bench),
# because testgen-bench performs `git clean -fdx` between runs which
# would wipe the cache file. We only clean *generated artefacts* between
# runs while preserving .testgen-cache.json.
#
# Output: scripts writes three JSON reports plus a side-by-side summary
# into результаты/cache-microexp/.
set -eu

EXP_ROOT="$HOME/testgen-experiments"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

MODEL="openai/gpt-4o-mini"
PROVIDER=""
WORK="$EXP_ROOT/cache-microexp"
OUT_DIR="$REPO_ROOT/результаты/cache-microexp"
LOG_DIR="$REPO_ROOT/логи"
LOG_FILE="$LOG_DIR/cache-microexp.log"

BASE_AB="de7178dc9dffadc3cf56bece3962737e8b0710b8"   # A,B base
HEAD_AB="525206d7c2b250ca658700448b3bf23ec4707115"   # A,B head
BASE_C="525206d7c2b250ca658700448b3bf23ec4707115"    # C base
HEAD_C="db9d1d0073d27a0a2d9a8c1bc52aa0af4374d265"    # C head (next commit)

mkdir -p "$OUT_DIR" "$LOG_DIR" "$WORK"

# Load .env
ENV_FILE="$REPO_ROOT/.env"
[[ -f "$ENV_FILE" ]] || { echo "no $ENV_FILE" >&2; exit 1; }
set -a; . "$ENV_FILE"; set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"

export PATH="$HOME/.local/go/bin:$HOME/go/bin:$PATH"

# Ensure binaries exist (rebuilt by run-model.sh during last full run)
[[ -x "$EXP_ROOT/testgen-agent" ]] || { echo "agent binary missing in $EXP_ROOT" >&2; exit 1; }

# Sanitize model id
MODEL_TAG="$(echo "$MODEL" | sed -e 's|/|-|g' -e 's|:|-|g')"

# ─── Prepare clean clone of gorilla/mux ─────────────────────────────────
REPO_DIR="$WORK/gorilla-mux"
if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "─── cloning gorilla/mux into $REPO_DIR ───" | tee -a "$LOG_FILE"
  git clone --quiet https://github.com/gorilla/mux.git "$REPO_DIR"
fi

run_agent() {
  local label="$1" base="$2" head="$3"
  echo
  echo "═══════════════════════════════════════════════"
  echo "  RUN $label"
  echo "    base: $base"
  echo "    head: $head"
  echo "    cache file present: $(ls "$REPO_DIR/.testgen-cache.json" 2>/dev/null && echo YES || echo NO)"
  echo "═══════════════════════════════════════════════"

  cd "$REPO_DIR"
  # Reset to the requested head, then clean generated artefacts only
  git fetch --quiet origin
  git checkout --quiet --detach "$head"
  # Remove generated test files but KEEP .testgen-cache.json
  git clean -fdx -e .testgen-cache.json -e /vendor >/dev/null 2>&1 || true

  local START END DUR REPORT
  START=$(date +%s)
  "$EXP_ROOT/testgen-agent" \
    --repo "$REPO_DIR" \
    --base "$base" \
    --report json \
    --ablation-config full \
    --model "$MODEL" \
    --temperature 0 \
    --test-timeout 60 \
    --run-index 1 --seed 42 \
    2>&1 | tee -a "$LOG_FILE" | tail -10
  END=$(date +%s)
  DUR=$((END - START))

  # Find newest report file and copy it to OUT_DIR
  REPORT=$(ls -1t "$REPO_DIR"/testgen-report-*.json 2>/dev/null | head -1)
  if [[ -z "$REPORT" ]]; then
    echo "ERROR: no JSON report produced for $label" >&2
    exit 1
  fi
  cp "$REPORT" "$OUT_DIR/run-$label.json"
  rm -f "$REPORT"
  echo "  duration: ${DUR}s"
  echo "  report: $OUT_DIR/run-$label.json"
}

# Wipe cache so RUN A starts cold
rm -f "$REPO_DIR/.testgen-cache.json"

run_agent "A-cold"      "$BASE_AB" "$HEAD_AB"
run_agent "B-warm-same" "$BASE_AB" "$HEAD_AB"
run_agent "C-warm-next" "$BASE_C"  "$HEAD_C"

# Side-by-side summary
python3 - "$OUT_DIR" <<'PY'
import json, os, sys
out = sys.argv[1]
labels = ["A-cold", "B-warm-same", "C-warm-next"]
rows = []
for lbl in labels:
    p = os.path.join(out, f"run-{lbl}.json")
    if not os.path.isfile(p):
        rows.append((lbl, None))
        continue
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    t = d.get("totals", {})
    cfg = d.get("config", {})
    rows.append((lbl, {
        "files_processed": t.get("files_processed"),
        "tests_validated": t.get("tests_validated"),
        "prompt_tokens":   t.get("prompt_tokens"),
        "completion_tokens": t.get("completion_tokens"),
        "duration_seconds": t.get("duration_seconds") or t.get("total_duration_seconds"),
        "cache_hits":      t.get("cache_hits"),
        "cache_misses":    t.get("cache_misses"),
    }))

print()
print("═════════ SUMMARY ═════════")
print(f"{'label':<14} {'files':>5} {'tests':>5} {'prompt_t':>9} {'compl_t':>8} {'sec':>5} {'hit':>4} {'miss':>4}")
for lbl, r in rows:
    if r is None:
        print(f"{lbl:<14} —")
        continue
    def fmt(v):
        return v if v is not None else "—"
    print(f"{lbl:<14} {fmt(r['files_processed']):>5} {fmt(r['tests_validated']):>5} "
          f"{fmt(r['prompt_tokens']):>9} {fmt(r['completion_tokens']):>8} "
          f"{fmt(r['duration_seconds']):>5} {fmt(r['cache_hits']):>4} {fmt(r['cache_misses']):>4}")

# Markdown table for ВКР
md = os.path.join(out, "SUMMARY.md")
with open(md, "w", encoding="utf-8") as f:
    f.write("# Micro-experiment: эффективность кэша\n\n")
    f.write("Модель: `openai/gpt-4o-mini`, репо: `gorilla/mux`, ablation: `full`.\n\n")
    f.write("| Прогон | base..head | files | tests | prompt | completion | сек | hit | miss |\n")
    f.write("|--------|-----------|------:|------:|-------:|-----------:|----:|----:|----:|\n")
    descrs = {
        "A-cold":       "de7178d..525206d (cold)",
        "B-warm-same":  "de7178d..525206d (warm, same)",
        "C-warm-next":  "525206d..db9d1d0 (warm, next-commit)",
    }
    for lbl, r in rows:
        d = descrs.get(lbl, lbl)
        if r is None:
            f.write(f"| {lbl} | {d} | — | — | — | — | — | — | — |\n")
            continue
        def fmt(v):
            return str(v) if v is not None else "—"
        f.write(
            f"| {lbl} | {d} | {fmt(r['files_processed'])} | {fmt(r['tests_validated'])} "
            f"| {fmt(r['prompt_tokens'])} | {fmt(r['completion_tokens'])} "
            f"| {fmt(r['duration_seconds'])} | {fmt(r['cache_hits'])} | {fmt(r['cache_misses'])} |\n"
        )
    f.write("\n*Если поля cache_hits/misses пустые — значит сборка агента не пробрасывает их в JSON-totals; в этом случае косвенный показатель — резкое падение prompt+completion токенов на B относительно A.*\n")
print(f"\nWrote markdown summary: {md}")
PY

echo
echo "Done. Results in $OUT_DIR"
