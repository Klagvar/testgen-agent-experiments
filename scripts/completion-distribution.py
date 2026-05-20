#!/usr/bin/env python3
"""Per-call completion token distribution.

Each agent run consists of 1..3 LLM calls (initial + up to 2 retries).
The JSON report aggregates them into a single completion_tokens field;
to detect 4096-token caps we need attempt-level data which is only in
the log file. As a proxy: distribution of total per-run completion
tokens, bucketed by 4096-multiples."""
import glob
import json
import os
from collections import Counter

models = [
    ("3.5-haiku",     "результаты/raw/anthropic-claude-3.5-haiku"),
    ("4.5-haiku",     "результаты/raw/anthropic-claude-haiku-4.5"),
    ("gpt-4o-mini",   "результаты/raw/openai-gpt-4o-mini"),
    ("gemini-3-flash","результаты/raw/google-gemini-3-flash-preview"),
    ("deepseek-v3",   "результаты/raw/deepseek-deepseek-chat"),
    ("llama-70b",     "результаты/raw/meta-llama-llama-3.3-70b-instruct"),
    ("qwen-30b",      "результаты/raw/qwen-qwen3-coder-30b-a3b-instruct"),
]

def bucket(c):
    if c == 0: return "0"
    if c < 1024: return "<1k"
    if c < 4096: return "1-4k"
    if c == 4096: return "EXACTLY 4096"
    if c < 8192: return "4k-8k"
    if c == 8192: return "EXACTLY 8192"
    if c < 12288: return "8k-12k"
    if c == 12288: return "EXACTLY 12288"
    if c < 16384: return "12k-16k"
    return ">=16k"

print(f"{'model':<18} {'<1k':>5} {'1-4k':>6} {'4k-8k':>6} {'8k-12k':>7} {'12k-16k':>8} {'>=16k':>6} | exact=4096 | exact=12288")
print("─" * 105)
for tag, mdir in models:
    buckets = Counter()
    for f in glob.glob(os.path.join(mdir, "*/*-run*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        c = d.get("totals", {}).get("completion_tokens", 0)
        buckets[bucket(c)] += 1
    print(f"{tag:<18} "
          f"{buckets['<1k']+buckets['0']:>5} "
          f"{buckets['1-4k']:>6} "
          f"{buckets['4k-8k']:>6} "
          f"{buckets['8k-12k']:>7} "
          f"{buckets['12k-16k']:>8} "
          f"{buckets['>=16k']:>6} "
          f"| {buckets['EXACTLY 4096']:>9} | {buckets['EXACTLY 12288']:>10}")
