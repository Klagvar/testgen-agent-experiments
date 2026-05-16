#!/usr/bin/env python3
"""Estimate cost to finish 4.5-haiku rerun.

Uses old-run (cap=4096) per-repo costs and applies the observed
inflation factor (new tokens / old tokens) on the 3 already-finished
shared repos."""
import json, glob, os
from collections import Counter

OLD = "результаты/raw/anthropic-claude-haiku-4.5_OLD-cap4096"
NEW = "результаты/raw/anthropic-claude-haiku-4.5"
PRICE_IN, PRICE_OUT = 1.0/1e6, 5.0/1e6

def collect(mdir):
    per_repo = Counter()
    runs = Counter()
    cost = Counter()
    for f in glob.glob(os.path.join(mdir, "*/*-run*.json")):
        repo = os.path.basename(os.path.dirname(f))
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        t = d.get("totals", {})
        runs[repo] += 1
        per_repo[repo] += 1
        cost[repo] += t.get("prompt_tokens", 0) * PRICE_IN + t.get("completion_tokens", 0) * PRICE_OUT
    return runs, cost

old_runs, old_cost = collect(OLD)
new_runs, new_cost = collect(NEW)

shared = sorted(set(old_runs) & set(new_runs))
remaining = sorted(set(old_runs) - set(new_runs))
partial = [r for r in set(old_runs) & set(new_runs) if new_runs[r] < old_runs[r]]

print(f"{'repo':<25} {'OLD runs':>9} {'OLD cost':>9} {'NEW runs':>9} {'NEW cost':>9} {'inflation':>11}")
print("─" * 80)
inflation_factors = []
for repo in shared:
    if new_runs[repo] >= old_runs[repo]:
        infl = (new_cost[repo] / new_runs[repo]) / (old_cost[repo] / old_runs[repo])
        inflation_factors.append(infl)
        print(f"{repo:<25} {old_runs[repo]:>9} ${old_cost[repo]:>7.2f} {new_runs[repo]:>9} ${new_cost[repo]:>7.2f} {infl:>10.1f}x")

avg_infl = sum(inflation_factors)/len(inflation_factors) if inflation_factors else 1.0
print(f"\nAverage inflation factor (NEW/OLD per-run cost): {avg_infl:.1f}×")
print()

remaining_cost = 0
print(f"{'repo':<25} {'OLD cost':>9} {'projected NEW':>14}")
print("─" * 55)
for repo in remaining:
    proj = old_cost[repo] * avg_infl
    remaining_cost += proj
    print(f"{repo:<25} ${old_cost[repo]:>7.2f} ${proj:>12.2f}")

# Partial: gin-gonic-gin (1/18 done)
for repo in partial:
    done = new_runs[repo]
    todo = old_runs[repo] - done
    proj = old_cost[repo] * (todo/old_runs[repo]) * avg_infl
    remaining_cost += proj
    print(f"{repo+f' ({todo}/{old_runs[repo]} left)':<25} ${old_cost[repo]*todo/old_runs[repo]:>7.2f} ${proj:>12.2f}")

print("─" * 55)
print(f"{'TOTAL TO FINISH':<25}             ${remaining_cost:>12.2f}")
print()
print(f"With 30% safety margin:    ${remaining_cost*1.3:.2f}")
