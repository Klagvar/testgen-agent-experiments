#!/usr/bin/env python3
"""Failure mode analysis: when files fail, why?

We examine file-level entries (status='failed') in raw JSON and try to
classify failure modes based on heuristic signals (e.g., tests_total=0
suggests the model produced nothing or pruner removed all candidates;
tests_total>0 but tests_passed=0 suggests a runtime/assertion failure).
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import MODELS, collect  # type: ignore


def classify_failure(file_entry: dict) -> str:
    """Heuristic classification of file-level failure."""
    if file_entry.get("status") == "success":
        return "success"
    tests_total = file_entry.get("tests_total", 0)
    tests_passed = file_entry.get("tests_passed", 0)
    if tests_total == 0:
        return "no-tests"  # nothing produced or all pruned
    if tests_total > 0 and tests_passed == 0:
        return "all-failed"  # tests compiled & ran but every one failed
    if tests_total > 0 and tests_passed < tests_total:
        return "partial"
    return "other"


def main() -> None:
    rows = collect()

    # Aggregate failures per model in 'full' config only
    by_model = defaultdict(Counter)
    for r in rows:
        if r["config"] != "full":
            continue
        for f in r["files_raw"]:
            cat = classify_failure(f)
            by_model[r["model_id"]][cat] += 1

    print()
    print("=== Failure modes per model in 'full' config (file-level) ===")
    print(f"{'Model':<26}{'success':>10}{'no-tests':>11}{'all-failed':>13}{'partial':>10}{'total':>9}")
    print("-" * 80)
    for raw_dir, sid, lbl in MODELS:
        c = by_model[sid]
        total = sum(c.values())
        if total == 0:
            print(f"{lbl:<26}{'-':>10}{'-':>11}{'-':>13}{'-':>10}{0:>9}")
            continue
        succ = c.get("success", 0)
        nt = c.get("no-tests", 0)
        af = c.get("all-failed", 0)
        pa = c.get("partial", 0)
        print(f"{lbl:<26}{succ:>5d} ({succ/total*100:>2.0f}%){nt:>5d} ({nt/total*100:>2.0f}%){af:>6d} ({af/total*100:>2.0f}%){pa:>4d} ({pa/total*100:>2.0f}%){total:>9d}")

    # Failure modes by config
    print()
    print("=== Failure modes per config (averaged across all 7 models) ===")
    by_config = defaultdict(Counter)
    for r in rows:
        for f in r["files_raw"]:
            cat = classify_failure(f)
            by_config[r["config"]][cat] += 1

    print(f"{'Config':<24}{'success':>10}{'no-tests':>11}{'all-failed':>13}{'partial':>10}{'total':>9}")
    for cfg in ["full", "no-types", "no-smart-diff", "no-structured-feedback", "no-pruning", "no-coverage"]:
        c = by_config[cfg]
        total = sum(c.values())
        if total == 0:
            continue
        succ = c.get("success", 0)
        nt = c.get("no-tests", 0)
        af = c.get("all-failed", 0)
        pa = c.get("partial", 0)
        print(f"{cfg:<24}{succ:>5d} ({succ/total*100:>2.0f}%){nt:>5d} ({nt/total*100:>2.0f}%){af:>6d} ({af/total*100:>2.0f}%){pa:>4d} ({pa/total*100:>2.0f}%){total:>9d}")


if __name__ == "__main__":
    main()
