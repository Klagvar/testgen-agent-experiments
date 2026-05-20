#!/usr/bin/env python3
"""Mutation score: how many mutants are killed by generated tests.

mutation_enabled is False in our experiment configuration (see config.json).
So all mutations_total are 0. This means: we DO NOT have mutation testing
data in the main experiment. We need to either:
  (a) run a small mutation experiment separately
  (b) acknowledge that the mutation module is implemented but not evaluated

Let's verify what's in the data first.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import MODELS, collect  # type: ignore


def main() -> None:
    rows = collect()
    print()
    print("=== Mutation testing in the main experiment ===")
    nonzero_total = sum(1 for r in rows if r["mutations_total"] > 0)
    nonzero_killed = sum(1 for r in rows if r["mutations_killed"] > 0)
    print(f"Total rows: {len(rows)}")
    print(f"Rows with mutations_total > 0: {nonzero_total}")
    print(f"Rows with mutations_killed > 0: {nonzero_killed}")

    # Check config flag
    print()
    print("=== mutation_enabled flag distribution ===")
    # Need to peek into raw JSONs
    import json
    from pathlib import Path as _P
    enabled_count = 0
    for r in rows:
        with open(r["_path"], encoding="utf-8") as f:
            data = json.load(f)
        if data.get("config", {}).get("mutation_enabled"):
            enabled_count += 1
    print(f"Rows with mutation_enabled=True in config: {enabled_count}")


if __name__ == "__main__":
    main()
