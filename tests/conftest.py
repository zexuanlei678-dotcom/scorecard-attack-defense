"""pytest 公共夹具：构造可复现的合成数据，测试不依赖外部数据文件。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def synthetic_data() -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(7)
    n = 2000
    utilization = rng.uniform(0, 1.5, n)
    debt_ratio = rng.uniform(0, 3, n)
    age = rng.integers(21, 80, n).astype(float)
    past_due_30_59 = rng.poisson(0.3, n).astype(float)
    past_due_60_89 = rng.poisson(0.1, n).astype(float)
    past_due_90 = rng.poisson(0.1, n).astype(float)
    monthly_income = rng.lognormal(8, 0.6, n)
    open_credit_lines = rng.integers(1, 15, n).astype(float)
    real_estate_lines = rng.integers(0, 5, n).astype(float)
    dependents = rng.integers(0, 5, n).astype(float)

    # 违约概率与利用率、逾期正相关，保证特征有预测力
    logit = (
        -3
        + 1.2 * utilization
        + 0.8 * past_due_90
        + 0.5 * past_due_30_59
        + 0.3 * debt_ratio
    )
    p_bad = 1 / (1 + np.exp(-logit))
    y = pd.Series((rng.uniform(0, 1, n) < p_bad).astype(int))
    X = pd.DataFrame(
        {
            "utilization": utilization,
            "debt_ratio": debt_ratio,
            "age": age,
            "past_due_30_59": past_due_30_59,
            "past_due_60_89": past_due_60_89,
            "past_due_90": past_due_90,
            "monthly_income": monthly_income,
            "open_credit_lines": open_credit_lines,
            "real_estate_lines": real_estate_lines,
            "dependents": dependents,
        }
    )
    return X, y
