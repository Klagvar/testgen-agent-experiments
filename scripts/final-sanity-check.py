#!/usr/bin/env python3
"""Pre-thesis-writing sanity check: are all models complete on all 8
repos × 6 ablation configs × 3 runs?"""
import json, glob, os
from collections import defaultdict, Counter

EXPECTED_REPOS = {
    "burntsushi-toml", "etcd-io-bbolt", "gin-gonic-gin", "google-uuid",
    "gorilla-mux", "hashicorp-raft", "restic-restic", "spf13-cobra",
}
EXPECTED_CONFIGS = {
    "full", "no-coverage", "no-pruning", "no-smart-diff",
    "no-structured-feedback", "no-types",
}
EXPECTED_RUNS = 3

models = sorted(os.listdir("результаты/raw"))
models = [m for m in models if os.path.isdir(os.path.join("результаты/raw", m))]

print(f"Found {len(models)} models in результаты/raw/")
print(f"Expected per model: {len(EXPECTED_REPOS)} repos × {len(EXPECTED_CONFIGS)} configs × {EXPECTED_RUNS} runs = {len(EXPECTED_REPOS)*len(EXPECTED_CONFIGS)*EXPECTED_RUNS} runs")
print("=" * 100)

global_ok = True
for m in models:
    mdir = os.path.join("результаты/raw", m)
    print(f"\n── {m} ──")
    found_repos = set()
    repo_cfg_runs = defaultdict(lambda: defaultdict(set))
    bad_jsons = []
    for f in glob.glob(os.path.join(mdir, "*/*-run*.json")):
        repo = os.path.basename(os.path.dirname(f))
        found_repos.add(repo)
        fname = os.path.basename(f)
        # Parse cfg-run<N>.json
        cfg, _, run = fname.rsplit("-run", 1)[0], None, fname.rsplit("-run", 1)[1].split(".")[0]
        cfg = fname.rsplit("-run", 1)[0]
        try:
            run_idx = int(run)
        except ValueError:
            run_idx = -1
        repo_cfg_runs[repo][cfg].add(run_idx)
        try:
            d = json.load(open(f, encoding="utf-8"))
            if "totals" not in d:
                bad_jsons.append((f, "no totals"))
        except Exception as e:
            bad_jsons.append((f, str(e)[:50]))

    missing_repos = EXPECTED_REPOS - found_repos
    extra_repos = found_repos - EXPECTED_REPOS
    if missing_repos:
        print(f"  ❌ MISSING REPOS: {missing_repos}")
        global_ok = False
    if extra_repos:
        print(f"  ⚠️  EXTRA REPOS: {extra_repos}")

    issues = 0
    total_runs = 0
    for repo in sorted(EXPECTED_REPOS):
        if repo not in found_repos:
            continue
        for cfg in sorted(EXPECTED_CONFIGS):
            runs = repo_cfg_runs[repo].get(cfg, set())
            total_runs += len(runs)
            if len(runs) != EXPECTED_RUNS:
                print(f"  ❌ {repo}/{cfg}: only {len(runs)} runs ({sorted(runs)}), expected {EXPECTED_RUNS}")
                issues += 1
                global_ok = False
            elif runs != {1, 2, 3}:
                print(f"  ⚠️  {repo}/{cfg}: runs are {sorted(runs)} not {{1,2,3}}")
                issues += 1
                global_ok = False
    if bad_jsons:
        print(f"  ❌ BAD JSON FILES ({len(bad_jsons)}):")
        for f, err in bad_jsons[:5]:
            print(f"      {f}: {err}")
        global_ok = False

    if issues == 0 and not bad_jsons and not missing_repos:
        print(f"  ✅ {len(found_repos)}/{len(EXPECTED_REPOS)} repos × {len(EXPECTED_CONFIGS)} configs × {EXPECTED_RUNS} runs = {total_runs} runs (clean)")

print()
print("=" * 100)
if global_ok:
    print("✅ ALL MODELS COMPLETE — ready for thesis writing")
else:
    print("❌ SOME ISSUES FOUND — see above")
