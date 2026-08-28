from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "paper/figures"
TAB = ROOT / "paper/tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

PRIMARY = "#1A6FC4"
PRIMARY_LIGHT = "#5B9BD5"
PRIMARY_PALE = "#B4D4F0"
BASELINE = "#767676"
POSITIVE = "#2E9E44"
NEGATIVE = "#E53935"
ACCENT = "#E28E2C"
PURPLE = "#7B5FD6"
TEXT = "#333333"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DengXian", "Noto Sans CJK SC", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "svg.fonttype": "none",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
})


def style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#D8D8D8", linewidth=0.6, alpha=0.65)
    ax.set_axisbelow(True)


def save(fig, stem):
    fig.savefig(FIG / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(FIG / f"{stem}.png", dpi=320, bbox_inches="tight")
    plt.close(fig)


def write_latex_table(df: pd.DataFrame, path: Path, decimals: int = 2):
    def cell(value):
        if isinstance(value, (float, np.floating)):
            return f"{value:.{decimals}f}"
        return str(value).replace("%", r"\%").replace("_", r"\_")
    cols = "l" * len(df.columns)
    lines = [r"\begin{tabular}{" + cols + "}", r"\toprule",
             " & ".join(cell(c) for c in df.columns) + r" \\", r"\midrule"]
    lines.extend(" & ".join(cell(v) for v in row) + r" \\" for row in df.itertuples(index=False, name=None))
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def q1():
    metrics = json.loads((ROOT / "results/Q1/experiments/round2/metrics/q1_metrics.json").read_text())
    summary = json.loads((ROOT / "results/Q1/experiments/round2/run_summary.json").read_text())
    base = {m["metrics_summary"]["alpha"]: m["metrics_summary"]["cumulative_profit"]
            for m in summary["methods"] if m["role"] == "usable_baseline"}
    rows = metrics["management_grid"]
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.4), sharey=True)
    all_profit_values = list(base.values()) + [r["cumulative_profit"] for r in rows]
    shared_ymax = max(all_profit_values) / 1e4 * 1.18
    for ax, alpha, panel in zip(axes, [0.5, 0.0], ["(a) 半价销售模式", "(b) 滞销模式"]):
        vals = [base[alpha]] + [r["cumulative_profit"] for r in rows if r["alpha"] == alpha]
        vals = np.array(vals) / 1e4
        labels = ["Baseline", "无最小占比", "10%最小占比"]
        colors = [BASELINE, PRIMARY_LIGHT, PRIMARY]
        bars = ax.bar(labels, vals, color=colors, edgecolor="white", width=0.66)
        ax.set_title(panel, loc="center", pad=8, fontsize=9)
        ax.set_ylabel("七年累计净收益（万元）" if alpha == 0.5 else "")
        ax.set_ylim(0, shared_ymax)
        style(ax)
        for bar, value in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, value + max(vals)*0.025, f"{value:.1f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    save(fig, "q1_cumulative_profit_comparison")

    table_rows = []
    for r in sorted(rows, key=lambda item: item["alpha"], reverse=True):
        table_rows.append({"销售模式": "半价销售模式" if r["alpha"] == 0.5 else "滞销模式", "配置": r["config"],
                           "累计收益(元)": r["cumulative_profit"], "MIP Gap(%)": 100*r["mip_gap"],
                           "作物数": r["unique_crop_count"], "H1(%)": 100*r["top1_area_share"],
                           "H3(%)": 100*r["top3_area_share"], "违反数": r["violations"]})
    df = pd.DataFrame(table_rows)
    df.to_csv(TAB / "q1_core_results.csv", index=False, encoding="utf-8-sig")
    write_latex_table(df, TAB / "q1_core_results.tex")


