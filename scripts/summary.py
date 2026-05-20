#!/usr/bin/env python3
"""Pretty-print a per-config summary of one repo's smoke results.

Usage: python3 summary.py <results-dir> [<prompt-usd-per-m> <compl-usd-per-m>]
"""
import glob
import json
import os
import sys

if len(sys.argv) < 2:
    print(__doc__, file=sys.stderr); sys.exit(1)
d = sys.argv[1]
PROMPT_USD_PER_M = float(sys.argv[2]) if len(sys.argv) > 2 else 0.04
COMPL_USD_PER_M  = float(sys.argv[3]) if len(sys.argv) > 3 else 0.10

reports = sorted(p for p in glob.glob(os.path.join(d, "*.json"))
                 if os.path.basename(p) != "repo.json")
if not reports:
    print(f"  no JSON reports in {d}", file=sys.stderr); sys.exit(1)

total_p = total_c = 0
total_dur = 0.0
print(f"  {'config':24s} {'prompt':>7s} {'compl':>7s} {'dur,s':>7s} {'status':>10s} {'cost':>8s}")
print(f"  {'-'*24} {'-'*7} {'-'*7} {'-'*7} {'-'*10} {'-'*8}")
for f in reports:
    r = json.load(open(f))
    cfg = r.get("config", {}).get("ablation_config") or os.path.basename(f).replace(".json", "")
    t = r.get("totals", {})
    p = t.get("prompt_tokens", 0)
    c = t.get("completion_tokens", 0)
    dur = r.get("duration_seconds", 0.0)
    fst = r["files"][0]["status"] if r.get("files") else "-"
    cost = p * PROMPT_USD_PER_M / 1e6 + c * COMPL_USD_PER_M / 1e6
    print(f"  {cfg:24s} {p:7d} {c:7d} {dur:7.1f} {fst:>10s}  ${cost:.4f}")
    total_p += p; total_c += c; total_dur += dur

cost = total_p * PROMPT_USD_PER_M / 1e6 + total_c * COMPL_USD_PER_M / 1e6
n = len(reports)
print(f"  {'-'*24} {'-'*7} {'-'*7} {'-'*7}")
print(f"  {'TOTAL':24s} {total_p:7d} {total_c:7d} {total_dur:7.1f}            ${cost:.4f}")
print()
avg_p, avg_c, avg_d = total_p // n, total_c // n, total_dur / n
print(f"  Per-run averages: prompt={avg_p}, completion={avg_c}, duration={avg_d:.1f}s")
print()
full_cube = avg_p * 864 * PROMPT_USD_PER_M / 1e6 + avg_c * 864 * COMPL_USD_PER_M / 1e6
print(f"  Extrapolation to 864-run cube at the same per-token price: ${full_cube:.2f}")
