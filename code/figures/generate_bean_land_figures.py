from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "paper" / "figures"
CSV = ROOT / "results" / "Q1" / "experiments" / "round3" / "tables" / "bean_land_value_sensitivity.csv"

PRIMARY = "#1A6FC4"
ACCENT = "#E28E2C"
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


df = pd.read_csv(CSV, encoding="utf-8-sig")
beta = df["beta_cny_per_mu"].to_numpy()
bean_share = df["bean_area_share"].to_numpy() * 100
profit = df["real_profit_cny"].to_numpy() / 1e4

# 图A：β → 豆类面积占比
fig, ax = plt.subplots(figsize=(4.4, 3.0))
ax.plot(beta, bean_share, marker="o", color=PRIMARY)
ax.set_xlabel("豆类地力价值 β（元/亩）")
ax.set_ylabel("豆类面积占比（%）")
ax.set_xticks(beta)
style(ax)
fig.tight_layout()
save(fig, "q1_bean_land_area_share")

# 图B：β → 真实净收益
fig, ax = plt.subplots(figsize=(4.4, 3.0))
ax.plot(beta, profit, marker="s", color=ACCENT)
ax.set_xlabel("豆类地力价值 β（元/亩）")
ax.set_ylabel("真实净收益（万元）")
ax.set_xticks(beta)
style(ax)
fig.tight_layout()
save(fig, "q1_bean_land_profit")

print("done")
