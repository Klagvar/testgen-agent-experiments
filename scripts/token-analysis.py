#!/usr/bin/env python3
"""Per-file token analysis grouped by status, across models."""
import json
import glob
import os

models = [
    ("Qwen 7B (floor)", "результаты/raw/qwen-qwen-2.5-7b-instruct"),
    ("Qwen 30B candidate", "результаты/raw/qwen-qwen3-coder-30b-a3b-instruct"),
]

def stats_per_file(model_dir):
    by_status = {}
    for f in glob.glob(os.path.join(model_dir, "*/*-run*.json")):
        d = json.load(open(f, encoding="utf-8"))
        for entry in d.get("files", []):
            st = entry.get("status", "unknown")
            r = by_status.setdefault(st, {"n": 0, "pin": 0, "comp": 0,
                                          "tests_total": 0, "tests_passed": 0})
            r["n"] += 1
            r["pin"] += entry.get("prompt_tokens", 0)
            r["comp"] += entry.get("completion_tokens", 0)
            r["tests_total"] += entry.get("tests_total", 0)
            r["tests_passed"] += entry.get("tests_passed", 0)
    return by_status

print(f"{'model':<22} {'status':<12} {'files':>6} {'avg prompt':>12} "
      f"{'avg compl':>11} {'tests_passed':>13}")
print("-" * 80)
for tag, dn in models:
    s = stats_per_file(dn)
    for st in sorted(s.keys()):
        r = s[st]
        if r["n"] == 0:
            continue
        print(
            f"{tag:<22} {st:<12} {r['n']:>6} "
            f"{r['pin']/r['n']:>12.0f} {r['comp']/r['n']:>11.0f} "
            f"{r['tests_passed']:>13}"
        )
    print()
