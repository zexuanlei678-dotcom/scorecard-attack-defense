"""可视化模块：统一配色与绘图风格，输出汇报用图。"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# 统一配色：深蓝=正常/基线，橙红=攻击/风险，墨绿=防御
PALETTE = {"base": "#2f5d8a", "attack": "#d96c3b", "defense": "#3f7d5f", "grey": "#9aa3ad"}
# 多序列用色（4条攻击曲线彼此区分）
SERIES_COLORS = ["#2f5d8a", "#d96c3b", "#3f7d5f", "#8a5a9e"]
sns.set_theme(style="whitegrid", font="DejaVu Sans")


def plot_score_distribution(scores: pd.Series, y: pd.Series, path: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.histplot(scores[y == 0], bins=40, color=PALETTE["base"], label="Good", stat="density", alpha=0.6, ax=ax)
    sns.histplot(scores[y == 1], bins=40, color=PALETTE["attack"], label="Bad", stat="density", alpha=0.6, ax=ax)
    ax.set_xlabel("Credit score"); ax.set_ylabel("Density"); ax.legend()
    ax.set_title("Score distribution by true label")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_iv_table(iv_tbl: pd.DataFrame, path: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    iv_tbl = iv_tbl.copy()
    iv_tbl["color"] = [PALETTE["attack"] if m == "high" else PALETTE["base"] for m in iv_tbl["manipulability"]]
    sns.barplot(data=iv_tbl, x="iv", y="feature", hue="feature", legend=False,
                palette=iv_tbl["color"].tolist(), ax=ax)
    ax.set_title("Information value by feature (orange=highly manipulable)")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_attack_curves(curves: dict[str, pd.DataFrame], path: str) -> None:
    """各算子的操纵强度-翻转率曲线。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, (name, df) in enumerate(curves.items()):
        ax.plot(df["strength"], df["flip_rate"], marker="o", label=name,
                color=SERIES_COLORS[i % len(SERIES_COLORS)])
    ax.set_xlabel("Manipulation strength"); ax.set_ylabel("Flip rate")
    ax.set_title("Attack strength vs. approval flip rate")
    ax.legend(); fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_score_gain_cost(curves: dict[str, pd.DataFrame], path: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, (name, df) in enumerate(curves.items()):
        ax.plot(df["cost"], df["score_gain"], marker="s", label=name,
                color=SERIES_COLORS[i % len(SERIES_COLORS)])
    ax.set_xlabel("Manipulation cost (normalized)"); ax.set_ylabel("Mean score gain")
    ax.set_title("Cost vs. score gain")
    ax.legend(); fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_bad_rate_comparison(entries: dict[str, float], path: str) -> None:
    """不同策略下的客户真实坏账率对比。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    names = list(entries.keys())
    vals = list(entries.values())
    colors = [PALETTE["base"] if "baseline" in n else PALETTE["defense"] if "defense" in n or "robust" in n else PALETTE["attack"] for n in names]
    ax.bar(names, vals, color=colors)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("True bad rate"); ax.set_title("True bad rate under different policies")
    plt.xticks(rotation=15, ha="right")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_defense_comparison(summary_df: pd.DataFrame, path: str) -> None:
    """防御前后翻转率与 AUC 分组柱状图。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(summary_df))
    w = 0.35
    ax.bar(x - w/2, summary_df["flip_rate"], w, label="Flip rate", color=PALETTE["attack"])
    ax.bar(x + w/2, summary_df["auc"], w, label="AUC", color=PALETTE["base"])
    ax.set_xticks(x); ax.set_xticklabels(summary_df["policy"], rotation=15, ha="right")
    ax.set_title("Defense comparison: flip rate vs. discriminative power")
    ax.legend(); fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)
