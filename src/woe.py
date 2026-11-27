"""分箱、WOE 编码与 IV 计算。

WOE（Weight of Evidence）衡量分箱内好坏客户分布相对总体的偏离：
    WOE_i = ln( Good_i / Good_total ) - ln( Bad_i / Bad_total )
IV（Information Value）衡量特征整体预测力：
    IV = Σ (Good_i/Good_total - Bad_i/Bad_total) × WOE_i
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


class WOETransformer:
    """对每个数值特征做等频分箱并拟合 WOE 映射。"""

    def __init__(
        self,
        max_bins: int = C.MAX_BINS,
        min_bin_pct: float = C.MIN_BIN_PCT,
        iv_min: float = C.IV_MIN,
    ) -> None:
        self.max_bins = max_bins
        self.min_bin_pct = min_bin_pct
        self.iv_min = iv_min
        self.bins: dict[str, np.ndarray] = {}
        self.woe_map: dict[str, pd.Series] = {}
        self.iv: dict[str, float] = {}
        self.selected_features: list[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "WOETransformer":
        for col in X.columns:
            edges = self._make_edges(X[col])
            self.bins[col] = edges
            binned = pd.cut(X[col], bins=edges, include_lowest=True)
            woe, iv = self._calc_woe_iv(binned, y)
            self.woe_map[col] = woe
            self.iv[col] = iv
        self.selected_features = [
            c for c in X.columns if self.iv[c] >= self.iv_min
        ]
        return self

    def transform(self, X: pd.DataFrame, use_selected: bool = True) -> pd.DataFrame:
        cols = self.selected_features if use_selected else list(X.columns)
        out = pd.DataFrame(index=X.index)
        for col in cols:
            binned = pd.cut(X[col], bins=self.bins[col], include_lowest=True)
            out[col] = binned.map(self.woe_map[col]).astype(float)
        return out

    def fit_transform(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        return self.fit(X, y).transform(X)

    def iv_table(self) -> pd.DataFrame:
        """按 IV 降序输出特征预测力表。"""
        tbl = pd.DataFrame(
            {"feature": list(self.iv.keys()), "iv": list(self.iv.values())}
        ).sort_values("iv", ascending=False, ignore_index=True)
        tbl["strength"] = tbl["iv"].map(_iv_strength)
        tbl["manipulability"] = [
            C.GMSC_MANIPULABILITY.get(c, "low") for c in tbl["feature"]
        ]
        return tbl

    def _make_edges(self, s: pd.Series) -> np.ndarray:
        # 分箱数受最小样本占比约束
        n_bins = min(self.max_bins, max(2, int(1 / self.min_bin_pct)))
        qs = np.linspace(0, 1, n_bins + 1)
        edges = np.unique(np.quantile(s, qs))
        if len(edges) < 3:  # 取值过少时退化为唯一值切分
            edges = np.unique(np.concatenate([[s.min() - 1e-6], np.sort(s.unique()), [s.max()]]))
        edges[0] = -np.inf
        edges[-1] = np.inf
        return edges

    @staticmethod
    def _calc_woe_iv(
        binned: pd.Series, y: pd.Series
    ) -> tuple[pd.Series, float]:
        stats = pd.DataFrame({"bin": binned, "bad": y, "good": 1 - y})
        grp = stats.groupby("bin", observed=False)[["good", "bad"]].sum()
        total_good, total_bad = grp["good"].sum(), grp["bad"].sum()
        # 0.5 平滑，避免空箱导致除零
        good_pct = (grp["good"] + 0.5) / (total_good + 0.5)
        bad_pct = (grp["bad"] + 0.5) / (total_bad + 0.5)
        woe = np.log(good_pct / bad_pct)
        iv = float(((good_pct - bad_pct) * woe).sum())
        return woe, iv


def _iv_strength(iv: float) -> str:
    if iv < 0.02:
        return "无预测力"
    if iv < 0.1:
        return "弱"
    if iv < 0.3:
        return "中等"
    if iv < 0.5:
        return "强"
    return "过强(需警惕)"