def q2():
    metrics = json.loads((ROOT / "results/Q2/experiments/round3/metrics/q2_metrics.json").read_text())
    rows = metrics["paired_test"]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.6), sharey=False)
    names = ["平均收益", "5%分位数", "最差5%均值"]
    keys = ["mean_profit", "q05_profit", "lower_tail_mean"]
    for ax, alpha, panel in zip(axes, [0.5, 0.0], ["(a) 半价销售模式", "(b) 滞销模式"]):
        main = next(r for r in rows if r["method"] == "Main" and r["alpha"] == alpha)
        base = next(r for r in rows if r["method"] == "Baseline" and r["alpha"] == alpha)
        x = np.arange(3); w = 0.34
        ax.bar(x-w/2, [base[k]/1e4 for k in keys], w, color=BASELINE, label="Baseline")
        ax.bar(x+w/2, [main[k]/1e4 for k in keys], w, color=PRIMARY, label="Q2-M1")
        ax.set_xticks(x, names)
        ax.set_ylabel("七年累计净收益（万元）")
        ax.set_title(panel, loc="center", pad=8, fontsize=9)
        style(ax)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.01))
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "q2_expected_tail_comparison")

    robust = json.loads((ROOT / "robustness/Q2/q2_robustness_summary.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.5))
    for ax, alpha, panel in zip(axes, [0.5, 0.0], ["(a) 半价销售模式", "(b) 滞销模式"]):
        vals = [next(e for e in r["evaluations"] if e["alpha"] == alpha)["paired_mean_difference"] / 1e4 for r in robust["seed_results"]]
        seeds = [str(r["seed"]) for r in robust["seed_results"]]
        colors = [POSITIVE if v >= 0 else NEGATIVE for v in vals]
        ax.bar(seeds, vals, color=colors, width=0.62)
        ax.axhline(0, color=TEXT, linewidth=0.9)
        ax.set_xlabel("随机种子")
        ax.set_ylabel("主方法减 Baseline（万元）")
        ax.set_title(panel, loc="center", pad=8, fontsize=9)
        style(ax)
        for i, v in enumerate(vals): ax.text(i, v + max(abs(np.array(vals)))*0.05, f"{v:.1f}", ha="center", fontsize=8)
    fig.tight_layout()
    save(fig, "q2_seed_mean_profit_difference")

    df = pd.DataFrame(rows)[["method", "alpha", "mean_profit", "q05_profit", "lower_tail_mean", "minimum_profit", "profit_std", "loss_probability", "constraint_violations"]]
    df.to_csv(TAB / "q2_risk_metrics.csv", index=False, encoding="utf-8-sig")
    write_latex_table(df, TAB / "q2_risk_metrics.tex")


def q3():
    metrics = json.loads((ROOT / "results/Q3/experiments/round2/metrics/q3_metrics.json").read_text())
    half = [r for r in metrics["comparison"] if r["alpha"] == 0.5]
    order = ["weak", "medium", "strong"]
    half = [next(r for r in half if r["strength"] == s) for s in order]
    x = np.arange(3)
    fig, axes = plt.subplots(2, 1, figsize=(6.4, 5.8), sharex=True, gridspec_kw={"hspace": 0.14})
    axes[0].plot(x, [r["q3_mean_profit"]/1e4 for r in half], color=PRIMARY, marker="o", label="平均收益")
    axes[0].plot(x, [r["q3_q05_profit"]/1e4 for r in half], color=ACCENT, marker="s", linestyle="--", label="5%分位数")
    axes[0].set_ylabel("累计净收益（万元）")
    axes[0].set_title("(a) 收益水平与下尾位置", loc="center", pad=8, fontsize=9)
    axes[0].legend(frameon=False, ncol=2)
    style(axes[0])
    axes[1].plot(x, [r["q3_profit_std"]/1e4 for r in half], color=PURPLE, marker="D")
    axes[1].set_ylabel("收益标准差（万元）")
    axes[1].set_xlabel("模拟关系强度")
    axes[1].set_title("(b) 收益波动", loc="center", pad=8, fontsize=9)
    axes[1].set_xticks(x, ["弱（0.15）", "中（0.35）", "强（0.55）"])
    style(axes[1])
    save(fig, "q3_relationship_strength_sensitivity")

    macro = metrics["macro_micro_attribution"]
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.axvspan(80, 100, ymin=0.0, ymax=1/1.2, color="#EAF5EC", zorder=0)
    ax.fill_between([70, 80], 1.0, 1.2, color="#FBEAEA", zorder=0)
    ax.fill_between([70, 80], 0.0, 1.0, color="#F3F3F3", zorder=0)
    ax.fill_between([80, 100], 1.0, 1.2, color="#F3F3F3", zorder=0)
    for row, color in zip(macro["pairwise_checks"], [PRIMARY, ACCENT, PURPLE]):
        ax.scatter(100*row["crop_area_vector_similarity"], 100*row["relative_profit_difference"], s=70, color=color, edgecolor="white", linewidth=0.8)
        ax.annotate(f"{row['left']}-{row['right']}", (100*row["crop_area_vector_similarity"], 100*row["relative_profit_difference"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.axvline(80, color=BASELINE, linestyle="--", linewidth=1)
    ax.axhline(1, color=NEGATIVE, linestyle=":", linewidth=1.2)
    ax.text(89.5, 0.88, "微观等价平移区\n不触发 Fallback", ha="center", va="center", color="#236B32", fontsize=9)
    ax.text(75, 1.10, "结构性跳变区\n触发 Fallback", ha="center", va="center", color="#A52222", fontsize=8)
    ax.text(80.2, 0.03, "相似度阈值 80%", rotation=90, va="bottom", color=BASELINE, fontsize=7)
    ax.text(70.4, 1.01, "收益偏差阈值 1%", va="bottom", color=NEGATIVE, fontsize=7)
    ax.set_xlim(70, 100)
    ax.set_ylim(0, 1.2)
    ax.set_xlabel("41维作物总面积结构相似度（%）")
    ax.set_ylabel("七年期望收益相对偏差（%）")
    style(ax)
    save(fig, "q3_macro_structure_stability")

    corr = json.loads((ROOT / "results/Q3/experiments/round2/metrics/q3_correlation_checks.json").read_text())
    fig, axes = plt.subplots(3, 2, figsize=(7.2, 8.2))
    labels = ["销量增长", "亩产增长", "价格增长"]
    image = None
    for i, strength in enumerate(order):
        for j, (key, subtitle) in enumerate([("target_matrix", "目标"), ("empirical_realized_economic_matrix", "经验")]):
            matrix = np.array(corr[strength][key])
            cmap = plt.get_cmap("RdBu_r")
            norm = plt.Normalize(vmin=-0.35, vmax=0.35)
            image = axes[i, j].imshow(matrix, cmap=cmap, norm=norm)
            axes[i, j].set_xticks(range(3), labels, rotation=25, ha="right")
            axes[i, j].set_yticks(range(3), labels)
            if i == 0:
                axes[i, j].text(0.5, 1.09, subtitle, transform=axes[i, j].transAxes, ha="center", fontsize=9)
            if j == 0:
                axes[i, j].text(-0.37, 0.5, strength, transform=axes[i, j].transAxes, va="center", rotation=90, fontsize=9)
            for a in range(3):
                for b in range(3):
                    value = matrix[a, b]
                    red, green, blue, _ = cmap(norm(value))
                    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
                    axes[i, j].text(b, a, f"{value:.2f}", ha="center", va="center", fontsize=8,
                                         color="white" if luminance < 0.48 else TEXT)
            axes[i, j].set_frame_on(False)
    fig.subplots_adjust(left=0.13, right=0.80, bottom=0.08, top=0.93, hspace=0.42, wspace=0.38)
    cbar = fig.colorbar(image, ax=axes, fraction=0.035, pad=0.08)
    cbar.set_label("相关系数")
    save(fig, "q3_correlation_matrix_validation")

    df = pd.read_csv(ROOT / "results/Q3/experiments/round2/tables/q3_q2_paired_comparison.csv")
    df = df[df["strength"] == "medium"]
    df.to_csv(TAB / "q3_medium_q2_comparison.csv", index=False, encoding="utf-8-sig")
    write_latex_table(df, TAB / "q3_medium_q2_comparison.tex")
    corr_rows = [{"强度": s, "最小特征值": corr[s]["minimum_eigenvalue"], "最大相关误差": corr[s]["maximum_absolute_correlation_error"], "需求裁剪比例": corr[s]["demand_response_clipping_ratio"]} for s in order]
    cdf = pd.DataFrame(corr_rows)
    cdf.to_csv(TAB / "q3_correlation_checks.csv", index=False, encoding="utf-8-sig")
    write_latex_table(cdf, TAB / "q3_correlation_checks.tex", decimals=4)


def main():
    q1(); q2(); q3()


if __name__ == "__main__":
    main()
