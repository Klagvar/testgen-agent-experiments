#!/usr/bin/env python3
"""Aggregate mutation micro-experiment (7 models × 8 repos × full × 1 run).

Reads all full.json reports under results/mutation-microexp/ and prints:
  1. Per-(model, repo) mutation score table
  2. Per-model summary (median / mean / count of repos with non-zero mutations)
  3. Per-repo summary (which repos generate mutations at all)
  4. List of survived mutants for the thesis appendix
"""
from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MUT_DIR = ROOT / "результаты" / "mutation-microexp"

CANONICAL_MODELS = [
    ("qwen-qwen-2.5-7b-instruct", "Qwen-7B"),
    ("qwen-qwen3-coder-30b-a3b-instruct", "Qwen3-Coder-30B"),
    ("meta-llama-llama-3.3-70b-instruct", "Llama-3.3-70B"),
    ("deepseek-deepseek-chat", "DeepSeek-V3"),
    ("openai-gpt-4o-mini", "GPT-4o-mini"),
    ("anthropic-claude-3.5-haiku", "Claude-3.5-Haiku"),
    ("google-gemini-3-flash-preview", "Gemini-3-Flash"),
]

REPOS = [
    "gorilla-mux",
    "google-uuid",
    "spf13-cobra",
    "burntsushi-toml",
    "gin-gonic-gin",
    "etcd-io-bbolt",
    "hashicorp-raft",
    "restic-restic",
]


def load(model_dir: str, repo: str):
    p = MUT_DIR / model_dir / repo / "full.json"
    if not p.exists():
        return None
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    print("# Mutation micro-experiment: aggregated results")
    print(f"# {len(CANONICAL_MODELS)} models × {len(REPOS)} repos × 1 run × 'full' config")
    print()

    # ── 1. per-(model, repo) score matrix ────────────────────────────────
    print("## Per-(model × repo) mutation score (% killed / total)")
    header = ["Model".ljust(20)] + [r[:13].ljust(13) for r in REPOS]
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(["-" * (len(h) + 2) for h in header]) + "|")

    rows = []
    for model_dir, label in CANONICAL_MODELS:
        cells = [label.ljust(20)]
        for repo in REPOS:
            d = load(model_dir, repo)
            if d is None or d["totals"]["mutations_total"] == 0:
                cells.append("—".ljust(13))
                continue
            killed = d["totals"]["mutations_killed"]
            total = d["totals"]["mutations_total"]
            pct = 100.0 * killed / total if total else 0
            cells.append(f"{pct:5.1f}% ({killed}/{total})".ljust(13))
        print("| " + " | ".join(cells) + " |")
        rows.append((label, model_dir))
    print()

    # ── 2. per-model summary (only non-zero mutations counted) ──────────
    print("## Per-model summary (only repos with mutations_total > 0)")
    print("| Model | n repos | median % | mean % | killed/total (sum) |")
    print("|-------|--------:|---------:|-------:|-------------------:|")
    for model_dir, label in CANONICAL_MODELS:
        scores = []
        sk = st = 0
        for repo in REPOS:
            d = load(model_dir, repo)
            if d is None:
                continue
            total = d["totals"]["mutations_total"]
            killed = d["totals"]["mutations_killed"]
            if total == 0:
                continue
            scores.append(100.0 * killed / total)
            sk += killed
            st += total
        if scores:
            median = statistics.median(scores)
            mean = statistics.mean(scores)
            print(
                f"| {label} | {len(scores)} | {median:.1f} | {mean:.1f} | {sk}/{st} ({100 * sk / st:.1f}%) |"
            )
        else:
            print(f"| {label} | 0 | — | — | 0/0 |")
    print()

    # ── 3. per-repo summary: who actually generates mutants? ────────────
    print("## Per-repo summary (across all 7 models)")
    print("| Repo | n models with muts | median % | range |")
    print("|------|------------------:|---------:|-------|")
    for repo in REPOS:
        scores = []
        for model_dir, _ in CANONICAL_MODELS:
            d = load(model_dir, repo)
            if d is None:
                continue
            total = d["totals"]["mutations_total"]
            if total == 0:
                continue
            scores.append(100.0 * d["totals"]["mutations_killed"] / total)
        if scores:
            print(
                f"| {repo} | {len(scores)} | {statistics.median(scores):.1f} | "
                f"{min(scores):.1f}–{max(scores):.1f} |"
            )
        else:
            print(f"| {repo} | 0 | — | — |")
    print()

    # ── 4. zero-mutation cases ───────────────────────────────────────────
    print("## Cases with zero mutations (test passed but mutation engine produced no mutants)")
    print("| Model | Repo | tests_validated | mutations_total | reason hint |")
    print("|-------|------|----------------:|----------------:|-------------|")
    for model_dir, label in CANONICAL_MODELS:
        for repo in REPOS:
            d = load(model_dir, repo)
            if d is None:
                continue
            tv = d["totals"]["tests_validated"]
            mt = d["totals"]["mutations_total"]
            if mt == 0:
                hint = "validate=0 (no test passed)" if tv == 0 else "no mutable AST in changed lines"
                print(f"| {label} | {repo} | {tv} | {mt} | {hint} |")

    # ── 5. survived mutants (interesting bugs) ──────────────────────────
    print()
    print("## Survived mutants (qualitative — for thesis appendix)")
    for model_dir, label in CANONICAL_MODELS:
        for repo in REPOS:
            d = load(model_dir, repo)
            if d is None:
                continue
            survived = d["totals"]["mutations_total"] - d["totals"]["mutations_killed"]
            if survived > 0:
                print(f"- **{label} × {repo}**: {survived} survived "
                      f"(score {100 * d['totals']['mutations_killed'] / d['totals']['mutations_total']:.1f}%)")


if __name__ == "__main__":
    main()
