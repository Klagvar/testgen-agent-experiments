#!/usr/bin/env python3
"""Pretty-print Qwen 7B rerun metrics for cobra+toml."""
import json
import os
import glob
import sys

base = sys.argv[1] if len(sys.argv) > 1 else "."
os.chdir(base)

print(f"{'repo':<18} {'config':<24} {'r':<2} {'files':>5} {'gen':>4} {'val':>4} {'branch%':>8} {'diff%':>6} {'tokens':>7}")
print("─" * 90)

for repo in ["spf13-cobra", "burntsushi-toml"]:
    for f in sorted(glob.glob(f"{repo}/*-run*.json")):
        d = json.load(open(f))
        t = d.get("totals", {})
        name = os.path.basename(f).replace(".json", "")
        cfg, run = name.rsplit("-run", 1)
        tokens = t.get("prompt_tokens", 0) + t.get("completion_tokens", 0)
        bcov = t.get("branch_coverage_pct", "")
        dcov = t.get("diff_coverage_pct", "")
        print(f"{repo:<18} {cfg:<24} {run:<2} "
              f"{t.get('files_processed',0):>5} "
              f"{t.get('tests_generated',0):>4} "
              f"{t.get('tests_validated',0):>4} "
              f"{str(bcov):>8} {str(dcov):>6} {tokens:>7}")

print()
print("═══ Сводка: успешные прогоны (validated > 0) ═══")
for repo in ["spf13-cobra", "burntsushi-toml"]:
    succ = total = 0
    sum_b = sum_d = 0.0
    nb = nd = 0
    for f in glob.glob(f"{repo}/*-run*.json"):
        d = json.load(open(f))
        t = d.get("totals", {})
        total += 1
        if t.get("tests_validated", 0) > 0:
            succ += 1
        if isinstance(t.get("branch_coverage_pct"), (int, float)):
            sum_b += t["branch_coverage_pct"]; nb += 1
        if isinstance(t.get("diff_coverage_pct"), (int, float)):
            sum_d += t["diff_coverage_pct"]; nd += 1
    avg_b = f"{sum_b/nb:.1f}%" if nb else "—"
    avg_d = f"{sum_d/nd:.1f}%" if nd else "—"
    print(f"  {repo}: {succ}/{total} run валидных | avg branch={avg_b} | avg diff={avg_d}")
