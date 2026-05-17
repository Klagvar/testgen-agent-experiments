"""Generate all five chapter-5 figures (G1..G5) as monochrome PNG.

All graphics are intentionally restrained: monochrome / grayscale palette,
pdfTeX-friendly fonts, no decorative elements. Each figure is saved both as
PNG (300 dpi) for the printed thesis and as PDF (vector) for inclusion via
\\includegraphics in LaTeX.

Outputs:
  результаты/графики/G1-capability-ladder.{png,pdf}
  результаты/графики/G2-component-importance.{png,pdf}
  результаты/графики/G3-pruner-criticality.{png,pdf}
  результаты/графики/G4-pareto-cost-quality.{png,pdf}
  результаты/графики/G5-mutation-score.{png,pdf}
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from _aggregate import collect, MODELS, CONFIGS, model_label  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "результаты" / "графики"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MUT_DIR = ROOT / "результаты" / "mutation-microexp"

# ── Pricing duplicated from 10-token-efficiency.py to keep this script standalone
PRICING = {
    "qwen-7b":      (0.04, 0.04),
    "qwen3-30b":    (0.10, 0.30),
    "llama-70b":    (0.59, 0.79),
    "deepseek-v3":  (0.27, 1.10),
    "gpt-4o-mini":  (0.15, 0.60),
    "claude-3.5":   (0.80, 4.00),
    "gemini-3-fl":  (0.30, 2.50),
}

# Mutation-experiment model dir names mapped to short ids used in the cube.
MUT_MODEL_MAP = {
    "qwen-qwen-2.5-7b-instruct":         "qwen-7b",
    "qwen-qwen3-coder-30b-a3b-instruct": "qwen3-30b",
    "meta-llama-llama-3.3-70b-instruct": "llama-70b",
    "deepseek-deepseek-chat":            "deepseek-v3",
    "openai-gpt-4o-mini":                "gpt-4o-mini",
    "anthropic-claude-3.5-haiku":        "claude-3.5",
    "google-gemini-3-flash-preview":     "gemini-3-fl",
}

REPOS = [
    "gorilla-mux", "google-uuid", "spf13-cobra", "burntsushi-toml",
    "gin-gonic-gin", "etcd-io-bbolt", "hashicorp-raft", "restic-restic",
]

# Restrained colour palette (legible after b/w printing too).
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "grid.color": "#888888",
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#222222",
    "xtick.color": "#222222",
    "ytick.color": "#222222",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
})

# Semantic palette (ColorBrewer-inspired, print-safe contrast).
PRIMARY    = "#1f5da6"   # main series (run_success, full, mean)
SECONDARY  = "#e07a1f"   # secondary series (file_macro, aggregated)
POSITIVE   = "#2c7a3a"   # "component is useful" / "Pareto-optimal"
NEGATIVE   = "#c0392b"   # "component hurts" / "ablated"
ACCENT     = "#b88412"   # frontier / highlight (muted gold)
NEUTRAL    = "#7f7f7f"   # dominated / neutral annotation
GREY_DARK  = "#222222"
GREY_MID   = "#666666"
GREY_LIGHT = "#BBBBBB"
GREY_FILL  = "#DDDDDD"


def save(fig: plt.Figure, name: str) -> None:
    out_png = OUT_DIR / f"{name}.png"
    out_pdf = OUT_DIR / f"{name}.pdf"
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)
    print(f"  wrote {out_png.relative_to(ROOT)}")
    print(f"  wrote {out_pdf.relative_to(ROOT)}")


# ── helpers ──────────────────────────────────────────────────────────────────

def aggregate_model_metrics(rows):
    """Return {sid: {file_macro, file_micro, run_success, validated_tests}}."""
    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_id"]].append(r)
    out = {}
    for raw_dir, sid, lbl in MODELS:
        rs = by_model.get(sid, [])
        if not rs:
            continue
        per_row_rate = []
        run_ok = 0
        total_ok = 0
        total_all = 0
        v_tests = 0
        for r in rs:
            if r["files_processed"] > 0:
                per_row_rate.append(r["files_successful"] / r["files_processed"] * 100)
                total_ok += r["files_successful"]
                total_all += r["files_processed"]
            else:
                per_row_rate.append(0.0)
            if r["tests_validated"] > 0:
                run_ok += 1
            v_tests += r["tests_validated"]
        out[sid] = {
            "label": lbl,
            "file_macro": sum(per_row_rate) / len(per_row_rate) if per_row_rate else 0.0,
            "file_micro": total_ok / total_all * 100 if total_all else 0.0,
            "run_success": run_ok / len(rs) * 100,
            "validated_tests": v_tests,
        }
    return out


def aggregate_per_config(rows):
    """Return {(sid, cfg): file_macro %} and {(sid, cfg): run_success %}."""
    idx = defaultdict(list)
    for r in rows:
        idx[(r["model_id"], r["config"])].append(r)
    fm, rs = {}, {}
    for (sid, cfg), lst in idx.items():
        per_row_rate = []
        run_ok = 0
        for r in lst:
            if r["files_processed"] > 0:
                per_row_rate.append(r["files_successful"] / r["files_processed"] * 100)
            else:
                per_row_rate.append(0.0)
            if r["tests_validated"] > 0:
                run_ok += 1
        fm[(sid, cfg)] = sum(per_row_rate) / len(per_row_rate) if per_row_rate else 0.0
        rs[(sid, cfg)] = run_ok / len(lst) * 100 if lst else 0.0
    return fm, rs


# ── G1 — capability ladder (horizontal bars) ─────────────────────────────────

def plot_g1(rows):
    metrics = aggregate_model_metrics(rows)
    ranked = sorted(metrics.items(), key=lambda kv: kv[1]["run_success"])
    labels = [m["label"] for _, m in ranked]
    vals = [m["run_success"] for _, m in ranked]
    fmacro = [m["file_macro"] for _, m in ranked]

    # Tier colour: floor/mid-tier/frontier — by run_success.
    def tier_color(rs: float) -> str:
        if rs < 25:
            return NEUTRAL
        if rs < 80:
            return PRIMARY
        return ACCENT

    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    y = np.arange(len(labels))
    bar_h = 0.62
    fm_h = 0.22

    rs_colors = [tier_color(v) for v in vals]
    rs_face = [c + "66" for c in rs_colors]  # 40 % alpha (RGBA)
    ax.barh(y + fm_h / 1.5, vals, color=rs_face, edgecolor=rs_colors,
            linewidth=1.1, height=bar_h - fm_h)
    ax.barh(y - bar_h / 2 + fm_h / 2, fmacro, color=SECONDARY,
            edgecolor=SECONDARY, linewidth=0.0, height=fm_h)

    for i, (v, fm) in enumerate(zip(vals, fmacro)):
        ax.text(v + 1.0, i + fm_h / 1.5, f"{v:.1f}%", va="center", ha="left",
                fontsize=10, color=GREY_DARK, fontweight="bold")
        ax.text(fm + 1.0, i - bar_h / 2 + fm_h / 2, f"{fm:.1f}%",
                va="center", ha="left", fontsize=8.5, color=SECONDARY)

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 112)
    ax.set_ylim(-0.7, len(labels) - 0.3)
    ax.set_xlabel("Доля успешных запусков, % (run_success)")
    ax.set_title("Иерархия моделей по успешности генерации\n(8 проектов × 6 конфигураций × 3 запуска = 144 запуска на модель)",
                 fontsize=11.5)

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=ACCENT + "66", ec=ACCENT, lw=1.1),
        plt.Rectangle((0, 0), 1, 1, color=PRIMARY + "66", ec=PRIMARY, lw=1.1),
        plt.Rectangle((0, 0), 1, 1, color=NEUTRAL + "66", ec=NEUTRAL, lw=1.1),
        plt.Rectangle((0, 0), 1, 1, color=SECONDARY),
    ]
    ax.legend(legend_handles,
              ["frontier (run_success ≥ 80 %)",
               "mid-tier (25 % ≤ run_success < 80 %)",
               "floor (run_success < 25 %)",
               "file_macro — успешных файлов на запуск"],
              loc="lower right", frameon=False, fontsize=8.8)

    ax.axhline(0.5, color=GREY_LIGHT, linewidth=0.8)
    ax.axhline(5.5, color=GREY_LIGHT, linewidth=0.8)

    save(fig, "G1-capability-ladder")


# ── G2 — component importance (mean Δ vs full + min/max whiskers) ────────────

def plot_g2(rows):
    fm, _ = aggregate_per_config(rows)
    components = [c for c in CONFIGS if c != "full"]
    component_labels = {
        "no-types":              "no-types\n(AST-типы)",
        "no-smart-diff":         "no-smart-\ndiff",
        "no-structured-feedback": "no-structured-\nfeedback",
        "no-pruning":            "no-pruning\n(AST-фильтр)",
        "no-coverage":           "no-coverage\n(cover-loop)",
    }

    means, mins, maxs = [], [], []
    for cfg in components:
        deltas = []
        for raw_dir, sid, lbl in MODELS:
            full_v = fm.get((sid, "full"), 0.0)
            d = fm.get((sid, cfg), 0.0) - full_v
            deltas.append(d)
        means.append(statistics.mean(deltas))
        mins.append(min(deltas))
        maxs.append(max(deltas))

    order = sorted(range(len(components)), key=lambda i: means[i])
    components = [components[i] for i in order]
    means = [means[i] for i in order]
    mins = [mins[i] for i in order]
    maxs = [maxs[i] for i in order]

    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    x = np.arange(len(components))
    err_low = [m - lo for m, lo in zip(means, mins)]
    err_high = [hi - m for m, hi in zip(means, maxs)]

    bar_colors = [POSITIVE if m < 0 else NEGATIVE for m in means]
    bar_face = [c + "55" for c in bar_colors]  # 33 % alpha
    ax.bar(x, means, color=bar_face, edgecolor=bar_colors, linewidth=1.3, width=0.55)
    ax.errorbar(x, means, yerr=[err_low, err_high], fmt="none",
                ecolor=GREY_DARK, capsize=6, capthick=1.0, elinewidth=1.0)

    for xi, m in zip(x, means):
        col = POSITIVE if m < 0 else NEGATIVE
        ax.text(xi, m - 1.8 if m < 0 else m + 1.8, f"{m:+.1f}",
                ha="center", va="top" if m < 0 else "bottom",
                fontsize=10, fontweight="bold", color=col)

    ax.axhline(0, color=GREY_DARK, linewidth=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([component_labels[c] for c in components], fontsize=9.5)
    ax.set_ylabel("Δ file_macro vs full, п.п.")
    ax.set_title("Вклад компонент архитектуры в качество генерации\n(столбец — среднее по 7 моделям, усы — min/max разброс)",
                 fontsize=11.5)
    ax.set_ylim(min(mins) - 8, max(maxs) + 8)

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=POSITIVE + "55", ec=POSITIVE, lw=1.3),
        plt.Rectangle((0, 0), 1, 1, color=NEGATIVE + "55", ec=NEGATIVE, lw=1.3),
    ]
    ax.legend(legend_handles,
              ["компонент полезен (отключение ↓ качества)",
               "компонент мешает (отключение ↑ качества)"],
              loc="upper left", frameon=False, fontsize=9)

    save(fig, "G2-component-importance")


# ── G3 — pruner criticality (paired bars: full vs no-pruning per model) ──────

def plot_g3(rows):
    fm, _ = aggregate_per_config(rows)
    metrics = aggregate_model_metrics(rows)
    ordered = sorted(metrics.items(), key=lambda kv: -kv[1]["file_macro"])

    labels = [m["label"] for _, m in ordered]
    full_vals = [fm[(sid, "full")] for sid, _ in ordered]
    np_vals = [fm[(sid, "no-pruning")] for sid, _ in ordered]
    deltas = [np_vals[i] - full_vals[i] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    x = np.arange(len(labels))
    w = 0.36
    ax.bar(x - w / 2, full_vals, width=w, color=POSITIVE, edgecolor=POSITIVE,
           label="full (с AST-pruner)")
    ax.bar(x + w / 2, np_vals, width=w, color=NEGATIVE + "AA",
           edgecolor=NEGATIVE, linewidth=1.0, label="no-pruning (без фильтра)")

    for xi, fv, nv, d in zip(x, full_vals, np_vals, deltas):
        ax.text(xi - w / 2, fv + 1.0, f"{fv:.0f}", ha="center", fontsize=9, color=POSITIVE)
        ax.text(xi + w / 2, nv + 1.0, f"{nv:.0f}", ha="center", fontsize=9, color=NEGATIVE)
        y_arrow = max(fv, nv) + 6
        ax.annotate(f"Δ {d:+.1f}", xy=(xi, y_arrow), ha="center", fontsize=9.5,
                    color=GREY_DARK, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9.5)
    ax.set_ylabel("file_macro success rate, %")
    ax.set_ylim(0, max(max(full_vals), max(np_vals)) + 18)
    ax.set_title("Критичность AST-pruner: полная конфигурация против no-pruning",
                 fontsize=11.5)
    ax.legend(loc="upper right", frameon=False, fontsize=10)

    save(fig, "G3-pruner-criticality")


# ── G4 — Pareto cost / quality (log-x scatter) ───────────────────────────────

def plot_g4(rows):
    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_id"]].append(r)

    pts = []
    for raw_dir, sid, lbl in MODELS:
        rs = by_model[sid]
        prompt = sum(r["prompt_tokens"] for r in rs)
        compl = sum(r["completion_tokens"] for r in rs)
        v_tests = sum(r["tests_validated"] for r in rs)
        in_p, out_p = PRICING[sid]
        cost_total = prompt / 1e6 * in_p + compl / 1e6 * out_p
        per_test = cost_total / v_tests if v_tests else None
        run_ok = sum(1 for r in rs if r["tests_validated"] > 0)
        run_succ = run_ok / len(rs) * 100 if rs else 0
        pts.append({"sid": sid, "label": lbl, "cost": per_test,
                    "run_succ": run_succ, "v_tests": v_tests})

    drawable = [p for p in pts if p["cost"] is not None and p["cost"] > 0]
    drawable.sort(key=lambda p: p["cost"])

    pareto = []
    best_q = -1
    for p in drawable:
        if p["run_succ"] > best_q:
            pareto.append(p)
            best_q = p["run_succ"]
    pareto_sids = {p["sid"] for p in pareto}

    fig, ax = plt.subplots(figsize=(9.0, 5.6))

    pareto_x = [p["cost"] for p in pareto]
    pareto_y = [p["run_succ"] for p in pareto]
    ax.plot(pareto_x, pareto_y, "-", color=POSITIVE, linewidth=2.0,
            zorder=2, alpha=0.55)
    # Заштрихуем «недоминируемую» область над линией.
    ax.fill_between(pareto_x, pareto_y, [112] * len(pareto_y),
                    color=POSITIVE, alpha=0.06, zorder=1)

    for p in drawable:
        is_pareto = p["sid"] in pareto_sids
        ax.scatter(p["cost"], p["run_succ"],
                   s=180 if is_pareto else 100,
                   marker="o",
                   edgecolor=POSITIVE if is_pareto else NEUTRAL,
                   facecolor=POSITIVE if is_pareto else "white",
                   linewidth=1.7 if is_pareto else 1.3,
                   zorder=4)

    short_labels = {
        "qwen-7b":      "Qwen-7B",
        "qwen3-30b":    "Qwen3-Coder-30B",
        "llama-70b":    "Llama-3.3-70B",
        "deepseek-v3":  "DeepSeek-V3",
        "gpt-4o-mini":  "GPT-4o-mini",
        "claude-3.5":   "Claude-3.5-Haiku",
        "gemini-3-fl":  "Gemini-3-Flash",
    }
    offsets = {
        "qwen-7b":      ( 14,  10),
        "qwen3-30b":    (  0, -22),
        "llama-70b":    (  0, -22),
        "deepseek-v3":  (  0,  14),
        "gpt-4o-mini":  ( 14,  -4),
        "claude-3.5":   (-14,  10),
        "gemini-3-fl":  (-14,  14),
    }
    halign = {
        "qwen-7b":      "left",
        "qwen3-30b":    "center",
        "llama-70b":    "center",
        "deepseek-v3":  "center",
        "gpt-4o-mini":  "left",
        "claude-3.5":   "right",
        "gemini-3-fl":  "right",
    }
    for p in drawable:
        dx, dy = offsets.get(p["sid"], (10, 10))
        is_pareto = p["sid"] in pareto_sids
        ax.annotate(short_labels[p["sid"]],
                    xy=(p["cost"], p["run_succ"]),
                    xytext=(dx, dy),
                    textcoords="offset points",
                    fontsize=10,
                    ha=halign.get(p["sid"], "left"),
                    fontweight="bold" if is_pareto else "normal",
                    color=POSITIVE if is_pareto else GREY_DARK)

    # Подпись линии Парето — на полпути между Qwen-7B и GPT-4o-mini (вертикальный участок).
    if len(pareto) >= 2:
        # Берём первую дугу — между Qwen-7B и GPT-4o-mini, она идёт почти вертикально.
        x_anchor = pareto_x[0]
        y_anchor = (pareto_y[0] + pareto_y[1]) / 2
        ax.annotate("граница Парето\n(Pareto-frontier)",
                    xy=(x_anchor, y_anchor),
                    xytext=(-78, 4),
                    textcoords="offset points",
                    fontsize=9.5, color=POSITIVE, style="italic",
                    ha="left",
                    arrowprops=dict(arrowstyle="->", color=POSITIVE,
                                    linewidth=0.9, alpha=0.7))

    ax.set_xscale("log")
    ax.set_xlabel("Стоимость одного валидного теста, $/test  (логарифмическая шкала)")
    ax.set_ylabel("Доля успешных запусков, %  (run_success)")
    ax.set_title("Стоимость против качества: какая модель оптимальна по соотношению цена/успех",
                 fontsize=11.5)
    ax.set_ylim(0, 112)
    ax.set_xlim(min(p["cost"] for p in drawable) * 0.55,
                max(p["cost"] for p in drawable) * 1.9)

    from matplotlib.ticker import LogLocator
    ax.xaxis.set_major_locator(LogLocator(base=10.0, numticks=6))
    ax.xaxis.set_minor_locator(LogLocator(base=10.0, subs=(2, 5), numticks=12))

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=POSITIVE,
                   markeredgecolor=POSITIVE, markersize=12,
                   label="Pareto-оптимальная: нет модели, которая\n"
                         "одновременно и дешевле, и качественнее"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="white",
                   markeredgecolor=NEUTRAL, markersize=10,
                   label="доминируемая: есть Pareto-оптимальная\n"
                         "модель, превосходящая её по обоим критериям"),
    ]
    ax.legend(handles=legend_handles, loc="lower right",
              frameon=True, framealpha=0.95, edgecolor=GREY_LIGHT,
              fontsize=9, labelspacing=1.0)

    save(fig, "G4-pareto-cost-quality")


# ── G5 — mutation score (grouped bars per model) ─────────────────────────────

def plot_g5():
    rows = []
    for model_dir, sid in MUT_MODEL_MAP.items():
        scores = []
        killed = total = 0
        cov_repos = 0
        for repo in REPOS:
            p = MUT_DIR / model_dir / repo / "full.json"
            if not p.exists():
                continue
            with p.open(encoding="utf-8") as f:
                d = json.load(f)
            t = d["totals"]["mutations_total"]
            k = d["totals"]["mutations_killed"]
            if t == 0:
                continue
            scores.append(100.0 * k / t)
            killed += k
            total += t
            cov_repos += 1
        if scores:
            rows.append({
                "sid": sid,
                "label": model_label(sid),
                "mean": statistics.mean(scores),
                "agg": 100 * killed / total if total else 0,
                "killed": killed,
                "total": total,
                "n_repos": cov_repos,
                "active": True,
            })
        else:
            rows.append({
                "sid": sid,
                "label": model_label(sid),
                "mean": 0.0,
                "agg": 0.0,
                "killed": 0,
                "total": 0,
                "n_repos": 0,
                "active": False,
            })

    rows.sort(key=lambda r: (not r["active"], -r["mean"]))
    labels = [r["label"] for r in rows]
    means = [r["mean"] for r in rows]
    aggs = [r["agg"] for r in rows]

    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    x = np.arange(len(labels))
    w = 0.36
    ax.bar(x - w / 2, means, width=w, color=PRIMARY, edgecolor=PRIMARY,
           label="среднее по репозиториям")
    ax.bar(x + w / 2, aggs, width=w, color=SECONDARY + "AA",
           edgecolor=SECONDARY, linewidth=1.0,
           label="агрегированное (Σ killed / Σ total)")

    for xi, r, m, a in zip(x, rows, means, aggs):
        if r["active"]:
            ax.text(xi - w / 2, m + 1.2, f"{m:.1f}", ha="center", fontsize=9,
                    color=PRIMARY, fontweight="bold")
            ax.text(xi + w / 2, a + 1.2, f"{a:.1f}", ha="center", fontsize=9,
                    color=SECONDARY, fontweight="bold")
            label_below = f"{r['n_repos']}/8\n({r['killed']}/{r['total']})"
        else:
            ax.text(xi, 6, "нет\nвалидных\nтестов", ha="center", va="bottom",
                    fontsize=9, color=NEUTRAL, style="italic")
            label_below = "0/8"
        ax.text(xi, -8, label_below, ha="center", va="top",
                fontsize=8.3, color=GREY_MID)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right", fontsize=9.5)
    ax.set_ylabel("mutation score, %")
    ax.set_ylim(-22, 112)
    ax.set_title("Мутационная стойкость (целевой прогон 7 × 8, конфигурация full)",
                 fontsize=11.5)
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, -0.20),
              frameon=False, fontsize=10, ncol=2)
    fig.subplots_adjust(bottom=0.30)

    save(fig, "G5-mutation-score")


def main() -> None:
    rows = collect()
    print(f"Loaded {len(rows)} reports from main cube")
    print()
    print("[G1] capability ladder")
    plot_g1(rows)
    print("[G2] component importance")
    plot_g2(rows)
    print("[G3] pruner criticality")
    plot_g3(rows)
    print("[G4] Pareto cost vs quality")
    plot_g4(rows)
    print("[G5] mutation score")
    plot_g5()
    print()
    print("Done. Files in: " + str(OUT_DIR))


if __name__ == "__main__":
    main()
