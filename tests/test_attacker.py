"""攻击模块测试。"""

from __future__ import annotations

import numpy as np

from src.attacker import (
    ATTACK_OPS,
    AttackEvaluator,
    combined_attack,
    manipulate_utilization,
)
from src.scorecard import Scorecard
from src.woe import WOETransformer


def test_utilization_never_negative(synthetic_data):
    X, y = synthetic_data
    for strength in (0.0, 0.5, 1.0):
        X_a, cost = manipulate_utilization(X, strength)
        assert (X_a["utilization"] >= 0).all()
        assert cost >= 0
        assert (X_a["utilization"] <= X["utilization"]).all()


def test_combined_attack_reduces_manipulable_features(synthetic_data):
    X, y = synthetic_data
    strengths = {"utilization": 0.9, "debt_ratio": 0.8, "delinquency": 0.5}
    X_a, _ = combined_attack(X, strengths)
    assert (X_a["utilization"] <= X["utilization"]).all()
    assert (X_a["debt_ratio"] <= X["debt_ratio"]).all()


def test_attack_never_changes_labels(synthetic_data):
    X, y = synthetic_data
    X_a, _ = combined_attack(
        X, {"utilization": 1.0, "debt_ratio": 1.0, "delinquency": 1.0}
    )
    # 攻击只改变特征，真实标签保持不变（评分失真的根源）
    assert len(X_a) == len(y)


def test_evaluator_flip_rate_nonnegative(synthetic_data):
    X, y = synthetic_data
    woe = WOETransformer().fit(X, y)
    card = Scorecard(woe).fit(X, y)
    thr = float(card.predict_score(X).median())
    ev = AttackEvaluator(card, thr)
    for op in ATTACK_OPS:
        r = ev.evaluate_op(X, y, op, 0.8)
        assert 0 <= r["flip_rate"] <= 1
        assert r["score_gain"] >= 0
        assert 0 <= r["flipped_true_bad_rate"] <= 1
