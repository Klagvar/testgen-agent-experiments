#!/usr/bin/env python3
"""Ablation matrix: 7 models × 6 configurations.

For each (model, config) we report:
  * file_macro success rate (mean across 8 repos × 3 runs = 24 rows)
  * file_micro success rate (sum of OK files / sum of all files)
  * run_success rate (fraction of 24 runs where validated_tests > 0)
  * delta vs full (file_macro_config - file_macro_full)

Also computes mean Δ per component across all models, to identify the
universally-critical components.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import CONFIGS, MODELS, collect  # type: ignore


def main() -> None:
    rows = collect()
    # Index by (model_id, config) -> list of rows
    idx = defaultdict(list)
    for r in rows:
        idx[(r["model_id"], r["config"])].append(r)

    # Compute file_macro per (model, config)
    fm = {}  # (sid, cfg) -> file_macro
    rs = {}  # (sid, cfg) -> run_success
    for (sid, cfg), lst in idx.items():
        per_row_rate = []
        run_ok = 0
        for r in lst:
            if r["files_processed"] > 0:
                per_row_rate.append(r["files_successful"] / r["files_processed"] * 100)
            else:
                per_row_rate.append(0.0)
            if r["tests_validated"] > 0:
                run_ok += 1
        fm[(sid, cfg)] = sum(per_row_rate) / len(per_row_rate) if per_row_rate else 0.0
        rs[(sid, cfg)] = run_ok / len(lst) * 100 if lst else 0.0

    print()
    print("=== file_macro success rate per (model, config) ===")
    print(f"{'Model':<24}", end="")
    for c in CONFIGS:
        print(f"{c[:14]:>10}", end="")
    print()
    for raw_dir, sid, lbl in MODELS:
        print(f"{lbl:<24}", end="")
        for cfg in CONFIGS:
            v = fm.get((sid, cfg), 0.0)
            print(f"{v:>9.1f}%", end="")
        print()

    print()
    print("=== run_success rate per (model, config) ===")
    print(f"{'Model':<24}", end="")
    for c in CONFIGS:
        print(f"{c[:14]:>10}", end="")
    print()
    for raw_dir, sid, lbl in MODELS:
        print(f"{lbl:<24}", end="")
        for cfg in CONFIGS:
            v = rs.get((sid, cfg), 0.0)
            print(f"{v:>9.1f}%", end="")
        print()

    # Delta vs full per model per config (file_macro)
    print()
    print("=== Δ vs full (file_macro p.p.) per (model, config) — negative means component helps ===")
    print(f"{'Model':<24}", end="")
    for c in CONFIGS:
        if c == "full":
            continue
        print(f"{c[:14]:>10}", end="")
    print()
    delta_by_cfg = defaultdict(list)
    for raw_dir, sid, lbl in MODELS:
        full_v = fm.get((sid, "full"), 0.0)
        print(f"{lbl:<24}", end="")
        for cfg in CONFIGS:
            if cfg == "full":
                continue
            d = fm.get((sid, cfg), 0.0) - full_v
            print(f"{d:>+9.1f} ", end="")
            delta_by_cfg[cfg].append(d)
        print()

    print()
    print("=== Mean Δ vs full per component (averaged over 7 models) ===")
    for cfg in CONFIGS:
        if cfg == "full":
            continue
        deltas = delta_by_cfg[cfg]
        mean = sum(deltas) / len(deltas) if deltas else 0.0
        worst = min(deltas)
        best = max(deltas)
        print(f"  {cfg:<24}  mean Δ = {mean:+.1f} p.p.   range = [{worst:+.1f}, {best:+.1f}]")


if __name__ == "__main__":
    main()
