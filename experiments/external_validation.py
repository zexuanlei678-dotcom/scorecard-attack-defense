"""外部验证：在 UCI 台湾信用卡违约数据集（30000 样本）上复现攻防结论。

该数据集字段与 GMSC 完全不同，用于检验"特征操纵导致评分失真"
这一结论是否跨数据集稳健，而非单一数据上的偶然现象。
运行：python experiments/external_validation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.attacker import AttackEvaluator
from src.scorecard import Scorecard, approval_report
from src.visualization import plot_score_distribution
from src.woe import WOETransformer

RESULTS = ROOT / "results"
MANIPULABILITY = {
    "utilization": "high",
    "pay_status": "medium",
    "pay_amount_ratio": "high",
    "age": "low",
    "credit_limit": "low",
}


def build_features(csv_path: str) -> tuple[pd.DataFrame, pd.Series]:
    raw = pd.read_csv(csv_path)
    y = raw["target"].astype(int)
    limit = raw["x1"].clip(lower=1)
    X = pd.DataFrame(
        {
            "credit_limit": raw["x1"],
            "age": raw["x5"],
            # 账单金额占信用额度比例 = 信用利用率
            "utilization": (raw["x12"] / limit).clip(lower=0, upper=2),
            # 本月还款状态（x6），负值统一视为 0（正常还款）
            "pay_status": raw["x6"].clip(lower=0, upper=8),
            # 实际还款额占额度比例
            "pay_amount_ratio": (raw["x18"] / limit).clip(lower=0, upper=2),
        }
    )
    return X, y


def main() -> None:
    X, y = build_features(str(ROOT / "data/credit_card_clients.csv"))
    cut = int(len(X) * 0.75)
    X_tr, X_te = X.iloc[:cut], X.iloc[cut:].reset_index(drop=True)
    y_tr, y_te = y.iloc[:cut], y.iloc[cut:].reset_index(drop=True)

    woe = WOETransformer().fit(X_tr, y_tr)
    card = Scorecard(woe).fit(X_tr, y_tr)
    metrics = {
        "dataset": "UCI Default of Credit Card Clients",
        "n_test": len(X_te),
        "test_evaluation": card.evaluate(X_te, y_te),
    }
    scores = card.predict_score(X_te)
    plot_score_distribution(scores, y_te, str(RESULTS / "07_external_score_dist.png"))

    threshold = float(card.predict_score(X_tr).median())
    metrics["baseline_approval"] = approval_report(scores, y_te, threshold)

    # 针对该数据集定义操纵算子：利用率与还款额比例突击改善、还款状态洗白
    def attack(strength: float) -> pd.DataFrame:
        X_a = X_te.copy()
        X_a["utilization"] = X_a["utilization"] * (1 - strength)
        X_a["pay_amount_ratio"] = X_a["pay_amount_ratio"] * (1 - strength * 0.5)
        X_a["pay_status"] = (X_a["pay_status"] - np.ceil(X_a["pay_status"] * strength)).clip(lower=0)
        return X_a

    base_pass = scores >= threshold
    out_rows = []
    for s in np.linspace(0.2, 1.0, 5):
        X_a = attack(float(s))
        a_scores = card.predict_score(X_a)
        a_pass = a_scores >= threshold
        flipped = (~base_pass) & a_pass
        out_rows.append(
            {
                "strength": round(float(s), 2),
                "flip_rate": round(float(flipped.mean()), 4),
                "flipped_true_bad_rate": round(float(y_te[flipped].mean()) if flipped.any() else 0.0, 4),
                "score_gain": round(float((a_scores - scores).mean()), 2),
            }
        )
    metrics["attack_sweep"] = out_rows
    metrics["baseline_approved_bad_rate"] = round(float(y_te[base_pass].mean()), 4)

    with open(RESULTS / "external_validation.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
