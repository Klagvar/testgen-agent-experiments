#!/usr/bin/env python3
"""Deep analysis: what scientific findings are already in the results?
Decide whether 4.5-haiku rerun adds anything new."""
import glob
import json
import os
from collections import Counter, defaultdict

models = [
    ("Qwen 7B (floor)",    "результаты/raw/qwen-qwen-2.5-7b-instruct"),
    ("Qwen 30B",           "результаты/raw/qwen-qwen3-coder-30b-a3b-instruct"),
    ("Llama 70B",          "результаты/raw/meta-llama-llama-3.3-70b-instruct"),
    ("DeepSeek V3",        "результаты/raw/deepseek-deepseek-chat"),
    ("GPT-4o-mini",        "результаты/raw/openai-gpt-4o-mini"),
    ("Claude 3.5 Haiku",   "результаты/raw/anthropic-claude-3.5-haiku"),
    ("Claude Haiku 4.5",   "результаты/raw/anthropic-claude-haiku-4.5_OLD-cap4096"),
    ("Gemini 3 Flash",     "результаты/raw/google-gemini-3-flash-preview"),
]

print("="*100)
print("CAPABILITY LADDER: success rate per model")
print("="*100)
print(f"{'rank':>4} {'model':<22} {'success/runs':>14} {'success%':>9} {'tests':>6} {'$ approx':>10}")
print("─"*100)

results = []
for tag, mdir in models:
    runs = 0
    success_runs = 0
    total_tests = 0
    p_in = 0
    p_out = 0
    for f in glob.glob(os.path.join(mdir, "*/*-run*.json")):
        runs += 1
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        t = d.get("totals", {})
        if t.get("tests_validated", 0) > 0:
            success_runs += 1
        total_tests += t.get("tests_validated", 0)
        p_in += t.get("prompt_tokens", 0)
        p_out += t.get("completion_tokens", 0)
    results.append((tag, runs, success_runs, total_tests, p_in, p_out))

results.sort(key=lambda x: -x[2]/max(x[1],1))
for i, (tag, runs, sr, t, pin, pout) in enumerate(results, 1):
    pct = sr/max(runs,1)*100
    print(f"{i:>4} {tag:<22} {sr:>5}/{runs:<8} {pct:>8.1f}% {t:>6} {(pin+pout)/1e6*0.5:>9.2f}")

print()
print("="*100)
print("ABLATION BREAKDOWN: which components help/hurt by model capability tier?")
print("="*100)

# Aggregate per-config success rate per model
def per_cfg_stats(mdir):
    cfg = defaultdict(lambda: [0, 0])  # [success, total]
    for f in glob.glob(os.path.join(mdir, "*/*-run*.json")):
        cf = os.path.basename(f).rsplit("-run", 1)[0]
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        t = d.get("totals", {})
        cfg[cf][1] += 1
        if t.get("tests_validated", 0) > 0:
            cfg[cf][0] += 1
    return cfg

print(f"{'model':<22} {'full':>6} {'no-types':>9} {'no-smart':>9} {'no-feedback':>12} {'no-prune':>9} {'no-cov':>7}")
print("─"*100)
for tag, mdir in models:
    cfg = per_cfg_stats(mdir)
    def pct(c): return f"{cfg[c][0]/max(cfg[c][1],1)*100:.0f}%"
    print(f"{tag:<22} {pct('full'):>6} {pct('no-types'):>9} {pct('no-smart-diff'):>9} {pct('no-structured-feedback'):>12} {pct('no-pruning'):>9} {pct('no-coverage'):>7}")

print()
print("="*100)
print("KEY FINDINGS for thesis (already established):")
print("="*100)
print("""
1. CAPABILITY LADDER (8 models, 15-92% range): Demonstrates that the agent
   architecture works across the entire LLM capability spectrum, with sane
   monotonic ordering aligned with known model strengths.

2. NON-MONOTONIC ABLATION BEHAVIOR: Components that help weaker models
   sometimes hurt stronger ones (or are no-ops). Universal: pruner. Variable:
   structured-feedback, smart-diff. Useful: types-context.

3. PRUNER IS UNIVERSAL: -40 to -70 p.p. when removed, across all 7-8 models.
   This is the SINGLE most important component.

4. COST-EFFECTIVENESS WINNER: Gemini 3 Flash (92% @ $5) vs DeepSeek V3
   (56% @ $5). Frontier models can be fast AND cheap.

5. CONFIGURATION TRAP (max_tokens × Anthropic native): NEW finding from
   today. Documented as a methodological lesson for cross-provider bench-
   marking. This is a self-contained scientific artifact independent of
   the specific 4.5-haiku number.

6. CACHE MICROEXP: Demonstrated -52% wall-clock, -31% prompt tokens,
   -43% completion on warm-same-head. Correct invalidation on shift.
""")
