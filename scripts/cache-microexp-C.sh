#!/usr/bin/env bash
# Helper to run only step C of the cache micro-experiment, reusing the
# cache file populated by an earlier scripts/cache-microexp.sh execution.
set -eu

EXP_ROOT="$HOME/testgen-experiments"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORK="$EXP_ROOT/cache-microexp/gorilla-mux"
OUT_DIR="$REPO_ROOT/результаты/cache-microexp"
LOG_FILE="$REPO_ROOT/логи/cache-microexp.log"
BASE_C="525206d7c2b250ca658700448b3bf23ec4707115"
HEAD_C="db9d1d0073d27a0a2d9a8c1bc52aa0af4374d265"

set -a
. "$REPO_ROOT/.env"
set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"
export PATH="$HOME/.local/go/bin:$HOME/go/bin:$PATH"

cd "$WORK"
echo "═══════════════════════════════════════════════"
echo "  RUN C-warm-next"
echo "    base: $BASE_C"
echo "    head: $HEAD_C"
echo "    cache: $(ls "$WORK/.testgen-cache.json" 2>/dev/null && echo YES || echo NO)"
echo "═══════════════════════════════════════════════"

git fetch --quiet origin
git checkout --quiet --detach "$HEAD_C"
git clean -fdx -e .testgen-cache.json -e /vendor >/dev/null 2>&1 || true

START=$(date +%s)
"$EXP_ROOT/testgen-agent" \
  --repo "$WORK" \
  --base "$BASE_C" \
  --report json \
  --ablation-config full \
  --model openai/gpt-4o-mini \
  --temperature 0 \
  --test-timeout 60 \
  --run-index 1 --seed 42 \
  2>&1 | tee -a "$LOG_FILE" | tail -10
END=$(date +%s)
DUR=$((END - START))

REPORT=$(ls -1t "$WORK"/testgen-report-*.json 2>/dev/null | head -1)
[[ -n "$REPORT" ]] || { echo "no report" >&2; exit 1; }
cp "$REPORT" "$OUT_DIR/run-C-warm-next.json"
rm -f "$REPORT"
echo "  duration: ${DUR}s"
echo "  report: $OUT_DIR/run-C-warm-next.json"

# Regenerate the SUMMARY.md across all three runs
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
    rows.append((lbl, {
        "files_processed": t.get("files_processed"),
        "tests_validated": t.get("tests_validated"),
        "prompt_tokens":   t.get("prompt_tokens"),
        "completion_tokens": t.get("completion_tokens"),
        "duration_seconds": t.get("duration_seconds") or t.get("total_duration_seconds"),
        "cache_hits":      t.get("cache_hits"),
        "cache_misses":    t.get("cache_misses"),
        "tests_cached":    t.get("tests_cached"),
    }))

print()
print("═════════ SUMMARY ═════════")
hdr = ["label","files","tests","prompt","compl","sec","hits","misses","cached"]
print(" ".join(f"{h:>11}" for h in hdr))
for lbl, r in rows:
    if r is None:
        print(f"{lbl:>11} —")
        continue
    def f(v): return str(v) if v is not None else "—"
    print(" ".join(f"{x:>11}" for x in [
        lbl, f(r['files_processed']), f(r['tests_validated']),
        f(r['prompt_tokens']), f(r['completion_tokens']),
        f(r['duration_seconds']), f(r['cache_hits']),
        f(r['cache_misses']), f(r['tests_cached']),
    ]))

md = os.path.join(out, "SUMMARY.md")
with open(md, "w", encoding="utf-8") as fp:
    fp.write("# Micro-experiment: эффективность кэша\n\n")
    fp.write("Модель: `openai/gpt-4o-mini`, репо: `gorilla/mux`, ablation: `full`.\n\n")
    fp.write("Дизайн (план §8.5):\n\n")
    fp.write("- **A — cold:** пустой `.testgen-cache.json`, `de7178d..525206d`.\n")
    fp.write("- **B — warm same head:** кэш от A, та же пара `de7178d..525206d`.\n")
    fp.write("- **C — warm shifted head:** кэш от A/B, новая пара `525206d..db9d1d0` (следующий коммит upstream).\n\n")
    fp.write("| Прогон | base..head | files | tests | prompt | completion | сек | tests_cached |\n")
    fp.write("|--------|-----------|------:|------:|-------:|-----------:|----:|-------------:|\n")
    descrs = {
        "A-cold":       "de7178d..525206d (cold)",
        "B-warm-same":  "de7178d..525206d (warm, same)",
        "C-warm-next":  "525206d..db9d1d0 (warm, next-commit)",
    }
    for lbl, r in rows:
        d_ = descrs.get(lbl, lbl)
        if r is None:
            fp.write(f"| {lbl} | {d_} | — | — | — | — | — | — |\n")
            continue
        def fm(v): return str(v) if v is not None else "—"
        fp.write(
            f"| {lbl} | {d_} | {fm(r['files_processed'])} | {fm(r['tests_validated'])} "
            f"| {fm(r['prompt_tokens'])} | {fm(r['completion_tokens'])} "
            f"| {fm(r['duration_seconds'])} | {fm(r['tests_cached'])} |\n"
        )
print(f"\nWrote markdown summary: {md}")
PY

echo
echo "Done. Results in $OUT_DIR"
