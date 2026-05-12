#!/usr/bin/env python3
"""
Generate a human-readable RUN-INFO.md for a model's results directory.

Usage:
    python3 scripts/generate-run-info.py <results-model-dir>

Reads:
    <model-dir>/benchmark-index.json
    <model-dir>/<repo>/<config>-runN.json

Writes:
    <model-dir>/RUN-INFO.md
"""
import json
import os
import sys
import glob
from datetime import datetime

if len(sys.argv) != 2:
    sys.exit(f"usage: {sys.argv[0]} <results-model-dir>")

model_dir = sys.argv[1]
index_path = os.path.join(model_dir, "benchmark-index.json")
if not os.path.isfile(index_path):
    sys.exit(f"benchmark-index.json not found in {model_dir}")

with open(index_path, encoding="utf-8") as f:
    idx = json.load(f)

model = idx["model"]
ts = idx["timestamp"]

# Collect per-repo + per-config stats
repo_stats = {}
provider_seen = set()
allow_fallbacks_seen = set()
temperature_seen = set()
seed_seen = set()
total_prompt = 0
total_completion = 0
total_runs = 0
total_validated = 0
total_runs_success = 0
total_validated_tests = 0

for repo_entry in idx["results"]:
    repo_name = repo_entry["repo"]["Name"]
    base = repo_entry["repo"]["Base"]
    head = repo_entry["repo"]["Head"]
    runs = repo_entry["runs"]
    repo_stats[repo_name] = {
        "base": base,
        "head": head,
        "configs": {},
        "duration_s": repo_entry["duration"] / 1e9,
        "n_runs": len(runs),
    }

    for run in runs:
        cfg = run["config"]
        run_idx = run["run_index"]
        rp = os.path.join(model_dir, repo_name, os.path.basename(run["report_path"]))
        if not os.path.isfile(rp):
            continue
        with open(rp, encoding="utf-8") as rf:
            rdata = json.load(rf)
        t = rdata.get("totals", {})
        validated = t.get("tests_validated", 0)
        generated = t.get("tests_generated", 0)
        files = t.get("files_processed", 0)
        bcov = t.get("branch_coverage_pct")
        dcov = t.get("diff_coverage_pct")
        prompt_tok = t.get("prompt_tokens", 0)
        compl_tok = t.get("completion_tokens", 0)

        cfg_data = repo_stats[repo_name]["configs"].setdefault(cfg, {
            "runs": 0, "validated": 0, "generated": 0,
            "files": [], "branch_pct": [], "diff_pct": [],
            "prompt_tok": 0, "completion_tok": 0,
        })
        cfg_data["runs"] += 1
        cfg_data["validated"] += validated
        cfg_data["generated"] += generated
        cfg_data["files"].append(files)
        if isinstance(bcov, (int, float)):
            cfg_data["branch_pct"].append(bcov)
        if isinstance(dcov, (int, float)):
            cfg_data["diff_pct"].append(dcov)
        cfg_data["prompt_tok"] += prompt_tok
        cfg_data["completion_tok"] += compl_tok

        total_prompt += prompt_tok
        total_completion += compl_tok
        total_runs += 1
        total_validated_tests += validated
        if validated > 0:
            total_runs_success += 1

        cfg_obj = rdata.get("config", {})
        prov = cfg_obj.get("provider")
        if isinstance(prov, list):
            provider_seen.update(prov)
        elif isinstance(prov, str) and prov:
            provider_seen.add(prov)
        if "provider_allow_fallbacks" in cfg_obj:
            allow_fallbacks_seen.add(cfg_obj["provider_allow_fallbacks"])
        if cfg_obj.get("temperature") is not None:
            temperature_seen.add(cfg_obj["temperature"])
        if cfg_obj.get("seed") is not None:
            seed_seen.add(cfg_obj["seed"])

# Compose markdown
lines = []
lines.append(f"# Прогон {model}")
lines.append("")
lines.append(f"**Дата завершения:** {ts}  ")
lines.append(f"**Всего репозиториев:** {len(repo_stats)}  ")
lines.append(f"**Всего ablation-запусков:** {total_runs}  ")
lines.append(
    f"**Успешных запусков (≥1 валидный тест):** {total_runs_success}/{total_runs} "
    f"({total_runs_success/total_runs*100:.1f} %)  "
)
lines.append(f"**Всего валидных тестов:** {total_validated_tests}  ")
total_tok = total_prompt + total_completion
lines.append(f"**Токенов всего:** prompt={total_prompt:,} + completion={total_completion:,} = {total_tok:,}")
lines.append("")

