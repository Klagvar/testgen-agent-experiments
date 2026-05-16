"""Universal aggregator: walk all raw JSON reports and emit one flat table.

Each row corresponds to one (model, repo, ablation_config, run_index) tuple.
Used as the input by all per-metric analysis scripts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "результаты" / "raw"

# Canonical order/labels used by all downstream scripts.
MODELS: list[tuple[str, str, str]] = [
    # (raw_dir_name, short_id, human_label)
    ("qwen-qwen-2.5-7b-instruct",            "qwen-7b",       "Qwen2.5-7B-Instruct"),
    ("qwen-qwen3-coder-30b-a3b-instruct",    "qwen3-30b",     "Qwen3-Coder-30B-A3B"),
    ("meta-llama-llama-3.3-70b-instruct",    "llama-70b",     "Llama-3.3-70B-Instruct"),
    ("deepseek-deepseek-chat",               "deepseek-v3",   "DeepSeek-V3"),
    ("openai-gpt-4o-mini",                   "gpt-4o-mini",   "GPT-4o-mini"),
    ("anthropic-claude-3.5-haiku",           "claude-3.5",    "Claude-3.5-Haiku"),
    ("google-gemini-3-flash-preview",        "gemini-3-fl",   "Gemini-3-Flash-Preview"),
]

REPOS: list[str] = [
    "gorilla-mux",
    "google-uuid",
    "spf13-cobra",
    "burntsushi-toml",
    "gin-gonic-gin",
    "etcd-io-bbolt",
    "hashicorp-raft",
    "restic-restic",
]

CONFIGS: list[str] = [
    "full",
    "no-types",
    "no-smart-diff",
    "no-structured-feedback",
    "no-pruning",
    "no-coverage",
]

RUNS = (1, 2, 3)


def _safe(d: dict[str, Any], path: list[str], default: Any = None) -> Any:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def load_one(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    files = data.get("files", []) or []
    successful_files = sum(1 for f in files if f.get("status") == "success")
    return {
        "model_dir":           path.parents[1].name,
        "repo":                path.parents[0].name,
        "config":              _safe(data, ["config", "ablation_config"], "?"),
        "run":                 _safe(data, ["config", "run_index"], 0),
        "duration_s":          data.get("duration_seconds", 0.0),
        "files_processed":     _safe(data, ["totals", "files_processed"], 0),
        "files_successful":    successful_files,
        "tests_generated":     _safe(data, ["totals", "tests_generated"], 0),
        "tests_validated":     _safe(data, ["totals", "tests_validated"], 0),
        "tests_cached":        _safe(data, ["totals", "tests_cached"], 0),
        "diff_cov_pct":        _safe(data, ["totals", "diff_coverage_pct"], 0),
        "branch_cov_pct":      _safe(data, ["totals", "branch_coverage_pct"], 0),
        "branches_covered":    _safe(data, ["totals", "branches_covered"], 0),
        "branches_total":      _safe(data, ["totals", "branches_total"], 0),
        "ep_covered":          _safe(data, ["totals", "error_paths_covered"], 0),
        "ep_total":            _safe(data, ["totals", "error_paths_total"], 0),
        "mutations_killed":    _safe(data, ["totals", "mutations_killed"], 0),
        "mutations_total":     _safe(data, ["totals", "mutations_total"], 0),
        "prompt_tokens":       _safe(data, ["totals", "prompt_tokens"], 0),
        "completion_tokens":   _safe(data, ["totals", "completion_tokens"], 0),
        "tok_per_test":        _safe(data, ["totals", "token_efficiency_tokens_per_test"], 0),
        "nat_test_count":      _safe(data, ["totals", "naturalness", "test_count"], 0),
        "nat_assert_ratio":    _safe(data, ["totals", "naturalness", "assertion_ratio"], 0),
        "nat_no_assert_pct":   _safe(data, ["totals", "naturalness", "no_assertions_pct"], 0),
        "nat_dup_assert_pct":  _safe(data, ["totals", "naturalness", "duplicate_assertions_pct"], 0),
        "nat_nil_assert_pct":  _safe(data, ["totals", "naturalness", "nil_only_assertions_pct"], 0),
        "nat_err_assert_pct": _safe(data, ["totals", "naturalness", "error_assertions_pct"], 0),
        "nat_test_name":       _safe(data, ["totals", "naturalness", "test_name_score"], 0),
        "nat_var_name":        _safe(data, ["totals", "naturalness", "var_name_score"], 0),
        "files_raw":           files,
        "_path":               str(path),
    }


def iter_rows() -> Iterable[dict[str, Any]]:
    for raw_dir, short_id, _label in MODELS:
        for repo in REPOS:
            for config in CONFIGS:
                for run in RUNS:
                    p = RAW_DIR / raw_dir / repo / f"{config}-run{run}.json"
                    if not p.exists():
                        continue
                    row = load_one(p)
                    row["model_id"] = short_id
                    row["model_dir"] = raw_dir
                    yield row


def collect() -> list[dict[str, Any]]:
    rows = list(iter_rows())
    return rows


def model_label(short_id: str) -> str:
    for _, sid, lbl in MODELS:
        if sid == short_id:
            return lbl
    return short_id


if __name__ == "__main__":
    rows = collect()
    print(f"Loaded {len(rows)} reports", file=sys.stderr)
    by_model: dict[str, int] = {}
    for r in rows:
        by_model[r["model_id"]] = by_model.get(r["model_id"], 0) + 1
    for sid in (m[1] for m in MODELS):
        print(f"  {sid:14s} {by_model.get(sid, 0):4d}", file=sys.stderr)
    expected = len(MODELS) * len(REPOS) * len(CONFIGS) * len(RUNS)
    print(f"Expected: {expected}", file=sys.stderr)
