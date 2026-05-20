#!/usr/bin/env python3
"""Variance: how stable are results across 3 independent runs?

For each (model, repo, config), the 3 runs use seed = 42 + run_index. With
temperature=0 we expect mostly deterministic behaviour, BUT some providers
introduce non-determinism (batching, retries, internal sampling).

We compute std-dev of file_success_rate across 3 runs for each (model,repo,config),
then aggregate.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import CONFIGS, MODELS, REPOS, collect  # type: ignore


def main() -> None:
    rows = collect()
    # group by (model, repo, config) -> list of file_success_rate from 3 runs
    grp = defaultdict(list)
    for r in rows:
        if r["files_processed"] > 0:
            rate = r["files_successful"] / r["files_processed"] * 100
        else:
            rate = 0.0
        grp[(r["model_id"], r["repo"], r["config"])].append(rate)

    # For each model, mean of std-devs across (repo, config) groups
    print()
    print("=== Stability across 3 runs per (model, repo, config) ===")
    print(f"{'Model':<26}{'mean σ':>10}{'max σ':>10}{'identical %':>14}{'groups':>9}")
    print("-" * 70)
    for raw_dir, sid, lbl in MODELS:
        sigmas = []
        identical = 0
        total_groups = 0
        for repo in REPOS:
            for cfg in CONFIGS:
                vals = grp.get((sid, repo, cfg), [])
                if len(vals) >= 2:
                    s = stdev(vals)
                    sigmas.append(s)
                    if s == 0:
                        identical += 1
                    total_groups += 1
        mean_s = mean(sigmas) if sigmas else 0
        max_s = max(sigmas) if sigmas else 0
        pct_id = identical / total_groups * 100 if total_groups else 0
        print(f"{lbl:<26}{mean_s:>9.1f}{max_s:>10.1f}{pct_id:>13.0f}%{total_groups:>9d}")

    # Most variable cases (top 10 globally)
    print()
    print("=== Top-10 most variable (model, repo, config) ===")
    items = []
    for (sid, repo, cfg), vals in grp.items():
        if len(vals) >= 2:
            s = stdev(vals)
            if s > 0:
                items.append((s, sid, repo, cfg, vals))
    items.sort(key=lambda x: -x[0])
    for s, sid, repo, cfg, vals in items[:10]:
        print(f"  σ={s:.1f}  {sid:<14}{repo:<22}{cfg:<22}runs={vals}")

    # Variance by ablation
    print()
    print("=== Mean σ by config (averaged across models and repos) ===")
    for cfg in CONFIGS:
        vals = []
        for raw_dir, sid, lbl in MODELS:
            for repo in REPOS:
                runs = grp.get((sid, repo, cfg), [])
                if len(runs) >= 2:
                    vals.append(stdev(runs))
        m = mean(vals) if vals else 0
        print(f"  {cfg:<24}  mean σ = {m:.1f} pp")


if __name__ == "__main__":
    main()
