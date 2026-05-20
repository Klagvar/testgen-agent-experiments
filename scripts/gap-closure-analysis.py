#!/usr/bin/env python3
"""Does our agent narrow the capability gap between weak and strong LLMs?

Use no-pruning as the proxy for "bare-LLM-like" baseline (it's the
single most-removable-component, and without pruner the agent essentially
ships whatever the LLM wrote without the AST-aware filtering that defines
the agent's edge over a thin wrapper).

For each model compute:
  Δ_abs   = success(full) - success(no-pruning)         absolute gain
  Δ_rel   = success(full) / max(success(no-pruning), 1) relative multiplier
  qual    = qualitative tier change (useless/marginal/usable/strong/excellent)
"""
import glob
import json
import os
from collections import Counter, defaultdict

models = [
    ("Qwen 2.5 7B (floor)", "результаты/raw/qwen-qwen-2.5-7b-instruct"),
    ("Qwen 30B",           "результаты/raw/qwen-qwen3-coder-30b-a3b-instruct"),
    ("Llama 70B",          "результаты/raw/meta-llama-llama-3.3-70b-instruct"),
    ("DeepSeek V3",        "результаты/raw/deepseek-deepseek-chat"),
    ("GPT-4o-mini",        "результаты/raw/openai-gpt-4o-mini"),
    ("Claude 3.5 Haiku",   "результаты/raw/anthropic-claude-3.5-haiku"),
    ("Gemini 3 Flash",     "результаты/raw/google-gemini-3-flash-preview"),
]

def cfg_success(mdir, cfg):
    succ = total = 0
    for f in glob.glob(os.path.join(mdir, "*/*-run*.json")):
        d = json.load(open(f, encoding="utf-8"))
        if d.get("config", {}).get("ablation_config") != cfg:
            continue
        total += 1
        if d.get("totals", {}).get("tests_validated", 0) > 0:
            succ += 1
    return succ, total

def tier(pct):
    if pct < 5: return "useless"
    if pct < 25: return "marginal"
    if pct < 50: return "usable"
    if pct < 80: return "strong"
    return "excellent"

print("="*100)
print("GAP CLOSURE ANALYSIS — does the agent narrow the capability gap?")
print("(using `no-pruning` ablation as proxy for bare-LLM baseline)")
print("="*100)
print()
print(f"{'model':<22} {'no-prune':>10} {'full':>8} {'Δ p.p.':>8} {'×ratio':>8} {'tier change':>30}")
print("─"*100)

results = []
for tag, mdir in models:
    s_np, t_np = cfg_success(mdir, "no-pruning")
    s_fl, t_fl = cfg_success(mdir, "full")
    pct_np = s_np / max(t_np, 1) * 100
    pct_fl = s_fl / max(t_fl, 1) * 100
    delta = pct_fl - pct_np
    ratio = pct_fl / pct_np if pct_np > 0 else float('inf')
    t_np_name = tier(pct_np)
    t_fl_name = tier(pct_fl)
    arrow = "→" if t_np_name != t_fl_name else "="
    transition = f"{t_np_name} {arrow} {t_fl_name}"
    ratio_str = "∞" if ratio == float('inf') else f"{ratio:.1f}×"
    print(f"{tag:<22} {pct_np:>9.1f}% {pct_fl:>7.1f}% {delta:>+7.1f} {ratio_str:>8} {transition:>30}")
    results.append((tag, pct_np, pct_fl, delta, ratio))

print()
print("="*100)
print("SPREAD ANALYSIS — does the gap between best and worst widen or narrow?")
print("="*100)
np_scores = [r[1] for r in results]
fl_scores = [r[2] for r in results]
print(f"  no-pruning spread:  min={min(np_scores):.1f} %  max={max(np_scores):.1f} %  spread={max(np_scores)-min(np_scores):.1f} p.p.")
print(f"  full-agent spread:  min={min(fl_scores):.1f} %  max={max(fl_scores):.1f} %  spread={max(fl_scores)-min(fl_scores):.1f} p.p.")
print(f"  Δ spread:           {(max(fl_scores)-min(fl_scores)) - (max(np_scores)-min(np_scores)):+.1f} p.p.")
print()
print("Interpretation guide:")
print("- positive Δ spread = gap WIDENS (agent helps strong more than weak)")
print("- negative Δ spread = gap NARROWS (agent equalizes; ideal for 'democratization' claim)")
print("- zero spread       = agent uniformly amplifies all models")

print()
print("="*100)
print("RELATIVE AMPLIFICATION RANKING")
print("="*100)
print("Which models gain the most from the agent harness, in absolute and relative terms?")
print()
print("By absolute Δ (p.p.):")
for tag, np_, fl, delta, ratio in sorted(results, key=lambda x: -x[3]):
    print(f"  {tag:<22} +{delta:.1f} p.p.  ({np_:.1f}% → {fl:.1f}%)")
print()
print("By relative ratio:")
for tag, np_, fl, delta, ratio in sorted(results, key=lambda x: -ratio if x[1] > 0 else float('-inf')):
    rs = "∞" if ratio == float('inf') else f"{ratio:.1f}×"
    print(f"  {tag:<22} {rs:>6}  ({np_:.1f}% → {fl:.1f}%)")
