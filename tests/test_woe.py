"""WOE 分箱与 IV 计算测试。"""

from __future__ import annotations

import numpy as np

from src.woe import WOETransformer


def test_bins_cover_full_range(synthetic_data):
    X, y = synthetic_data
    woe = WOETransformer().fit(X, y)
    for col, edges in woe.bins.items():
        assert np.isneginf(edges[0]) and np.isposinf(edges[-1])
        assert len(edges) >= 3


def test_iv_nonnegative_and_finite(synthetic_data):
    X, y = synthetic_data
    woe = WOETransformer().fit(X, y)
    for col, iv in woe.iv.items():
        assert iv >= 0
        assert np.isfinite(iv)


def test_predictive_feature_selected(synthetic_data):
    X, y = synthetic_data
    woe = WOETransformer().fit(X, y)
    # utilization 是合成数据中最强的预测特征，必须被选中
    assert "utilization" in woe.selected_features
    assert woe.iv["utilization"] > woe.iv["age"]


def test_transform_has_no_missing(synthetic_data):
    X, y = synthetic_data
    woe = WOETransformer().fit(X, y)
    out = woe.transform(X)
    assert not out.isna().any().any()
    assert np.isfinite(out.values).all()


def test_iv_table_columns(synthetic_data):
    X, y = synthetic_data
    woe = WOETransformer().fit(X, y)
    tbl = woe.iv_table()
    assert {"feature", "iv", "strength", "manipulability"} <= set(tbl.columns)
    # 已按 IV 降序
    assert tbl["iv"].is_monotonic_decreasing
