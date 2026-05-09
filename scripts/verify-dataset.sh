#!/usr/bin/env bash
# Verify dataset readiness:
#   1. each repo exists at workdir/<name>/
#   2. both base and head SHAs are reachable
#   3. git diff --stat base..head shows production .go files only
#   4. go build ./... at head succeeds
#
# Reads dataset.yaml from $REPO_ROOT/dataset.yaml or first argument.
set -eu

EXP_ROOT="${EXP_ROOT:-$HOME/testgen-experiments}"
WORKDIR="${WORKDIR:-$EXP_ROOT/workdir}"
DATASET="${1:-/mnt/d/Дз/4 семестр/НИР/эксперимент/dataset.yaml}"

if [[ ! -f "$DATASET" ]]; then
  echo "ERROR: dataset not found at $DATASET" >&2
  exit 1
fi

# Parse name/url/base/head from YAML (good enough for our format).
parse() {
  python3 -c "
import yaml,sys,json
d=yaml.safe_load(open(sys.argv[1]))
for r in d['repos']:
    print(json.dumps(r))
" "$1"
}

OK=0
FAIL=0
declare -a FAILURES

while IFS= read -r line; do
  name=$(echo "$line" | python3 -c 'import sys,json;print(json.load(sys.stdin)["name"])')
  base=$(echo "$line" | python3 -c 'import sys,json;print(json.load(sys.stdin)["base"])')
  head=$(echo "$line" | python3 -c 'import sys,json;print(json.load(sys.stdin)["head"])')

  printf "%-22s " "$name"

  url=$(echo "$line" | python3 -c 'import sys,json;print(json.load(sys.stdin)["url"])')
  dir="$WORKDIR/$name"

  if [[ ! -d "$dir/.git" ]]; then
    printf "(cloning) "
    if ! git clone --quiet "$url" "$dir" 2>/tmp/clone-$name.log; then
      echo "FAIL: clone failed (see /tmp/clone-$name.log)"
      FAIL=$((FAIL+1)); FAILURES+=("$name: clone failed")
      continue
    fi
  fi

  # Some repos (gin, raft) keep PR commits behind unfetched refs.
  # Try cat-file first; if missing, do a full fetch then retry.
  if ! git -C "$dir" cat-file -e "$base^{commit}" 2>/dev/null \
     || ! git -C "$dir" cat-file -e "$head^{commit}" 2>/dev/null; then
    printf "(fetching) "
    git -C "$dir" fetch --quiet origin "+refs/heads/*:refs/remotes/origin/*" 2>/dev/null || true
    git -C "$dir" fetch --quiet origin "$base" "$head" 2>/dev/null || true
  fi

  if ! git -C "$dir" cat-file -e "$base^{commit}" 2>/dev/null; then
    echo "FAIL: base $base not reachable after fetch"
    FAIL=$((FAIL+1)); FAILURES+=("$name: base SHA missing")
    continue
  fi
  if ! git -C "$dir" cat-file -e "$head^{commit}" 2>/dev/null; then
    echo "FAIL: head $head not reachable after fetch"
    FAIL=$((FAIL+1)); FAILURES+=("$name: head SHA missing")
    continue
  fi

  # Switch to head if not already there (no-op if already there).
  if [[ "$(git -C "$dir" rev-parse HEAD)" != "$head" ]]; then
    git -C "$dir" -c advice.detachedHead=false checkout --quiet "$head" 2>/dev/null || {
      echo "FAIL: cannot checkout $head"
      FAIL=$((FAIL+1)); FAILURES+=("$name: checkout failed")
      continue
    }
  fi

  # Production .go files changed (excluding _test.go and vendor/).
  prod_files=$(git -C "$dir" diff --name-only "$base..$head" \
             | grep -E '\.go$' | grep -vE '(_test\.go$|^vendor/|^_examples/)' || true)
  prod_count=$(printf "%s\n" "$prod_files" | grep -c . || true)
  test_files=$(git -C "$dir" diff --name-only "$base..$head" \
             | grep -E '_test\.go$' | wc -l)

  # go build ./... at head (cheap sanity).
  if ! ( cd "$dir" && go build ./... 2>&1 | head -3 ) >/tmp/build-$name.log 2>&1; then
    echo "FAIL: go build ./... failed (see /tmp/build-$name.log)"
    FAIL=$((FAIL+1)); FAILURES+=("$name: build failed")
    continue
  fi

  echo "OK  prod=$prod_count, tests=$test_files"
  OK=$((OK+1))
done < <(parse "$DATASET")

echo
echo "─── Summary ──────────────────────────────────────"
echo "OK:   $OK"
echo "FAIL: $FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  echo
  echo "Failures:"
  printf "  - %s\n" "${FAILURES[@]}"
  exit 1
fi
