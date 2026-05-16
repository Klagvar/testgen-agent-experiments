"""Capability ladder: success rate per model averaged across all configs/runs.

Definition of success: per-(model, repo, config, run) we look at file-level
results and count file-level statuses success/total. A "successful run" is
the most user-facing aggregate (file-level success rate) per row.

Reports two views:
  A) macro success rate: mean over all 144 rows = mean over (repo,config,run)
     of the row's file_success_rate. This avoids weighting toward repos with
     more files.
  B) micro success rate: total successful files / total files.

Also reports tests_validated counts (as a complementary success indicator,
useful because no-pruning-style configs can lose validity even with files
"successful").
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import collect, MODELS, REPOS, CONFIGS, model_label  # type: ignore


def main() -> None:
    rows = collect()
    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_id"]].append(r)

    print()
    print("=" * 100)
    print(f"{'Model':<26}{'file_macro':>12}{'file_micro':>12}{'run_succ':>11}{'OK files':>10}{'all files':>11}{'V tests':>9}{'hours':>9}")
    print("-" * 100)

    summary = []
    for raw_dir, sid, lbl in MODELS:
        rs = by_model.get(sid, [])
        if not rs:
            continue
        per_row_rate = []
        total_ok = 0
        total_all = 0
        total_validated = 0
        total_seconds = 0.0
        runs_total = 0
        runs_success = 0  # run is "successful" if at least one test was validated
        for r in rs:
            files_proc = r["files_processed"]
            files_ok = r["files_successful"]
            total_ok += files_ok
            total_all += files_proc
            total_validated += r["tests_validated"]
            total_seconds += r["duration_s"]
            runs_total += 1
            if r["tests_validated"] > 0:
                runs_success += 1
            if files_proc > 0:
                per_row_rate.append(files_ok / files_proc * 100)
            else:
                per_row_rate.append(0.0)
        macro = sum(per_row_rate) / len(per_row_rate) if per_row_rate else 0.0
        micro = total_ok / total_all * 100 if total_all > 0 else 0.0
        run_succ = runs_success / runs_total * 100 if runs_total else 0.0
        hours = total_seconds / 3600
        summary.append((sid, lbl, macro, micro, run_succ, total_ok, total_all, total_validated, hours))
        print(f"{lbl:<26}{macro:>11.1f}%{micro:>11.1f}%{run_succ:>10.1f}%{total_ok:>10d}{total_all:>11d}{total_validated:>9d}{hours:>9.1f}")
    print("=" * 100)

    print()
    print("=== Capability ladder (by file-macro success rate) ===")
    summary_sorted = sorted(summary, key=lambda x: -x[2])
    for rank, (sid, lbl, macro, micro, run_succ, ok, all_, val, hrs) in enumerate(summary_sorted, 1):
        print(f"  {rank}. {lbl:<26} file_macro={macro:5.1f}%  file_micro={micro:5.1f}%  "
              f"run_success={run_succ:5.1f}%  validated_tests={val}  hours={hrs:.1f}")

    # Per-config success rate per model (for cross-tab in §5.3)
    print()
    print("=== Per-config view (file-level macro success rate per model × config) ===")
    print(f"{'Model':<24}", end="")
    for c in CONFIGS:
        print(f"{c[:10]:>11}", end="")
    print()
    for raw_dir, sid, lbl in MODELS:
        rs = by_model.get(sid, [])
        if not rs:
            continue
        print(f"{lbl:<24}", end="")
        for cfg in CONFIGS:
            sub = [r for r in rs if r["config"] == cfg]
            if not sub:
                print(f"{'-':>11}", end="")
                continue
            rates = []
            for r in sub:
                if r["files_processed"] > 0:
                    rates.append(r["files_successful"] / r["files_processed"] * 100)
                else:
                    rates.append(0.0)
            avg = sum(rates) / len(rates)
            print(f"{avg:>10.1f}%", end="")
        print()


if __name__ == "__main__":
    main()
