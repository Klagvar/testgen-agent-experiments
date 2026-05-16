#!/usr/bin/env python3
"""Cross-model comparison table."""
import json
import glob
import os
import sys

import sys

# Auto-discover all model directories under результаты/raw/
HUMAN_NAMES = {
    "qwen-qwen-2.5-7b-instruct": "Qwen 2.5 7B (floor)",
    "qwen-qwen3-coder-30b-a3b-instruct": "Qwen3-Coder-30B-A3B",
    "meta-llama-llama-3.3-70b-instruct": "Llama 3.3 70B",
    "openai-gpt-4o-mini": "GPT-4o-mini",
    "deepseek-deepseek-chat": "DeepSeek-chat",
    "anthropic-claude-3.5-haiku": "Claude 3.5 Haiku",
    "google-gemini-3-flash-preview": "Gemini 3 Flash",
}
# claude-haiku-4.5 был запущен, но исключён из основной выборки из-за
# configuration trap (max_tokens=4096 строго соблюдается Anthropic native
# и обрезает ответы посреди composite literal). Подробнее:
# результаты/НАБЛЮДЕНИЯ.md → "Configuration trap".

raw_root = "результаты/raw"
if not os.path.isdir(raw_root):
    sys.exit(f"{raw_root} not found — run this from the repo root")

models = []
for d in sorted(os.listdir(raw_root)):
    full = os.path.join(raw_root, d)
    if os.path.isdir(full):
        label = HUMAN_NAMES.get(d, d)
        models.append((label, full))

def stats(model_dir):
    runs_succ = 0
    runs_total = 0
    val_tests = 0
    pin = pcomp = 0
    durs = 0
    for f in glob.glob(os.path.join(model_dir, "*/repo.json")):
        d = json.load(open(f, encoding="utf-8"))
        durs += d.get("duration", 0)
    for f in glob.glob(os.path.join(model_dir, "*/*-run*.json")):
        d = json.load(open(f, encoding="utf-8"))
        t = d.get("totals", {})
        v = t.get("tests_validated", 0)
        runs_total += 1
        val_tests += v
        if v > 0:
            runs_succ += 1
        pin += t.get("prompt_tokens", 0)
        pcomp += t.get("completion_tokens", 0)
    return runs_succ, runs_total, val_tests, pin, pcomp, durs / 1e9

print(f"{'model':<25} {'успешных runs':>14} {'тестов':>8} {'prompt tok':>13} {'compl tok':>12} {'часы':>7}")
print("-" * 85)
for m, d in models:
    s = stats(d)
    pct = s[0] / s[1] * 100
    print(
        f"{m:<25} {s[0]:>3}/{s[1]:>3} ({pct:>4.1f}%)  "
        f"{s[2]:>8} {s[3]:>13,} {s[4]:>12,} {s[5]/3600:>7.2f}"
    )
