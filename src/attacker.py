"""特征操纵攻击模型。

模拟理性借款人在申贷前对可操纵特征进行"资质包装"，核心假设：
特征被改变后评分随之变化，但借款人的真实违约标签不变——
由此产生"分数虚高、风险未降"的评分失真。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


# 单个操纵算子：返回操纵后的特征矩阵与归一化操纵成本
def manipulate_utilization(X: pd.DataFrame, strength: float) -> tuple[pd.DataFrame, float]:
    """账单日前突击还款，降低信用利用率。成本与被偿还的利用率成正比。"""
    X_a = X.copy()
    delta = X_a["utilization"] * strength
    X_a["utilization"] = X_a["utilization"] - delta
    cost = float(delta.mean())
    return X_a, cost


def manipulate_debt_ratio(X: pd.DataFrame, strength: float) -> tuple[pd.DataFrame, float]:
    """债务重组/偿还，降低负债比率。"""
    X_a = X.copy()
    delta = X_a["debt_ratio"].clip(upper=5) * strength
    X_a["debt_ratio"] = X_a["debt_ratio"] - delta
    cost = float(delta.mean())
    return X_a, cost


def manipulate_delinquency(X: pd.DataFrame, strength: float) -> tuple[pd.DataFrame, float]:
    """逾期记录申诉/随时间洗白，计数按强度向下削减。"""
    X_a = X.copy()
    total = 0.0
    for col in C.GMSC_DELINQUENCY_COLS:
        removed = np.ceil(X_a[col] * strength)
        X_a[col] = (X_a[col] - removed).clip(lower=0)
        total += float(removed.mean())
    return X_a, total


def manipulate_income(X: pd.DataFrame, strength: float) -> tuple[pd.DataFrame, float]:
    """收入申报美化（存在被核验风险，仅作对照）。"""
    X_a = X.copy()
    X_a["monthly_income"] = X_a["monthly_income"] * (1 + strength)
    return X_a, float(strength)


# 算子注册表：名称 -> (函数, 可操纵性等级)
ATTACK_OPS = {
    "utilization": (manipulate_utilization, "high"),
    "debt_ratio": (manipulate_debt_ratio, "high"),
    "delinquency": (manipulate_delinquency, "medium"),
    "income": (manipulate_income, "medium"),
}


def combined_attack(X: pd.DataFrame, strengths: dict[str, float]) -> tuple[pd.DataFrame, float]:
    """按给定强度依次施加全部操纵，模拟系统性"资质包装"。"""
    X_a = X.copy()
    total_cost = 0.0
    for name, strength in strengths.items():
        if strength <= 0:
            continue
        fn = ATTACK_OPS[name][0]
        X_a, cost = fn(X_a, strength)
        total_cost += cost
    return X_a, total_cost


class AttackEvaluator:
    """在固定评分卡与审批阈值下评估操纵攻击效果。"""

    def __init__(self, scorecard, approval_threshold: float) -> None:
        self.card = scorecard
        self.threshold = approval_threshold

    def baseline(self, X: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        scores = self.card.predict_score(X)
        approved = scores >= self.threshold
        return scores, approved

    def evaluate_op(
        self, X: pd.DataFrame, y: pd.Series, op_name: str, strength: float
    ) -> dict[str, float]:
        """评估单个操纵算子在给定强度下的攻击效果。"""
        base_scores, base_approved = self.baseline(X)
        fn = ATTACK_OPS[op_name][0]
        X_a, cost = fn(X, strength)
        a_scores = self.card.predict_score(X_a)
        a_approved = a_scores >= self.threshold

        # 攻击前被拒、攻击后通过的客户 = 攻击得手
        flipped = (~base_approved) & a_approved
        return {
            "op": op_name,
            "strength": strength,
            "cost": round(cost, 4),
            "score_gain": round(float((a_scores - base_scores).mean()), 2),
            "flip_rate": round(float(flipped.mean()), 4),
            "flipped_count": int(flipped.sum()),
            # 得手客户的真实违约率：标签未被操纵，这是机构的隐藏坏账
            "flipped_true_bad_rate": round(float(y[flipped].mean()) if flipped.any() else 0.0, 4),
            "new_approval_rate": round(float(a_approved.mean()), 4),
        }

    def sweep_strength(
        self, X: pd.DataFrame, y: pd.Series, op_name: str, points: int = 10
    ) -> pd.DataFrame:
        """扫描操纵强度 0.1~1.0，输出成本-效果曲线。"""
        rows = [
            self.evaluate_op(X, y, op_name, s)
            for s in np.linspace(0.1, 1.0, points)
        ]
        return pd.DataFrame(rows)

    def evaluate_combined(
        self, X: pd.DataFrame, y: pd.Series, strengths: dict[str, float]
    ) -> dict[str, float]:
        """评估组合攻击。"""
        base_scores, base_approved = self.baseline(X)
        X_a, cost = combined_attack(X, strengths)
        a_scores = self.card.predict_score(X_a)
        a_approved = a_scores >= self.threshold
        flipped = (~base_approved) & a_approved
        return {
            "cost": round(cost, 4),
            "score_gain": round(float((a_scores - base_scores).mean()), 2),
            "flip_rate": round(float(flipped.mean()), 4),
            "flipped_count": int(flipped.sum()),
            "flipped_true_bad_rate": round(float(y[flipped].mean()) if flipped.any() else 0.0, 4),
            "new_approval_rate": round(float(a_approved.mean()), 4),
        }
