"""数据加载与清洗管线。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from . import config as C


def load_gmsc(csv_path: str) -> tuple[pd.DataFrame, pd.Series]:
    """加载 Give Me Some Credit 数据集并完成清洗。

    返回 (特征矩阵 X, 标签 y)，标签 1 表示违约（坏客户）。
    """
    raw = pd.read_csv(csv_path)
    raw = raw.rename(columns=C.GMSC_RENAME)
    raw = raw.drop(columns=[C.GMSC_ID_COL], errors="ignore")

    y = raw[C.GMSC_TARGET].astype(int)
    X = raw.drop(columns=[C.GMSC_TARGET]).copy()

    # 1) 年龄异常值：age=0 视为缺失，后续统一填补
    X.loc[X["age"] <= 0, "age"] = np.nan

    # 2) 逾期计数编码错误（96/98 等异常大值）截断
    for col in C.GMSC_DELINQUENCY_COLS:
        X.loc[X[col] > C.GMSC_DELINQUENCY_CAP, col] = C.GMSC_DELINQUENCY_CAP

    # 3) 极端偏态字段做 winsorize，避免单个异常值主导分箱
    for col in ["utilization", "debt_ratio", "monthly_income"]:
        hi = X[col].quantile(0.999)
        X.loc[X[col] > hi, col] = hi

    # 4) 缺失值填补：数值型用中位数，计数型用 0
    for col in X.columns:
        if X[col].isna().any():
            fill = 0.0 if col in C.GMSC_DELINQUENCY_COLS + ["dependents"] else X[col].median()
            X[col] = X[col].fillna(fill)

    X = X.astype(float).reset_index(drop=True)
    y = y.reset_index(drop=True)
    return X, y


def split_data(
    X: pd.DataFrame, y: pd.Series, test_size: float = C.TEST_SIZE
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """分层划分训练集/测试集，保证违约比例一致。"""
    return train_test_split(
        X, y, test_size=test_size, random_state=C.RANDOM_STATE, stratify=y
    )


def summary(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """输出字段级数据摘要，便于报告引用。"""
    summ = X.describe().T[["mean", "std", "min", "50%", "max"]]
    summ["missing"] = X.isna().sum()
    summ["manipulability"] = [
        C.GMSC_MANIPULABILITY.get(c, "low") for c in X.columns
    ]
    summ["bad_rate"] = [
        y.groupby(pd.qcut(X[c], 10, duplicates="drop")).mean().mean() for c in X.columns
    ]
    return summ
