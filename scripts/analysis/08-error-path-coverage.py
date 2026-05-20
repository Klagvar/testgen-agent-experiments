#!/usr/bin/env python3
"""Error path coverage: how often error-return branches are covered.

Many of our 8 repos have error_paths_total == 0 (functions without error
returns). We focus on the ones where the metric is meaningful.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import MODELS, REPOS, collect  # type: ignore


def main() -> None:
    rows = collect()

    # Per-repo: how many rows have non-zero error_paths_total
    print()
    print("=== Repos where error_paths_total > 0 ===")
    print(f"{'Repo':<22}{'rows w/ EP':>12}{'rows total':>12}{'mean EP_total':>14}")
    for repo in REPOS:
        rs = [r for r in rows if r["repo"] == repo]
        with_ep = [r for r in rs if r["ep_total"] > 0]
        if not with_ep:
            print(f"{repo:<22}{0:>12d}{len(rs):>12d}{0:>14.1f}")
            continue
        print(f"{repo:<22}{len(with_ep):>12d}{len(rs):>12d}{mean([r['ep_total'] for r in with_ep]):>14.1f}")

    # Per-model EP coverage on relevant repos only
    print()
    print("=== Per-model EP covered/total (full config, success rows, where ep_total > 0) ===")
    print(f"{'Model':<26}{'covered':>11}{'total':>10}{'pct':>10}{'rows':>7}")
    for raw_dir, sid, lbl in MODELS:
        rs = [r for r in rows
              if r["model_id"] == sid and r["config"] == "full"
              and r["files_successful"] > 0 and r["ep_total"] > 0]
        if not rs:
            print(f"{lbl:<26}{'-':>11}{'-':>10}{'-':>10}{0:>7}")
            continue
        cov = sum(r["ep_covered"] for r in rs)
        tot = sum(r["ep_total"] for r in rs)
        pct = cov / tot * 100 if tot > 0 else 0
        print(f"{lbl:<26}{cov:>11d}{tot:>10d}{pct:>9.1f}%{len(rs):>7}")

    # Per-(model, repo) on EP-rich repos
    ep_rich = [repo for repo in REPOS
               if any(r["ep_total"] > 0 for r in rows if r["repo"] == repo)]
    print()
    print(f"=== EP_pct per (model, repo) — full config, success rows; relevant repos: {ep_rich} ===")
    print(f"{'Model':<24}", end="")
    for repo in ep_rich:
        print(f"{repo[:14]:>16}", end="")
    print()
    for raw_dir, sid, lbl in MODELS:
        print(f"{lbl[:24]:<24}", end="")
        for repo in ep_rich:
            rs = [r for r in rows
                  if r["model_id"] == sid and r["repo"] == repo
                  and r["config"] == "full" and r["files_successful"] > 0
                  and r["ep_total"] > 0]
            if not rs:
                print(f"{'-':>16}", end="")
                continue
            cov = sum(r["ep_covered"] for r in rs)
            tot = sum(r["ep_total"] for r in rs)
            pct = cov / tot * 100 if tot else 0
            print(f"{pct:>15.0f}%", end="")
        print()


if __name__ == "__main__":
    main()
