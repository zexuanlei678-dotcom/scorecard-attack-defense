"""评分卡模型测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.scorecard import Scorecard, approval_report, psi
from src.woe import WOETransformer


def _fit_card(synthetic_data):
    X, y = synthetic_data
    woe = WOETransformer().fit(X, y)
    return Scorecard(woe).fit(X, y), X, y


def test_score_orders_opposite_to_risk(synthetic_data):
    card, X, y = _fit_card(synthetic_data)
    scores = card.predict_score(X)
    p_bad = card.predict_proba_bad(X)
    # 分数与违约概率强反向（WOE离散化下不要求完美线性）
    assert np.corrcoef(scores, p_bad)[0, 1] < -0.95


def test_metrics_in_valid_range(synthetic_data):
    card, X, y = _fit_card(synthetic_data)
    m = card.evaluate(X, y)
    assert 0.5 < m["auc"] <= 1
    assert 0 <= m["ks"] <= 1
    assert abs(m["gini"] - (2 * m["auc"] - 1)) < 1e-6


def test_scorecard_table_points_sum_shape(synthetic_data):
    card, X, y = _fit_card(synthetic_data)
    tbl = card.scorecard_table()
    assert {"feature", "bin", "woe", "points"} <= set(tbl.columns)
    assert len(tbl) >= len(card.coef_)


def test_psi_identical_distribution_near_zero(synthetic_data):
    card, X, y = _fit_card(synthetic_data)
    s = card.predict_score(X)
    assert psi(s, s) < 1e-6


def test_approval_report_rates(synthetic_data):
    card, X, y = _fit_card(synthetic_data)
    scores = card.predict_score(X)
    thr = float(scores.median())
    rep = approval_report(scores, y, thr)
    assert 0 <= rep["approval_rate"] <= 1
    assert 0 <= rep["approved_bad_rate"] <= 1
    assert 0 <= rep["rejected_bad_capture"] <= 1
