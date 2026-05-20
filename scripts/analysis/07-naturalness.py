#!/usr/bin/env python3
"""Naturalness: 5 sub-metrics describing how human-like generated tests are.

Sub-metrics (from totals.naturalness):
  - assertion_ratio:        avg assertions per test (higher = more thorough)
  - no_assertions_pct:      % of tests with zero assertions (lower = better)
  - duplicate_assertions_pct: % redundant assertions (lower = better)
  - nil_only_assertions_pct: % asserting only against nil (lower = more meaningful)
  - error_assertions_pct:   % asserting on error returns (Go-specific positive)
  - test_name_score:        0-100, naming naturalness
  - var_name_score:         0-1, variable naming naturalness

Aggregate over 'full' configuration only (most representative production state)
and only over rows with at least 1 successful file.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import MODELS, collect  # type: ignore

METRICS = [
    ("nat_assert_ratio",   "assertions/test", ".2f", "higher better"),
    ("nat_no_assert_pct",  "no-assert %",     ".0f", "lower better"),
    ("nat_dup_assert_pct", "dup-assert %",    ".1f", "lower better"),
    ("nat_nil_assert_pct", "nil-only %",      ".1f", "lower better"),
    ("nat_err_assert_pct", "err-assert %",    ".0f", "context"),
    ("nat_test_name",      "test name 0-100", ".0f", "higher better"),
    ("nat_var_name",       "var name 0-1",    ".2f", "higher better"),
]


def main() -> None:
    rows = collect()

    # Aggregate over 'full' config, success rows only
    rs_by_model = defaultdict(list)
    for r in rows:
        if r["config"] == "full" and r["files_successful"] > 0 and r["nat_test_count"] > 0:
            rs_by_model[r["model_id"]].append(r)

    print()
    print("=== Naturalness sub-metrics in 'full' configuration (success rows) ===")
    print()
    print(f"{'Model':<24}{'AR':>8}{'NA%':>8}{'DA%':>8}{'NL%':>8}{'EA%':>8}{'TN':>8}{'VN':>8}{'n':>5}")
    print("-" * 88)
    for raw_dir, sid, lbl in MODELS:
        rs = rs_by_model[sid]
        if not rs:
            print(f"{lbl[:24]:<24}{'-':>8}" * 7)
            continue
        ar = mean([r["nat_assert_ratio"] for r in rs])
        na = mean([r["nat_no_assert_pct"] for r in rs])
        da = mean([r["nat_dup_assert_pct"] for r in rs])
        nl = mean([r["nat_nil_assert_pct"] for r in rs])
        ea = mean([r["nat_err_assert_pct"] for r in rs])
        tn = mean([r["nat_test_name"] for r in rs])
        vn = mean([r["nat_var_name"] for r in rs])
        print(f"{lbl[:24]:<24}{ar:>8.2f}{na:>7.0f}%{da:>7.1f}%{nl:>7.1f}%{ea:>7.0f}%{tn:>8.0f}{vn:>8.2f}{len(rs):>5}")

    print()
    print("Legend:")
    print("  AR = avg assertions per test (higher better)")
    print("  NA = % tests with zero assertions (lower better)")
    print("  DA = % duplicate assertions (lower better)")
    print("  NL = % nil-only assertions (lower better)")
    print("  EA = % error-related assertions (context-dependent for Go)")
    print("  TN = test-name naturalness 0-100 (higher better)")
    print("  VN = var-name naturalness 0-1 (higher better)")

    # Cross-config comparison: full vs no-coverage on assertion_ratio (proxy for cover-loop benefit)
    print()
    print("=== full vs no-coverage on assertion_ratio (mean) ===")
    print(f"{'Model':<26}{'full':>10}{'no-cov':>10}{'Δ':>10}")
    by_mc = defaultdict(list)
    for r in rows:
        if r["files_successful"] > 0 and r["nat_test_count"] > 0:
            by_mc[(r["model_id"], r["config"])].append(r["nat_assert_ratio"])
    for raw_dir, sid, lbl in MODELS:
        full_v = mean(by_mc[(sid, "full")] or [0])
        nc_v = mean(by_mc[(sid, "no-coverage")] or [0])
        print(f"{lbl:<26}{full_v:>9.2f}{nc_v:>9.2f}{full_v-nc_v:>+9.2f}")


if __name__ == "__main__":
    main()
