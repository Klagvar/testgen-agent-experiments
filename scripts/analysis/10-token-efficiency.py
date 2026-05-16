"""Token efficiency: tokens per validated test, total cost per model.

Per-million pricing (USD, OpenRouter pinned providers as of 2026-05):
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import collect, MODELS  # type: ignore

# (input USD/M, output USD/M)
PRICING = {
    "qwen-7b":      (0.04,  0.04),
    "qwen3-30b":    (0.10,  0.30),
    "llama-70b":    (0.59,  0.79),
    "deepseek-v3":  (0.27,  1.10),
    "gpt-4o-mini":  (0.15,  0.60),
    "claude-3.5":   (0.80,  4.00),
    "gemini-3-fl":  (0.30,  2.50),
}


def main() -> None:
    rows = collect()
    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_id"]].append(r)

    print()
    print("=== Token consumption and cost per model ===")
    print(f"{'Model':<24}{'prompt M':>10}{'compl M':>10}{'$ in':>8}{'$ out':>8}{'$ total':>10}{'V tests':>9}{'$/test':>8}")
    print("-" * 92)
    for raw_dir, sid, lbl in MODELS:
        rs = by_model[sid]
        prompt = sum(r["prompt_tokens"] for r in rs)
        compl = sum(r["completion_tokens"] for r in rs)
        v_tests = sum(r["tests_validated"] for r in rs)
        in_p, out_p = PRICING[sid]
        cost_in = prompt / 1_000_000 * in_p
        cost_out = compl / 1_000_000 * out_p
        cost_total = cost_in + cost_out
        per_test = cost_total / v_tests if v_tests else float("inf")
        per_test_str = f"${per_test:.3f}" if v_tests else "  ∞"
        print(f"{lbl:<24}{prompt/1e6:>9.2f}M{compl/1e6:>9.2f}M{cost_in:>7.2f}${cost_out:>7.2f}${cost_total:>9.2f}${v_tests:>9d}{per_test_str:>8}")

    # Pareto frontier: cost per test vs run_success
    print()
    print("=== Pareto: cost per validated test vs run_success ===")
    print(f"{'Model':<24}{'$/test':>9}{'run_succ':>10}{'V_tests':>9}{'tier':>14}")
    print("-" * 70)
    pts = []
    for raw_dir, sid, lbl in MODELS:
        rs = by_model[sid]
        prompt = sum(r["prompt_tokens"] for r in rs)
        compl = sum(r["completion_tokens"] for r in rs)
        v_tests = sum(r["tests_validated"] for r in rs)
        in_p, out_p = PRICING[sid]
        cost_total = prompt / 1_000_000 * in_p + compl / 1_000_000 * out_p
        per_test = cost_total / v_tests if v_tests else float("inf")
        runs = len(rs)
        run_ok = sum(1 for r in rs if r["tests_validated"] > 0)
        run_succ = run_ok / runs * 100 if runs else 0
        pts.append((sid, lbl, per_test, run_succ, v_tests))

    # Identify dominated points
    pts_sorted = sorted(pts, key=lambda x: x[2])  # by cost ascending
    pareto = []
    best_quality = -1
    for sid, lbl, cost, q, v in pts_sorted:
        tier = ""
        if cost == float("inf"):
            tier = "no value"
        elif q > best_quality:
            tier = "PARETO"
            pareto.append((sid, lbl, cost, q))
            best_quality = q
        else:
            tier = "dominated"
        cost_str = f"${cost:.3f}" if cost != float("inf") else "  ∞"
        print(f"{lbl:<24}{cost_str:>9}{q:>9.1f}%{v:>9d}{tier:>14}")

    print()
    print(f"Pareto-optimal models: {[p[1] for p in pareto]}")


if __name__ == "__main__":
    main()
