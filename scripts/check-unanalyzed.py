#!/usr/bin/env python3
"""What metrics do we collect but haven't analyzed yet?"""
import json
sample = "результаты/raw/google-gemini-3-flash-preview/gin-gonic-gin/full-run1.json"
d = json.load(open(sample, encoding="utf-8"))
t = d.get("totals", {})
nat = t.get("naturalness", {})
files = d.get("files", [])

print("=" * 80)
print("Доступные метрики в каждом JSON-отчёте:")
print("=" * 80)
print()
print("Toplevel keys:", sorted(d.keys()))
print()
print("totals fields:")
for k, v in sorted(t.items()):
    if isinstance(v, dict):
        print(f"  {k}: dict")
        for k2, v2 in v.items():
            print(f"    {k2}: {v2}")
    else:
        print(f"  {k}: {v}")

print()
print("Per-file fields:")
if files:
    for k, v in sorted(files[0].items()):
        if not isinstance(v, (dict, list)):
            print(f"  {k}: {v}")

print()
print("=" * 80)
print("СТАТУС АНАЛИЗА")
print("=" * 80)
print("""
ПРОАНАЛИЗИРОВАНО (отражено в Тейках 1-8):
  ✅ tests_validated, files_processed, success rate
  ✅ prompt_tokens, completion_tokens (только агрегаты)
  ✅ duration_seconds (только в финальной таблице "часов")
  ✅ ablation_config (6 конфигов × 7 моделей = матрица)

НЕ ПРОАНАЛИЗИРОВАНО (можно добавить):
  ❌ branch_coverage_pct  — собирается, но не разобрано по моделям
  ❌ branches_covered / branches_total — то же
  ❌ diff_coverage_pct  — кастомная метрика SAGA, не разобрана
  ❌ mutations_killed / mutations_total — собирается, не анализировано
  ❌ error_paths_covered / error_paths_total — Go-специфичная метрика
  ❌ token_efficiency_tokens_per_test — есть, не сравнивалось по моделям
  ❌ naturalness (5 sub-метрик):
       - test_count, assertion_ratio, no_assertions_pct,
         duplicate_assertions_pct, nil_only_assertions_pct,
         error_assertions_pct, test_name_score, var_name_score
  ❌ Variance across 3 runs (стандартное отклонение)
  ❌ Failure mode analysis: чем заканчиваются неуспешные runs?
  ❌ Per-repo difficulty: какие репо легче, почему?
""")
