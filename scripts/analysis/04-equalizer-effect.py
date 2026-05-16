"""Equalizer effect: full vs no-pruning per model.

We use no-pruning as a proxy baseline ("minimal harness"): only the LLM and
test execution loop, without AST-based filtering. The intuition: how much
does the SAGA harness narrow (or widen) the capability gap between weak and
strong LLMs, compared to a baseline closer to "raw LLM + execution"?

Compares run_success rate for both configs, computes:
  - absolute gain (Δ p.p.)
  - relative multiplier (full / no-pruning)
  - tier transition (no-pruning tier → full tier)
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import collect, MODELS  # type: ignore


def main() -> None:
    rows = collect()
    idx = defaultdict(list)
    for r in rows:
        idx[(r["model_id"], r["config"])].append(r)

    def run_success(rs):
        if not rs:
            return 0.0
        ok = sum(1 for r in rs if r["tests_validated"] > 0)
        return ok / len(rs) * 100

    print()
    print("=== full vs no-pruning per model (run_success %) ===")
    print(f"{'Model':<26}{'no-pruning':>14}{'full':>10}{'Δ pp':>10}{'rel x':>10}")
    print("-" * 70)
    summary = []
    for raw_dir, sid, lbl in MODELS:
        np_v = run_success(idx[(sid, "no-pruning")])
        full_v = run_success(idx[(sid, "full")])
        delta = full_v - np_v
        rel = (full_v / np_v) if np_v > 0 else float("inf")
        summary.append((sid, lbl, np_v, full_v, delta, rel))
        rel_str = f"{rel:.2f}x" if np_v > 0 else "  ∞"
        print(f"{lbl:<26}{np_v:>13.1f}%{full_v:>9.1f}%{delta:>+9.1f}{rel_str:>10}")

    print()
    print("=== Spread analysis ===")
    np_vals = [s[2] for s in summary]
    full_vals = [s[3] for s in summary]
    print(f"  no-pruning spread (max-min): {max(np_vals):.1f}% - {min(np_vals):.1f}% = {max(np_vals)-min(np_vals):.1f} pp")
    print(f"  full       spread (max-min): {max(full_vals):.1f}% - {min(full_vals):.1f}% = {max(full_vals)-min(full_vals):.1f} pp")
    print(f"  spread change: {(max(full_vals)-min(full_vals)) - (max(np_vals)-min(np_vals)):+.1f} pp")

    print()
    print("=== Capability tier classification ===")
    # Tiers based on run_success: floor=<25, mid=25-75, prod-ready=75-95, frontier=>95
    def tier(rate: float) -> str:
        if rate < 25:
            return "floor"
        if rate < 75:
            return "mid"
        if rate < 95:
            return "prod"
        return "frontier"

    print(f"{'Model':<26}{'no-prune tier':>16}{'full tier':>16}{'transition':>12}")
    for sid, lbl, np_v, full_v, delta, rel in summary:
        t1 = tier(np_v)
        t2 = tier(full_v)
        trans = "→ promote" if t1 != t2 else "→ stays"
        print(f"{lbl:<26}{t1+f' ({np_v:.0f}%)':>16}{t2+f' ({full_v:.0f}%)':>16}{trans:>12}")

    # Mean gain by tier
    print()
    print("=== Mean improvement (Δ pp) ===")
    print(f"  Mean Δ (all models):       {sum(s[4] for s in summary)/len(summary):+.1f} pp")
    print(f"  Mean Δ (mid-tier without floor and frontier): "
          f"{sum(s[4] for s in summary if 25 < s[2] < 95)/max(1, sum(1 for s in summary if 25 < s[2] < 95)):+.1f} pp")


if __name__ == "__main__":
    main()
