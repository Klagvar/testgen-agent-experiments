#!/usr/bin/env python3
"""Detailed diagnosis: WHY does Claude Haiku 4.5 fail more than 3.5?

Compare:
- tests_generated vs tests_validated (how many got created vs survived compilation)
- per-attempt success (does retry-loop actually help?)
- per-config breakdown
"""
import json, glob, os, re
from collections import Counter

models = [
    ("3.5-haiku", "результаты/raw/anthropic-claude-3.5-haiku"),
    ("4.5-haiku", "результаты/raw/anthropic-claude-haiku-4.5"),
]

print(f"{'metric':<35} {'3.5-haiku':>15} {'4.5-haiku':>15}")
print("─" * 70)

stats = {tag: Counter() for tag, _ in models}
errors = {tag: Counter() for tag, _ in models}

for tag, mdir in models:
    for f in glob.glob(os.path.join(mdir, "*/*-run*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        t = d.get("totals", {})
        files = d.get("files", []) or []
        s = stats[tag]
        s["runs"] += 1
        s["files_processed"] += t.get("files_processed", 0)
        s["tests_generated"] += t.get("tests_generated", 0)
        s["tests_validated"] += t.get("tests_validated", 0)
        s["prompt_tokens"] += t.get("prompt_tokens", 0)
        s["completion_tokens"] += t.get("completion_tokens", 0)
        if t.get("tests_validated", 0) > 0:
            s["successful_runs"] += 1
        # Look at per-file outcomes
        for fl in files:
            status = fl.get("status", "")
            errs = fl.get("errors", []) or []
            attempts = fl.get("attempts", 0)
            s[f"file_status_{status}"] += 1
            s["max_attempts"] = max(s.get("max_attempts", 0), attempts)
            for e in errs:
                msg = e.get("message", "") if isinstance(e, dict) else str(e)
                # Classify
                low = msg.lower()
                if "expected 'package'" in low or "expected ';'" in low or "expected '}'" in low:
                    errors[tag]["parse: bad_package_or_brace"] += 1
                elif "ast merge" in low or "parse generated tests" in low:
                    errors[tag]["parse: ast_merge_failed"] += 1
                elif "cannot use" in low and "as" in low and "in argument" in low:
                    errors[tag]["compile: type_mismatch"] += 1
                elif "undefined:" in low:
                    errors[tag]["compile: undefined_symbol"] += 1
                elif "missing method" in low:
                    errors[tag]["compile: missing_method"] += 1
                elif "unknown field" in low:
                    errors[tag]["compile: unknown_field"] += 1
                elif "no test results" in low or "test execution" in low:
                    errors[tag]["test: execution_fail"] += 1
                elif "max retries" in low:
                    errors[tag]["limit: max_retries"] += 1
                elif "test:" in low and "fail" in low:
                    errors[tag]["test: assertion_fail"] += 1
                else:
                    errors[tag][f"other: {msg[:50]}"] += 1


for key in ["runs", "successful_runs", "files_processed", "tests_generated",
            "tests_validated", "prompt_tokens", "completion_tokens"]:
    v35 = stats["3.5-haiku"][key]
    v45 = stats["4.5-haiku"][key]
    print(f"{key:<35} {v35:>15,} {v45:>15,}")

# Ratio of validated to generated tells us "how many survive compilation"
g35 = stats["3.5-haiku"]["tests_generated"]
g45 = stats["4.5-haiku"]["tests_generated"]
v35 = stats["3.5-haiku"]["tests_validated"]
v45 = stats["4.5-haiku"]["tests_validated"]
print(f"{'compile/validate survival rate':<35} "
      f"{(v35/g35*100 if g35 else 0):>14.1f}% "
      f"{(v45/g45*100 if g45 else 0):>14.1f}%")

print()
print("Per-file status counts (out of all files in all runs):")
print("─" * 70)
all_statuses = set()
for tag in stats:
    for k in stats[tag]:
        if k.startswith("file_status_"):
            all_statuses.add(k.replace("file_status_", ""))
for st in sorted(all_statuses):
    v35 = stats["3.5-haiku"][f"file_status_{st}"]
    v45 = stats["4.5-haiku"][f"file_status_{st}"]
    print(f"  {st:<33} {v35:>15} {v45:>15}")

print()
print("Top error patterns:")
print("─" * 70)
all_err_keys = set(errors["3.5-haiku"].keys()) | set(errors["4.5-haiku"].keys())
for k in sorted(all_err_keys, key=lambda x: -(errors["4.5-haiku"][x] + errors["3.5-haiku"][x])):
    v35 = errors["3.5-haiku"][k]
    v45 = errors["4.5-haiku"][k]
    if v35 + v45 == 0:
        continue
    print(f"  {k:<45} {v35:>10} {v45:>10}")
