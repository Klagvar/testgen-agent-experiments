#!/usr/bin/env python3
"""Branch coverage: pct of diff-related branches taken by tests.

Same convention as diff_coverage: only count rows with at least one
successful file. We're particularly interested in full vs no-coverage
to validate the claim that the cover-loop trades file-success for
deeper branch coverage.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import CONFIGS, MODELS, collect  # type: ignore


def main() -> None:
    rows = collect()

    print()
    print("=== branch_coverage_pct per model (success rows only) ===")
    print(f"{'Model':<26}{'mean':>10}{'median':>10}{'rows':>8}")
    print("-" * 60)
    for raw_dir, sid, lbl in MODELS:
        rs = [r for r in rows if r["model_id"] == sid and r["files_successful"] > 0]
        if not rs:
            print(f"{lbl:<26}{'-':>10}{'-':>10}{0:>8}")
            continue
        vals = [r["branch_cov_pct"] for r in rs]
        med = sorted(vals)[len(vals) // 2]
        print(f"{lbl:<26}{mean(vals):>9.1f}%{med:>9.1f}%{len(rs):>8}")

    # Per (model, config), only success rows
    print()
    print("=== branch_cov mean per (model, config) — success rows only ===")
    print(f"{'Model':<24}", end="")
    for c in CONFIGS:
        print(f"{c[:10]:>10}", end="")
    print()
    by_mc = defaultdict(list)
    for r in rows:
        if r["files_successful"] > 0:
            by_mc[(r["model_id"], r["config"])].append(r["branch_cov_pct"])
    for raw_dir, sid, lbl in MODELS:
        print(f"{lbl:<24}", end="")
        for cfg in CONFIGS:
            vs = by_mc[(sid, cfg)]
            if vs:
                print(f"{mean(vs):>9.0f}%", end="")
            else:
                print(f"{'-':>10}", end="")
        print()

    # full vs no-coverage on branch_coverage (the trade-off claim)
    print()
    print("=== full vs no-coverage branch_coverage (success rows only) ===")
    print(f"{'Model':<26}{'full':>10}{'no-cov':>10}{'Δ':>10}")
    for raw_dir, sid, lbl in MODELS:
        full_v = mean([r["branch_cov_pct"] for r in rows
                       if r["model_id"] == sid and r["config"] == "full" and r["files_successful"] > 0]
                      or [0])
        nc_v = mean([r["branch_cov_pct"] for r in rows
                     if r["model_id"] == sid and r["config"] == "no-coverage" and r["files_successful"] > 0]
                    or [0])
        print(f"{lbl:<26}{full_v:>9.0f}%{nc_v:>9.0f}%{full_v-nc_v:>+9.0f}")

    # Aggregate: average of branches_covered/branches_total per (model, config)
    print()
    print("=== absolute branches: covered vs total per model ===")
    print(f"{'Model':<26}{'covered':>11}{'total':>11}{'pct':>10}")
    for raw_dir, sid, lbl in MODELS:
        rs = [r for r in rows if r["model_id"] == sid and r["files_successful"] > 0]
        cov_sum = sum(r["branches_covered"] for r in rs)
        total_sum = sum(r["branches_total"] for r in rs)
        pct = cov_sum / total_sum * 100 if total_sum > 0 else 0
        print(f"{lbl:<26}{cov_sum:>11d}{total_sum:>11d}{pct:>9.1f}%")


if __name__ == "__main__":
    main()
