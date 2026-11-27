"""主实验：基线评分卡 -> 特征操纵攻击 -> 防御评估。

运行：python experiments/run_experiments.py
所有图表写入 results/，指标写入 results/metrics.json。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import config as C
from src.attacker import AttackEvaluator
from src.data_pipeline import load_gmsc, split_data
from src.defender import (
    ChangeDetector,
    defense_vs_attack,
    train_adversarial_scorecard,
    train_robust_scorecard,
)
from src.scorecard import Scorecard, approval_report, psi
from src.visualization import (
    plot_attack_curves,
    plot_bad_rate_comparison,
    plot_defense_comparison,
    plot_iv_table,
    plot_score_distribution,
    plot_score_gain_cost,
)
from src.woe import WOETransformer

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


def main() -> None:
    metrics: dict = {}

    # ---------- 1. 数据 ----------
    X, y = load_gmsc(str(ROOT / "data/gmsc.csv"))
    X_tr, X_te, y_tr, y_te = split_data(X, y)
    metrics["data"] = {
        "n_total": len(X), "n_train": len(X_tr), "n_test": len(X_te),
        "bad_rate": round(float(y.mean()), 4),
    }

    # ---------- 2. WOE / IV ----------
    woe = WOETransformer().fit(X_tr, y_tr)
    iv_tbl = woe.iv_table()
    iv_tbl.to_csv(RESULTS / "iv_table.csv", index=False)
    plot_iv_table(iv_tbl, str(RESULTS / "01_iv_table.png"))
    metrics["iv"] = iv_tbl.to_dict("records")

    # ---------- 3. 基线评分卡 ----------
    card = Scorecard(woe).fit(X_tr, y_tr)
    metrics["baseline_train"] = card.evaluate(X_tr, y_tr)
    metrics["baseline_test"] = card.evaluate(X_te, y_te)
    metrics["psi_train_vs_test"] = round(
        psi(card.predict_score(X_tr), card.predict_score(X_te)), 4
    )
    card.scorecard_table().to_csv(RESULTS / "scorecard_points.csv", index=False)

    scores_te = card.predict_score(X_te)
    plot_score_distribution(scores_te, y_te, str(RESULTS / "02_score_distribution.png"))

    # 审批阈值：训练集评分中位数
    threshold = float(card.predict_score(X_tr).quantile(1 - C.APPROVAL_QUANTILE))
    metrics["approval_threshold"] = round(threshold, 2)
    metrics["baseline_approval"] = approval_report(scores_te, y_te, threshold)

    # ---------- 4. 攻击 ----------
    evaluator = AttackEvaluator(card, threshold)
    curves = {}
    for op in ("utilization", "debt_ratio", "delinquency", "income"):
        curve = evaluator.sweep_strength(X_te, y_te, op)
        curve.to_csv(RESULTS / f"attack_{op}.csv", index=False)
        curves[op] = curve
    plot_attack_curves(curves, str(RESULTS / "03_attack_flip_curves.png"))
    plot_score_gain_cost(curves, str(RESULTS / "04_cost_score_gain.png"))

    # 组合攻击（强操纵场景）
    combo_strengths = {"utilization": 0.9, "debt_ratio": 0.7, "delinquency": 0.6, "income": 0.3}
    combo = evaluator.evaluate_combined(X_te, y_te, combo_strengths)
    metrics["combined_attack"] = combo

    # 各算子在满强度下的单点结果
    metrics["single_op_full_strength"] = [
        evaluator.evaluate_op(X_te, y_te, op, 1.0) for op in curves
    ]

    # ---------- 5. 防御 ----------
    robust_card, dropped = train_robust_scorecard(X_tr, y_tr)
    metrics["robust_dropped_features"] = dropped
    metrics["robust_test"] = robust_card.evaluate(X_te, y_te)

    adv_card = train_adversarial_scorecard(X_tr, y_tr)
    metrics["adversarial_test"] = adv_card.evaluate(X_te, y_te)

    # 突变检测：先在干净测试集拟合，再检测组合攻击后的样本
    detector = ChangeDetector().fit(X_tr)
    from src.attacker import combined_attack
    X_te_adv, _ = combined_attack(X_te, combo_strengths)
    base_pass = scores_te >= threshold
    adv_pass = card.predict_score(X_te_adv) >= threshold
    flipped_idx = X_te.index[(~base_pass) & adv_pass]
    metrics["change_detection"] = detector.detection_report(X_te_adv, flipped_idx, X_te)

    # 各策略面对同一组合攻击的翻转率对比
    policy_rows = []
    for name, c in (("baseline", card), ("robust", robust_card), ("adversarial", adv_card)):
        r = defense_vs_attack(c, X_te, y_te, threshold, combo_strengths)
        r["policy"] = name
        policy_rows.append(r)
    policy_df = pd.DataFrame(policy_rows)
    policy_df.to_csv(RESULTS / "defense_comparison.csv", index=False)
    plot_defense_comparison(policy_df, str(RESULTS / "05_defense_comparison.png"))
    metrics["defense_comparison"] = policy_rows

    # 坏账率视角：基线通过客户 vs 攻击后新通过客户
    bad_entries = {
        "baseline_approved": float(y_te[base_pass].mean()),
        "attack_flipped": float(y_te[flipped_idx].mean()) if len(flipped_idx) else 0.0,
    }
    plot_bad_rate_comparison(bad_entries, str(RESULTS / "06_bad_rate_gap.png"))
    metrics["bad_rate_gap"] = {k: round(v, 4) for k, v in bad_entries.items()}

    with open(RESULTS / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print("experiments finished; artifacts in", RESULTS)


if __name__ == "__main__":
    main()
