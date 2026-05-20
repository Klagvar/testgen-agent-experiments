#!/usr/bin/env python3
"""Diagnostic: why is success rate < 100% on GPT-4o-mini?

Three angles:
1. Per-config breakdown (which ablation lever fails more?)
2. Without spf13-cobra (which we already know is universally hard)
3. Sample failed runs to see what's actually wrong with the LLM output
"""
import glob
import json
import os
from collections import defaultdict

models = [
    ("Qwen 7B", "результаты/raw/qwen-qwen-2.5-7b-instruct"),
    ("Qwen 30B", "результаты/raw/qwen-qwen3-coder-30b-a3b-instruct"),
    ("Llama 70B", "результаты/raw/meta-llama-llama-3.3-70b-instruct"),
    ("GPT-4o-mini", "результаты/raw/openai-gpt-4o-mini"),
]

# ─── 1. Per-config success rate ──────────────────────────────────────
print("=== 1. Success rate per ablation config (excluding cobra) ===")
print()
for tag, dn in models:
    by_cfg = defaultdict(lambda: [0, 0])  # config -> [success, total]
    for f in glob.glob(os.path.join(dn, "*/*-run*.json")):
        repo = os.path.basename(os.path.dirname(f))
        if repo == "spf13-cobra":
            continue
        d = json.load(open(f, encoding="utf-8"))
        t = d.get("totals", {})
        cfg = d.get("config", {}).get("ablation_config", "?")
        by_cfg[cfg][1] += 1
        if t.get("tests_validated", 0) > 0:
            by_cfg[cfg][0] += 1
    print(f"  {tag}:")
    for cfg in sorted(by_cfg):
        s, t = by_cfg[cfg]
        print(f"    {cfg:25} {s:>2}/{t:>2} ({s/t*100:>5.1f}%)")
    print()

# ─── 2. Drop cobra ────────────────────────────────────────────────────
print("=== 2. Aggregate WITH vs WITHOUT spf13-cobra ===")
print()
print(f"  {'model':<14} {'with':>14} {'without':>14}")
for tag, dn in models:
    s_all = t_all = s_nc = t_nc = 0
    for f in glob.glob(os.path.join(dn, "*/*-run*.json")):
        repo = os.path.basename(os.path.dirname(f))
        d = json.load(open(f, encoding="utf-8"))
        v = d.get("totals", {}).get("tests_validated", 0)
        t_all += 1
        if v > 0:
            s_all += 1
        if repo != "spf13-cobra":
            t_nc += 1
            if v > 0:
                s_nc += 1
    p_all = s_all / t_all * 100
    p_nc = s_nc / t_nc * 100
    print(f"  {tag:<14} {s_all:>3}/{t_all:>3} ({p_all:>5.1f}%) {s_nc:>3}/{t_nc:>3} ({p_nc:>5.1f}%)")
print()

# ─── 3. Status breakdown ─────────────────────────────────────────────
print("=== 3. Per-file status (across all models) — где именно теряем тесты? ===")
print()
print(f"  {'model':<14} {'success':>9} {'partial':>9} {'failed':>9} {'total':>9}")
for tag, dn in models:
    counts = defaultdict(int)
    for f in glob.glob(os.path.join(dn, "*/*-run*.json")):
        d = json.load(open(f, encoding="utf-8"))
        for entry in d.get("files", []):
            counts[entry.get("status", "?")] += 1
    total = sum(counts.values())
    print(f"  {tag:<14} "
          f"{counts['success']:>4} ({counts['success']/total*100:>4.1f}%) "
          f"{counts['partial']:>4} ({counts['partial']/total*100:>4.1f}%) "
          f"{counts['failed']:>4} ({counts['failed']/total*100:>4.1f}%) "
          f"{total:>9}")
print()

# ─── 4. Timeouts — есть ли подозрение на timeout-cutoff ──────────────
print("=== 4. Подозрение на timeout: длительность одного запуска ===")
print()
print(f"  {'model':<14} {'медиана (s)':>11} {'p95':>6} {'p99':>6} {'max':>6}")
import statistics

for tag, dn in models:
    durations = []
    for f in glob.glob(os.path.join(dn, "*/repo.json")):
        d = json.load(open(f, encoding="utf-8"))
        for run in d.get("runs", []):
            durations.append(run.get("duration", 0) / 1e9)
    durations.sort()
    if not durations:
        continue
    n = len(durations)
    med = statistics.median(durations)
    p95 = durations[int(n * 0.95)]
    p99 = durations[min(n - 1, int(n * 0.99))]
    mx = durations[-1]
    print(f"  {tag:<14} {med:>11.1f} {p95:>6.1f} {p99:>6.1f} {mx:>6.1f}")
