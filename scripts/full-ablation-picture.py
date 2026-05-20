#!/usr/bin/env python3
"""Full ablation picture for GPT-4o-mini: success rate is just one metric.
We also need to look at branch coverage, diff coverage, tokens spent
(cost-efficiency), and total tests generated."""
import glob
import json
import os
from collections import defaultdict

models = [
    ("Qwen 7B (floor)", "результаты/raw/qwen-qwen-2.5-7b-instruct"),
    ("Qwen 30B", "результаты/raw/qwen-qwen3-coder-30b-a3b-instruct"),
    ("Llama 70B", "результаты/raw/meta-llama-llama-3.3-70b-instruct"),
    ("GPT-4o-mini", "результаты/raw/openai-gpt-4o-mini"),
    ("DeepSeek V3", "результаты/raw/deepseek-deepseek-chat"),
    ("Claude 3.5 Haiku", "результаты/raw/anthropic-claude-3.5-haiku"),
    ("Gemini 3 Flash", "результаты/raw/google-gemini-3-flash-preview"),
    # claude-haiku-4.5 был запущен, но из-за обнаруженной configuration trap
    # (max_tokens=4096 + Anthropic native API строго соблюдает лимит) его
    # результаты систематически занижены и не годятся для cross-model сравнения.
    # Подробности в результаты/НАБЛЮДЕНИЯ.md (раздел Configuration trap).
]

CONFIGS = ["full", "no-coverage", "no-pruning", "no-smart-diff",
           "no-structured-feedback", "no-types"]


def stats_for_config(model_dir, config):
    succ = total = 0
    tests = 0
    bcov = dcov = []
    bcov = []
    dcov = []
    prompt_tok = compl_tok = 0
    for f in glob.glob(os.path.join(model_dir, "*/*-run*.json")):
        repo = os.path.basename(os.path.dirname(f))
        if repo == "spf13-cobra":
            continue
        d = json.load(open(f, encoding="utf-8"))
        cfg = d.get("config", {}).get("ablation_config")
        if cfg != config:
            continue
        t = d.get("totals", {})
        total += 1
        v = t.get("tests_validated", 0)
        tests += v
        if v > 0:
            succ += 1
        b = t.get("branch_coverage_pct")
        dc = t.get("diff_coverage_pct")
        if isinstance(b, (int, float)):
            bcov.append(b)
        if isinstance(dc, (int, float)):
            dcov.append(dc)
        prompt_tok += t.get("prompt_tokens", 0)
        compl_tok += t.get("completion_tokens", 0)
    return {
        "success_rate": succ / total * 100 if total else 0,
        "n_succ": succ, "n_total": total,
        "tests": tests,
        "branch": sum(bcov) / len(bcov) if bcov else None,
        "diff": sum(dcov) / len(dcov) if dcov else None,
        "tokens_total": prompt_tok + compl_tok,
    }


print("Все цифры — без spf13-cobra (универсально трудный target, 0-3 успехов у всех)")
print("Каждая клетка: success% / branch% / diff% / тестов / токенов")
print()

for tag, dn in models:
    print(f"=== {tag} ===")
    base = stats_for_config(dn, "full")
    print(f"  {'config':<25} {'succ%':>6} {'branch%':>7} {'diff%':>6} "
          f"{'тестов':>7} {'токенов':>9} {'vs full':>10}")
    for cfg in CONFIGS:
        s = stats_for_config(dn, cfg)
        b = f"{s['branch']:.1f}" if s['branch'] is not None else "—"
        dc = f"{s['diff']:.1f}" if s['diff'] is not None else "—"
        if cfg == "full":
            delta = ""
        else:
            d_succ = s['success_rate'] - base['success_rate']
            d_brn = (s['branch'] or 0) - (base['branch'] or 0)
            delta = f"Δsucc={d_succ:+.0f}pp"
            if base['branch'] and s['branch']:
                delta += f", Δbranch={d_brn:+.0f}"
        print(f"  {cfg:<25} {s['success_rate']:>6.1f} {b:>7} {dc:>6} "
              f"{s['tests']:>7} {s['tokens_total']:>9,} {delta:>20}")
    print()
