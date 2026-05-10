#!/usr/bin/env python3
"""
Rebuild a complete benchmark-index.json for a model directory by walking
all per-repo `repo.json` files. The cmd/benchmark tool only writes an
index for the repos handled in its last invocation, so after a partial
rerun the on-disk index becomes inconsistent. This script restores
ground truth from the per-repo summaries that the agent itself wrote.

Usage:
    python3 scripts/rebuild-benchmark-index.py <results-model-dir>

Example:
    python3 scripts/rebuild-benchmark-index.py \
        результаты/raw/qwen-qwen-2.5-7b-instruct
"""
import json
import os
import sys
from datetime import datetime, timezone

if len(sys.argv) != 2:
    sys.exit(f"usage: {sys.argv[0]} <results-model-dir>")

model_dir = sys.argv[1]
if not os.path.isdir(model_dir):
    sys.exit(f"not a directory: {model_dir}")

results = []
latest_ts = None
total_duration_ns = 0
model_name = None
work_dir = None
agent_bin = None

for repo_name in sorted(os.listdir(model_dir)):
    repo_dir = os.path.join(model_dir, repo_name)
    repo_json = os.path.join(repo_dir, "repo.json")
    if not os.path.isfile(repo_json):
        continue

    with open(repo_json, encoding="utf-8") as f:
        repo_data = json.load(f)

    results.append(repo_data)
    total_duration_ns += repo_data.get("duration", 0)

    # Parse a timestamp out of the youngest run file in this repo to
    # pick the global "last touched" timestamp for the index.
    runs = repo_data.get("runs", [])
    for run in runs:
        rp = run.get("report_path", "")
        local = os.path.join(repo_dir, os.path.basename(rp)) if rp else None
        if local and os.path.isfile(local):
            try:
                with open(local, encoding="utf-8") as rf:
                    rdata = json.load(rf)
                ts_str = rdata.get("timestamp")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        if latest_ts is None or ts > latest_ts:
                            latest_ts = ts
                    except ValueError:
                        pass
                if model_name is None:
                    model_name = rdata.get("model")
            except (json.JSONDecodeError, OSError):
                pass

    if work_dir is None:
        cd = repo_data.get("clone_dir", "")
        if cd:
            work_dir = os.path.dirname(cd.rstrip("/"))

if not results:
    sys.exit(f"no repo.json files found under {model_dir}")

if model_name is None:
    model_name = os.path.basename(model_dir.rstrip("/")).replace("-", "/", 1)

if latest_ts is None:
    latest_ts = datetime.now(timezone.utc)

if work_dir is None:
    work_dir = ""

agent_bin = ""
if work_dir:
    candidate = os.path.join(os.path.dirname(work_dir), "testgen-agent")
    agent_bin = candidate

index = {
    "work_dir": work_dir,
    "model": model_name,
    "agent_bin": agent_bin,
    "timestamp": latest_ts.isoformat(),
    "results": results,
}

out_path = os.path.join(model_dir, "benchmark-index.json")
with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    json.dump(index, f, indent=2, ensure_ascii=False)
    f.write("\n")

n_runs = sum(len(r.get("runs", [])) for r in results)
total_seconds = total_duration_ns / 1e9
print(
    f"Rebuilt {out_path}: {len(results)} repos, "
    f"{n_runs} runs, total agent time = {total_seconds/3600:.2f} h"
)
