"""防御模块测试。"""

from __future__ import annotations

import numpy as np

from src.attacker import combined_attack
from src.defender import (
    ChangeDetector,
    train_adversarial_scorecard,
    train_robust_scorecard,
)


def test_robust_card_drops_high_manipulable(synthetic_data):
    X, y = synthetic_data
    card, dropped = train_robust_scorecard(X, y)
    assert "utilization" in dropped
    assert "debt_ratio" in dropped
    assert "age" not in dropped
    assert "utilization" not in card.woe.selected_features


def test_change_detector_flags_large_drop(synthetic_data):
    X, y = synthetic_data
    detector = ChangeDetector().fit(X)
    strengths = {"utilization": 0.95, "debt_ratio": 0.95, "delinquency": 0.9}
    X_adv, _ = combined_attack(X, strengths)
    flags = detector.flag(X_adv, X)
    # 强操纵必然触发部分标记
    assert flags.dtype == bool
    assert flags.sum() > 0


def test_change_detector_clean_low_false_positive(synthetic_data):
    X, y = synthetic_data
    detector = ChangeDetector().fit(X)
    # 无历史快照时仅矛盾组合规则生效，干净样本误报应较低
    flags = detector.flag(X)
    assert flags.mean() < 0.2


def test_adversarial_card_trains(synthetic_data):
    X, y = synthetic_data
    card = train_adversarial_scorecard(X, y)
    m = card.evaluate(X, y)
    assert 0.5 < m["auc"] <= 1
    scores = card.predict_score(X)
    assert np.isfinite(scores.values).all()
