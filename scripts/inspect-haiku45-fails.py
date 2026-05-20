#!/usr/bin/env python3
"""Inspect actual failure modes in haiku-4.5 vs 3.5 runs.
Look at file-level data and per-attempt history."""
import glob
import json
import os
from collections import Counter

models = [
    ("3.5", "результаты/raw/anthropic-claude-3.5-haiku"),
    ("4.5", "результаты/raw/anthropic-claude-haiku-4.5"),
]

print("=" * 70)
print("STEP 1: Inspect raw structure of one failed run")
print("=" * 70)

# Pick gin-gonic-gin full-run1 — 4.5 had 0/18 here, 3.5 had 15/18
sample_3 = "результаты/raw/anthropic-claude-3.5-haiku/gin-gonic-gin/full-run1.json"
sample_4 = "результаты/raw/anthropic-claude-haiku-4.5/gin-gonic-gin/full-run1.json"

for label, path in [("3.5", sample_3), ("4.5", sample_4)]:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    print(f"\n--- {label}-haiku gin-gonic-gin/full-run1 ---")
    print(f"keys: {list(d.keys())}")
    print(f"totals: {json.dumps(d.get('totals', {}), indent=2, ensure_ascii=False)}")
    files = d.get("files") or []
    print(f"files (count={len(files)}):")
    for fl in files[:5]:
        print(f"  {json.dumps({k: v for k, v in fl.items() if k != 'attempts_history'}, indent=2, ensure_ascii=False)[:400]}")

print()
print("=" * 70)
print("STEP 2: Aggregate file-level statuses for full config (no ablations)")
print("=" * 70)

for tag, mdir in models:
    s = Counter()
    err_lines = Counter()
    attempts_distrib = Counter()
    for f in glob.glob(os.path.join(mdir, "*/full-run*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        for fl in (d.get("files") or []):
            s[fl.get("status", "?")] += 1
            attempts_distrib[fl.get("attempts", -1)] += 1
            for err in (fl.get("errors") or []):
                if isinstance(err, dict):
                    msg = err.get("message", "")
                else:
                    msg = str(err)
                if msg:
                    err_lines[msg[:80]] += 1
    print(f"\n--- {tag}-haiku, full config ---")
    print(f"  status counts: {dict(s)}")
    print(f"  attempts distribution: {dict(attempts_distrib)}")
    print(f"  top error message prefixes:")
    for msg, n in err_lines.most_common(10):
        print(f"    {n:>4} × {msg!r}")