lines.append("## Параметры запуска")
lines.append("")
if provider_seen:
    lines.append(f"- **OpenRouter provider pin:** `{', '.join(sorted(provider_seen))}`")
else:
    lines.append(f"- **OpenRouter provider pin:** не задан (auto-routing; для моделей с единственным провайдером это no-op)")
af = sorted(allow_fallbacks_seen)
lines.append(f"- **provider.allow_fallbacks:** {af if af else '(default)'}")
lines.append(f"- **temperature:** `{sorted(temperature_seen)}`")
lines.append(f"- **seed:** `{sorted(seed_seen)}` (seed-base + run_index - 1)")
lines.append("- **ablation-конфиги:** full, no-coverage, no-pruning, no-smart-diff, no-structured-feedback, no-types")
lines.append("- **runs/config:** 3 (различаются seed)")
lines.append("- **окружение:** WSL2 / Ubuntu, Go 1.24, Clash Verge TUN")
lines.append("")

lines.append("## Сводка по репозиториям")
lines.append("")
lines.append("Колонки:")
lines.append("- **успешных runs** — число запусков (из 18), где агент сгенерил ≥1 валидный тест")
lines.append("- **валидных тестов** — суммарное число валидных тестов по всем 18 запускам")
lines.append("- **средн. branch% / diff%** — среднее по тем запускам, где coverage был посчитан")
lines.append("")
lines.append("| repo | base..head | runs | успешных runs | валидных тестов | средн. branch% | средн. diff% |")
lines.append("|------|-----------|-----:|--------------:|----------------:|---------------:|-------------:|")

# Re-walk per-run files to count successful runs distinctly from validated test count
import glob as _glob
for repo_name in sorted(repo_stats.keys()):
    rs = repo_stats[repo_name]
    bcov_all = []
    dcov_all = []
    n_val_tests = 0
    n_runs_success = 0
    n_runs_total = 0
    for f in _glob.glob(os.path.join(model_dir, repo_name, "*-run*.json")):
        with open(f, encoding="utf-8") as rf:
            rd = json.load(rf)
        tt = rd.get("totals", {})
        v = tt.get("tests_validated", 0)
        n_val_tests += v
        n_runs_total += 1
        if v > 0:
            n_runs_success += 1
        if isinstance(tt.get("branch_coverage_pct"), (int, float)):
            bcov_all.append(tt["branch_coverage_pct"])
        if isinstance(tt.get("diff_coverage_pct"), (int, float)):
            dcov_all.append(tt["diff_coverage_pct"])
    bcov_str = f"{sum(bcov_all)/len(bcov_all):.1f}%" if bcov_all else "—"
    dcov_str = f"{sum(dcov_all)/len(dcov_all):.1f}%" if dcov_all else "—"
    base_short = rs["base"][:8]
    head_short = rs["head"][:8]
    lines.append(
        f"| `{repo_name}` | `{base_short}..{head_short}` "
        f"| {n_runs_total} | {n_runs_success} | {n_val_tests} | {bcov_str} | {dcov_str} |"
    )
lines.append("")

lines.append("## Состав файлов")
lines.append("")
lines.append("```")
lines.append(f"{os.path.basename(model_dir)}/")
lines.append(f"├─ benchmark-index.json       # сводный индекс по всем 8 репо")
lines.append(f"├─ RUN-INFO.md                # этот файл")
for repo_name in sorted(repo_stats.keys()):
    n = len(glob.glob(os.path.join(model_dir, repo_name, "*-run*.json")))
    lines.append(f"├─ {repo_name}/")
    lines.append(f"│  ├─ repo.json               # сводка по репо ({n} ablation-runs)")
    lines.append(f"│  └─ <config>-run<N>.json    # 6×3 = 18 отчётов агента")
lines.append("```")
lines.append("")

lines.append("## Воспроизведение")
lines.append("")
lines.append("```bash")
if provider_seen:
    lines.append(f"PROVIDER={','.join(sorted(provider_seen))} \\")
    lines.append(f"  bash scripts/run-model.sh {model} 3 60")
else:
    lines.append(f"bash scripts/run-model.sh {model} 3 60")
    lines.append("# (без --provider — единственный провайдер на OpenRouter)")
lines.append("```")
lines.append("")
lines.append("Подробное описание методологии — в `план.md`, §6 (выбор репозиториев), §10 (контроль воспроизводимости).")
lines.append("")

out_path = os.path.join(model_dir, "RUN-INFO.md")
with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines))

print(f"Wrote {out_path}")
