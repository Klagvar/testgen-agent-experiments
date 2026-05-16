#!/usr/bin/env python3
"""Estimate spend on the running 4.5-haiku rerun."""
import json, glob, os
from collections import Counter

mdir = "результаты/raw/anthropic-claude-haiku-4.5"
total_in = 0
total_out = 0
runs = 0
per_repo = Counter()
per_repo_in = Counter()
per_repo_out = Counter()
status_buckets = Counter()
for f in sorted(glob.glob(os.path.join(mdir, "*/*-run*.json"))):
    runs += 1
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    t = d.get("totals", {})
    pin = t.get("prompt_tokens", 0)
    pout = t.get("completion_tokens", 0)
    total_in += pin
    total_out += pout
    repo = os.path.basename(os.path.dirname(f))
    per_repo[repo] += 1
    per_repo_in[repo] += pin
    per_repo_out[repo] += pout
    files = d.get("files") or []
    for fl in files:
        status_buckets[fl.get("status", "?")] += 1

# Anthropic native pricing for claude-haiku-4.5
PRICE_IN = 1.0  / 1_000_000   # $/token (input)
PRICE_OUT = 5.0 / 1_000_000   # $/token (output)
spend = total_in * PRICE_IN + total_out * PRICE_OUT

print(f"Runs done so far: {runs}/144  ({runs/144*100:.0f} %)")
print(f"Prompt tokens:    {total_in:>12,}")
print(f"Completion tokens:{total_out:>12,}")
print(f"Spend (anthropic claude-haiku-4.5 @ $1/$5 per Mtok): ${spend:.2f}")
print()
print("File status across completed runs:")
for k, v in status_buckets.most_common():
    print(f"  {k:<10} {v}")
print()
print("Per-repo runs:")
for repo, n in sorted(per_repo.items()):
    cost = per_repo_in[repo] * PRICE_IN + per_repo_out[repo] * PRICE_OUT
    print(f"  {repo:<25} {n:>3} runs   ${cost:.2f}")
remaining = 144 - runs
if runs > 0:
    avg = spend / runs
    print(f"\nAvg per run: ${avg:.3f}")
    print(f"Remaining {remaining} runs forecast: ~${remaining*avg:.2f}")
