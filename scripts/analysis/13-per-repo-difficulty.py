#!/usr/bin/env python3
"""Per-repo difficulty: average run_success across all 7 models in 'full' config."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import MODELS, REPOS, collect  # type: ignore


def main() -> None:
    rows = collect()
    print()
    print("=== Per-repo difficulty: file_macro and run_success in 'full' config ===")
    print(f"{'Repo':<22}{'file_macro':>12}{'run_succ':>11}{'V_tests':>9}{'EP_total':>10}")
    print("-" * 70)
    for repo in REPOS:
        rs = [r for r in rows if r["repo"] == repo and r["config"] == "full"]
        if not rs:
            print(f"{repo:<22}{'-':>12}{'-':>11}{0:>9}{0:>10}")
            continue
        rates = []
        run_ok = 0
        v_tests_total = 0
        ep_total = sum(r["ep_total"] for r in rs)
        for r in rs:
            if r["files_processed"] > 0:
                rates.append(r["files_successful"] / r["files_processed"] * 100)
            else:
                rates.append(0.0)
            if r["tests_validated"] > 0:
                run_ok += 1
            v_tests_total += r["tests_validated"]
        macro = sum(rates) / len(rates) if rates else 0
        run_succ = run_ok / len(rs) * 100
        print(f"{repo:<22}{macro:>11.1f}%{run_succ:>10.1f}%{v_tests_total:>9d}{ep_total:>10d}")

    print()
    print("=== Per-(repo, model) run_success matrix in 'full' config ===")
    print(f"{'Repo':<22}", end="")
    for raw_dir, sid, lbl in MODELS:
        print(f"{sid[:10]:>11}", end="")
    print()
    for repo in REPOS:
        print(f"{repo:<22}", end="")
        for raw_dir, sid, lbl in MODELS:
            rs = [r for r in rows if r["repo"] == repo and r["model_id"] == sid and r["config"] == "full"]
            if not rs:
                print(f"{'-':>11}", end="")
                continue
            ok = sum(1 for r in rs if r["tests_validated"] > 0)
            rate = ok / len(rs) * 100
            print(f"{rate:>10.0f}%", end="")
        print()


if __name__ == "__main__":
    main()
