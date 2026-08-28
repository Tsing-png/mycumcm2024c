from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "paper" / "figures"
TAB = ROOT / "results" / "Q1" / "experiments" / "round2" / "tables"
CLEAN = ROOT / "workspace" / "data_clean"

PRIMARY = "#1A6FC4"
PRIMARY_LIGHT = "#5B9BD5"
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


# ---- load ----
crops = pd.read_csv(CLEAN / "crops.csv", encoding="utf-8-sig")
name = dict(zip(crops.crop_id, crops.crop_name))

half = pd.read_csv(TAB / "q1_m1_alpha05_share10_k3_schedule.csv", encoding="utf-8-sig")
unsold = pd.read_csv(TAB / "q1_m1_alpha0_share0_k3_schedule.csv", encoding="utf-8-sig")
profit = pd.read_csv(TAB / "q1_profit_by_year.csv", encoding="utf-8-sig")


def crop_share(df):
    by_crop = df.groupby("crop_id").area_mu.sum().sort_values(ascending=False)
    return by_crop / by_crop.sum()


half_share = crop_share(half)
unsold_share = crop_share(unsold)

# ============ Figure 1: 各作物累计面积占比 ============
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.8), sharex=True)
for ax, share, title, color in [
    (axes[0], half_share, f"半价销售（{len(half_share)} 种作物）", PRIMARY),
    (axes[1], unsold_share, f"滞销（{len(unsold_share)} 种作物）", ACCENT),
]:
    top = share.head(12).iloc[::-1]
    ax.barh([name.get(int(c), str(c)) for c in top.index], top.values * 100, color=color)
    ax.set_title(title, fontsize=10, color=TEXT)
    ax.set_xlabel("面积占比（%）")
    style(ax)
    ax.set_xlim(0, max(half_share.max(), unsold_share.max()) * 100 * 1.08)
fig.tight_layout()
save(fig, "q1_crop_area_composition")

# ============ Figure 2: 逐年净收益 ============
def series(alpha, config):
    sub = profit[(profit.method_id == "Q1-M1") & (profit.alpha == alpha) & (profit.config == config)]
    return sub.set_index("year").net_profit / 10000  # 万元


def base_series(alpha):
    sub = profit[(profit.method_id == "Q1-B1") & (profit.alpha == alpha)]
    return sub.set_index("year").net_profit / 10000


fig, ax = plt.subplots(figsize=(5.6, 3.2))
years = [2024 + i for i in range(7)]
ax.plot(years, series(0.5, "share10_k3"), marker="o", color=PRIMARY, label="半价销售（主方案）")
ax.plot(years, series(0.0, "share0_k3"), marker="s", color=ACCENT, label="滞销（主方案）")
ax.plot(years, base_series(0.5), "--", color=PRIMARY_LIGHT, label="半价（规则轮作基线）")
ax.plot(years, base_series(0.0), "--", color="#C9A56A", label="滞销（规则轮作基线）")
ax.set_ylabel("净收益（万元）")
ax.set_xlabel("年份")
ax.set_xticks(years)
style(ax)
ax.legend(ncol=2, frameon=False)
fig.tight_layout()
save(fig, "q1_yearly_profit")

# ============ Figure 3: 作物面积结构随年份演变 ============
half["year"] = half["year"].astype(int)
by_year_crop = half.groupby(["year", "crop_id"]).area_mu.sum().unstack(fill_value=0)
top_crops = half.groupby("crop_id").area_mu.sum().sort_values(ascending=False).head(6).index.tolist()
other = [c for c in by_year_crop.columns if c not in top_crops]
by_year_crop["其他"] = by_year_crop[other].sum(axis=1)
stack = by_year_crop[top_crops + ["其他"]]

palette = [PRIMARY, PRIMARY_LIGHT, ACCENT, POSITIVE, PURPLE, NEGATIVE, BASELINE]
fig, ax = plt.subplots(figsize=(5.6, 3.2))
ax.stackplot(
    stack.index,
    *[stack[c].values for c in stack.columns],
    labels=[name.get(int(c), str(c)) for c in top_crops] + ["其他"],
    colors=palette,
    alpha=0.9,
)
ax.set_ylabel("种植面积（亩）")
ax.set_xlabel("年份")
ax.set_xticks(stack.index)
ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14))
ax.margins(x=0)
style(ax)
fig.tight_layout()
save(fig, "q1_crop_structure_evolution")

print("done:", [f for f in sorted(p.name for p in FIG.glob("q1_crop_*") + FIG.glob("q1_yearly_*"))])
