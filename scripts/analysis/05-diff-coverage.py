"""Diff coverage: pct of changed lines covered by generated tests.

We only consider rows where files_successful > 0 (otherwise diff coverage
is meaningless because no tests passed). Aggregates by (model, config) and
(model, repo).
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import collect, MODELS, CONFIGS, REPOS  # type: ignore


def main() -> None:
    rows = collect()

    # 1) per-model diff_cov averaged over rows where files_successful > 0
    print()
    print("=== diff_coverage_pct per model (rows with at least one successful file) ===")
    print(f"{'Model':<26}{'mean':>10}{'median':>10}{'rows':>8}{'rows_total':>12}")
    print("-" * 70)
    for raw_dir, sid, lbl in MODELS:
        rs = [r for r in rows if r["model_id"] == sid]
        ok = [r["diff_cov_pct"] for r in rs if r["files_successful"] > 0]
        all_n = len(rs)
        if not ok:
            print(f"{lbl:<26}{'-':>10}{'-':>10}{0:>8}{all_n:>12}")
            continue
        ok_sorted = sorted(ok)
        med = ok_sorted[len(ok_sorted) // 2]
        print(f"{lbl:<26}{mean(ok):>9.1f}%{med:>9.1f}%{len(ok):>8}{all_n:>12}")

    # 2) per (model, config)
    print()
    print("=== diff_cov mean per (model, config) — only rows with success ===")
    print(f"{'Model':<24}", end="")
    for c in CONFIGS:
        print(f"{c[:10]:>10}", end="")
    print()
    by_mc = defaultdict(list)
    for r in rows:
        if r["files_successful"] > 0:
            by_mc[(r["model_id"], r["config"])].append(r["diff_cov_pct"])
    for raw_dir, sid, lbl in MODELS:
        print(f"{lbl:<24}", end="")
        for cfg in CONFIGS:
            vs = by_mc[(sid, cfg)]
            if vs:
                print(f"{mean(vs):>9.0f}%", end="")
            else:
                print(f"{'-':>10}", end="")
        print()

    # 3) full vs no-coverage diff_cov (the key trade-off claim)
    print()
    print("=== full vs no-coverage diff_coverage (success rows only) ===")
    print(f"{'Model':<26}{'full':>10}{'no-cov':>10}{'Δ':>10}")
    for raw_dir, sid, lbl in MODELS:
        full_v = mean([r["diff_cov_pct"] for r in rows
                       if r["model_id"] == sid and r["config"] == "full" and r["files_successful"] > 0]
                      or [0])
        nc_v = mean([r["diff_cov_pct"] for r in rows
                     if r["model_id"] == sid and r["config"] == "no-coverage" and r["files_successful"] > 0]
                    or [0])
        print(f"{lbl:<26}{full_v:>9.0f}%{nc_v:>9.0f}%{full_v-nc_v:>+9.0f}")


if __name__ == "__main__":
    main()
