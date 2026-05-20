#!/usr/bin/env python3
"""Pretty-print key fields of a testgen JSON report."""
import json
import sys

d = json.load(open(sys.argv[1]))
cfg = d.get("config", {})
print("=== config (relevant fields) ===")
for k in ("provider", "provider_allow_fallbacks", "temperature", "seed",
          "ablation_config", "run_index"):
    print(f"  {k}: {cfg.get(k)}")
print(f"\nmodel: {d.get('model')}")
print(f"files: {len(d.get('files', []))}")
totals = d.get("totals", {})
print(f"prompt_tokens: {totals.get('prompt_tokens')}")
print(f"completion_tokens: {totals.get('completion_tokens')}")
