"""Pruner criticality: per-(model, repo) view of full vs no-pruning.

For each model, we tabulate file_macro under both configs and the delta.
Also breaks down by repo to identify whether pruner-loss is uniform across
repositories or driven by specific projects.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import collect, MODELS, REPOS  # type: ignore


def main() -> None:
    rows = collect()
    # (model_id, repo, config) -> list[row]
    idx = defaultdict(list)
    for r in rows:
        idx[(r["model_id"], r["repo"], r["config"])].append(r)

    def file_macro(rs):
        rates = []
        for r in rs:
            if r["files_processed"] > 0:
                rates.append(r["files_successful"] / r["files_processed"] * 100)
            else:
                rates.append(0.0)
        return sum(rates) / len(rates) if rates else 0.0

    print()
    print("=== full vs no-pruning per model (file_macro %) ===")
    print(f"{'Model':<24}{'full':>9}{'no-prune':>11}{'Δ':>9}{'rel(no-prune/full)':>20}")
    for raw_dir, sid, lbl in MODELS:
        full_v = file_macro(idx[(sid, *_unpack_repo(idx, sid)), 'full'] if False else _all_for(idx, sid, 'full'))
        np_v = file_macro(_all_for(idx, sid, 'no-pruning'))
        delta = np_v - full_v
        rel = (np_v / full_v * 100) if full_v > 0 else 0.0
        print(f"{lbl:<24}{full_v:>8.1f}%{np_v:>10.1f}%{delta:>+8.1f} {rel:>15.1f}%")

    print()
    print("=== Δ (no-pruning − full) per (model × repo) ===")
    print(f"{'Repo':<22}", end="")
    for raw_dir, sid, lbl in MODELS:
        print(f"{sid[:11]:>12}", end="")
    print()
    for repo in REPOS:
        print(f"{repo:<22}", end="")
        for raw_dir, sid, lbl in MODELS:
            f = file_macro(idx[(sid, repo, "full")])
            n = file_macro(idx[(sid, repo, "no-pruning")])
            d = n - f
            print(f"{d:>+11.0f} ", end="")
        print()

    print()
    print("=== full file_macro per (model × repo) ===")
    print(f"{'Repo':<22}", end="")
    for raw_dir, sid, lbl in MODELS:
        print(f"{sid[:11]:>12}", end="")
    print()
    for repo in REPOS:
        print(f"{repo:<22}", end="")
        for raw_dir, sid, lbl in MODELS:
            f = file_macro(idx[(sid, repo, "full")])
            print(f"{f:>11.0f}%", end="")
        print()

    print()
    print("=== no-pruning file_macro per (model × repo) ===")
    print(f"{'Repo':<22}", end="")
    for raw_dir, sid, lbl in MODELS:
        print(f"{sid[:11]:>12}", end="")
    print()
    for repo in REPOS:
        print(f"{repo:<22}", end="")
        for raw_dir, sid, lbl in MODELS:
            n = file_macro(idx[(sid, repo, "no-pruning")])
            print(f"{n:>11.0f}%", end="")
        print()


def _all_for(idx, sid, cfg):
    out = []
    for repo in REPOS:
        out.extend(idx[(sid, repo, cfg)])
    return out


def _unpack_repo(idx, sid):
    return ()


if __name__ == "__main__":
    main()
