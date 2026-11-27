"""评分卡模型：逻辑回归 + 分数映射 + 风险指标。

分数映射（好/坏比越大分数越高）：
    Factor = PDO / ln(2)
    Offset = BaseScore - Factor × ln(BaseOdds)
    Score  = Offset - Factor × (intercept + Σ coef_i × WOE_i)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve

from . import config as C


class Scorecard:
    """基于 WOE 特征的逻辑回归评分卡。"""

    def __init__(self, woe_transformer) -> None:
        self.woe = woe_transformer
        self.factor = C.PDO / np.log(2)
        self.offset = C.BASE_SCORE - self.factor * np.log(C.BASE_GOOD_BAD_ODDS)
        self.model = LogisticRegression(max_iter=1000, C=1.0)
        self.coef_: dict[str, float] = {}
        self.intercept_: float = 0.0

    def fit(self, X_raw: pd.DataFrame, y: pd.Series) -> "Scorecard":
        X_woe = self.woe.transform(X_raw)
        self.model.fit(X_woe, y)
        self.intercept_ = float(self.model.intercept_[0])
        self.coef_ = dict(zip(X_woe.columns, self.model.coef_[0]))
        return self

    def predict_proba_bad(self, X_raw: pd.DataFrame) -> np.ndarray:
        X_woe = self.woe.transform(X_raw)
        return self.model.predict_proba(X_woe)[:, 1]

    def predict_score(self, X_raw: pd.DataFrame) -> pd.Series:
        X_woe = self.woe.transform(X_raw)
        log_odds_bad = X_woe.apply(
            lambda r: self.intercept_ + sum(self.coef_[c] * r[c] for c in self.coef_),
            axis=1,
        )
        scores = self.offset - self.factor * log_odds_bad
        return pd.Series(scores.values, index=X_raw.index, name="score")

    def scorecard_table(self) -> pd.DataFrame:
        """输出每个特征分箱对应的分数扣减表（评分卡落地形式）。"""
        rows = []
        for feat, coef in self.coef_.items():
            edges = self.woe.bins[feat]
            for interval, woe_val in self.woe.woe_map[feat].items():
                points = -self.factor * coef * float(woe_val)
                rows.append(
                    {
                        "feature": feat,
                        "bin": str(interval),
                        "woe": round(float(woe_val), 4),
                        "points": round(points, 2),
                    }
                )
        return pd.DataFrame(rows)

    def base_points(self) -> float:
        return round(self.offset - self.factor * self.intercept_, 2)

    def evaluate(self, X_raw: pd.DataFrame, y: pd.Series) -> dict[str, float]:
        p_bad = self.predict_proba_bad(X_raw)
        scores = self.predict_score(X_raw)
        auc = roc_auc_score(y, p_bad)
        ks = _ks(y, p_bad)
        return {
            "auc": round(float(auc), 4),
            "gini": round(2 * float(auc) - 1, 4),
            "ks": round(ks, 4),
            "score_mean": round(float(scores.mean()), 2),
            "score_std": round(float(scores.std()), 2),
            "bad_rate": round(float(y.mean()), 4),
        }


def _ks(y_true: pd.Series, p_bad: np.ndarray) -> float:
    fpr, tpr, _ = roc_curve(y_true, p_bad)
    return float(np.max(tpr - fpr))


def psi(expected: pd.Series, actual: pd.Series, bins: int = 10) -> float:
    """群体稳定性指标 PSI，衡量两个评分分布的偏移程度。

    PSI < 0.1 稳定；0.1~0.25 轻微偏移；> 0.25 显著偏移。
    """
    qs = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    qs[0], qs[-1] = -np.inf, np.inf
    e_pct = pd.cut(expected, qs).value_counts(sort=False, normalize=True)
    a_pct = pd.cut(actual, qs).value_counts(sort=False, normalize=True)
    e_pct = e_pct.replace(0, 1e-4)
    a_pct = a_pct.replace(0, 1e-4)
    return float(((a_pct - e_pct) * np.log(a_pct / e_pct)).sum())


def approval_report(
    scores: pd.Series, y: pd.Series, threshold: float
) -> dict[str, float]:
    """给定审批分数线，输出通过率与坏账率。"""
    approved = scores >= threshold
    return {
        "approval_rate": round(float(approved.mean()), 4),
        "approved_bad_rate": round(float(y[approved].mean()) if approved.any() else 0.0, 4),
        "rejected_bad_capture": round(
            float(y[~approved].sum() / max(y.sum(), 1)), 4
        ),
    }
