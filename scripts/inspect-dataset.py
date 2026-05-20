#!/usr/bin/env python3
"""Print a per-repo summary of what base..head actually changes,
plus the head commit's subject — so we can compare against the PR
description in dataset.yaml.

Usage: python3 inspect-dataset.py [<dataset-yaml>]
"""
import os
import re
import subprocess
import sys

import yaml

ds_path = sys.argv[1] if len(sys.argv) > 1 else \
          "/mnt/d/Дз/4 семестр/НИР/эксперимент/dataset.yaml"
WORKDIR = os.environ.get("WORKDIR",
                         os.path.expanduser("~/testgen-experiments/workdir"))

with open(ds_path, encoding="utf-8") as f:
    raw = f.read()

ds = yaml.safe_load(raw)

def git(repo, *args):
    return subprocess.check_output(["git", "-C", repo, *args], text=True).strip()

def commit_files(repo, sha):
    out = git(repo, "show", "--name-status", "--format=", sha).splitlines()
    return [l for l in out if l.strip()]

# Pull the per-entry comment block from the YAML so we can match
# expected files to actual diff.
entries = re.findall(
    r"^\s*-\s*name:\s*(\S+)\s*\n.*?(?:#[^\n]*\n)*",
    raw, flags=re.MULTILINE)
yaml_text = raw

for r in ds["repos"]:
    name, base, head = r["name"], r["base"], r["head"]
    repo = os.path.join(WORKDIR, name)
    print("─" * 72)
    print(f"{name}")
    print(f"  base  = {base}")
    print(f"  head  = {head}")
    try:
        head_subject = git(repo, "log", "-1", "--format=%s", head)
    except subprocess.CalledProcessError:
        print("  ! cannot read head commit")
        continue
    print(f"  head subject : {head_subject}")
    n_commits = git(repo, "rev-list", "--count", f"{base}..{head}")
    print(f"  commits in range : {n_commits}")
    if int(n_commits) > 0:
        commits = git(repo, "log", "--oneline", f"{base}..{head}").splitlines()
        for c in commits[:6]:
            print(f"    {c}")
        if len(commits) > 6:
            print(f"    ... and {len(commits)-6} more")

    diff_files = git(repo, "diff", "--name-only", f"{base}..{head}").splitlines()
    if diff_files:
        prod = [f for f in diff_files if f.endswith(".go")
                and not f.endswith("_test.go")
                and not any(f.startswith(p) for p in ("vendor/", "examples/", "_examples/"))]
        tests = [f for f in diff_files if f.endswith("_test.go")]
        other = [f for f in diff_files if f not in prod and f not in tests]
        print(f"  diff files   : prod={len(prod)} tests={len(tests)} other={len(other)}")
        for f in prod:
            print(f"    PROD  {f}")
        for f in tests[:3]:
            print(f"    TEST  {f}")
        if len(tests) > 3:
            print(f"    TEST  ... +{len(tests)-3} more")
        for f in other[:3]:
            print(f"    OTHER {f}")
    else:
        print("  ! diff is empty")
