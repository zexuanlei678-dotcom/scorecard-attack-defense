"""防御模块：稳健评分卡、突变检测、对抗训练。

三类防御对应不同的部署成本与性能代价，实验中统一用
"攻击翻转率下降 + AUC/KS 变化"评估其有效性与代价。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .attacker import ATTACK_OPS, combined_attack
from .scorecard import Scorecard
from .woe import WOETransformer


# ---------- 防御1：剔除高可操纵特征的稳健评分卡 ----------
def train_robust_scorecard(
    X: pd.DataFrame,
    y: pd.Series,
    drop_levels: tuple[str, ...] = ("high",),
) -> tuple[Scorecard, list[str]]:
    """剔除指定可操纵性等级的特征后重新训练评分卡。"""
    drop_cols = [
        c
        for c in X.columns
        if C.GMSC_MANIPULABILITY.get(c) in drop_levels
    ]
    keep = [c for c in X.columns if c not in drop_cols]
    woe = WOETransformer().fit(X[keep], y)
    card = Scorecard(woe).fit(X[keep], y)
    return card, drop_cols


# ---------- 防御2：特征突变检测 ----------
class ChangeDetector:
    """基于历史快照与本次申请差异的突变检测。

    真实业务中机构可同时看到客户的历史特征快照与本次申请值。
    当高可操纵特征在短期内出现大幅"改善"（如利用率骤降、
    逾期记录消失），或出现"零利用率+多逾期"的矛盾组合时，
    标记为可疑、转人工审核。
    """

    def __init__(
        self,
        relative_drop: float = 0.5,
        low_quantile: float = 0.02,
    ) -> None:
        self.relative_drop = relative_drop
        self.low_quantile = low_quantile
        self.low_util_threshold = 0.0

    def fit(self, X: pd.DataFrame) -> "ChangeDetector":
        self.low_util_threshold = float(X["utilization"].quantile(self.low_quantile))
        return self

    def flag(self, X_now: pd.DataFrame, X_prev: pd.DataFrame | None = None) -> pd.Series:
        suspicious = pd.Series(False, index=X_now.index)
        if X_prev is not None:
            # 相对降幅：(历史值-当前值)/历史值，历史值过小则跳过
            for col in ["utilization", "debt_ratio"]:
                base = X_prev[col].clip(lower=1e-6)
                rel_drop = (base - X_now[col]) / base
                suspicious |= rel_drop >= self.relative_drop
            # 逾期计数短期内消失
            prev_dlq = X_prev[C.GMSC_DELINQUENCY_COLS].sum(axis=1)
            now_dlq = X_now[C.GMSC_DELINQUENCY_COLS].sum(axis=1)
            suspicious |= (prev_dlq >= 1) & (now_dlq < prev_dlq)
        # 矛盾组合：近乎零利用率却存在历史逾期记录
        contradiction = (X_now["utilization"] <= self.low_util_threshold) & (
            X_now[C.GMSC_DELINQUENCY_COLS].sum(axis=1) >= 1
        )
        return suspicious | contradiction

    def detection_report(
        self,
        X_attacked: pd.DataFrame,
        flipped_idx: pd.Index,
        X_clean: pd.DataFrame,
    ) -> dict[str, float]:
        """返回攻击得手客户的检测率与干净样本上的误报率。

        攻击场景下 X_clean 即攻击前快照；干净样本无真实历史，
        矛盾组合规则仍可在其上估计误报。
        """
        flags = self.flag(X_attacked, X_clean)
        clean_flags = self.flag(X_clean)
        return {
            "detection_rate": round(float(flags[flipped_idx].mean()) if len(flipped_idx) else 0.0, 4),
            "false_positive_rate": round(float(clean_flags.mean()), 4),
            "flagged_total": int(flags.sum()),
        }


# ---------- 防御3：对抗训练 ----------
def train_adversarial_scorecard(
    X: pd.DataFrame,
    y: pd.Series,
    strengths: dict[str, float] | None = None,
) -> Scorecard:
    """将操纵样本与原始样本混合后重新训练，降低模型对操纵的敏感度。"""
    strengths = strengths or {"utilization": 0.8, "debt_ratio": 0.6, "delinquency": 0.5}
    X_adv, _ = combined_attack(X, strengths)
    X_mix = pd.concat([X, X_adv], ignore_index=True)
    y_mix = pd.concat([y, y], ignore_index=True)
    woe = WOETransformer().fit(X_mix, y_mix)
    return Scorecard(woe).fit(X_mix, y_mix)


# ---------- 防御效果统一评估 ----------
def defense_vs_attack(
    card: Scorecard,
    X: pd.DataFrame,
    y: pd.Series,
    approval_threshold: float,
    strengths: dict[str, float],
) -> dict[str, float]:
    """给定防御卡与攻击强度，计算攻击翻转率与得手客户真实坏账率。"""
    X_adv, _ = combined_attack(X, strengths)
    base_pass = card.predict_score(X) >= approval_threshold
    adv_pass = card.predict_score(X_adv) >= approval_threshold
    flipped = (~base_pass) & adv_pass
    return {
        "flip_rate": round(float(flipped.mean()), 4),
        "flipped_count": int(flipped.sum()),
        "flipped_true_bad_rate": round(float(y[flipped].mean()) if flipped.any() else 0.0, 4),
        "auc": card.evaluate(X, y)["auc"],
        "ks": card.evaluate(X, y)["ks"],
    }
