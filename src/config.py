"""全局配置：数据集字段、特征可操纵性分类、评分卡刻度参数。

本项目不包含任何个人身份信息，所有实验数据均为公开匿名数据集。
"""

from __future__ import annotations

# ---------- Give Me Some Credit (GMSC) ----------
GMSC_TARGET = "SeriousDlqin2yrs"
GMSC_ID_COL = "Sr_No"

# 原始字段名 -> 规范化字段名
GMSC_RENAME = {
    "monthly_utilization": "utilization",
    "NumberOfTime30-59DaysPastDueNotWorse": "past_due_30_59",
    "DebtRatio": "debt_ratio",
    "MonthlyIncome": "monthly_income",
    "NumberOfOpenCreditLinesAndLoans": "open_credit_lines",
    "NumberOfTimes90DaysLate": "past_due_90",
    "NumberRealEstateLoansOrLines": "real_estate_lines",
    "NumberOfTime60-89DaysPastDueNotWorse": "past_due_60_89",
    "NumberOfDependents": "dependents",
}

# 特征可操纵性分级（基于信贷业务常识）：
# high   -> 借款人可在申贷前短期改变（突击还款、降低使用率、负债重组）
# medium -> 可通过申诉、时间推移或收入申报改变，需要一定成本/周期
# low    -> 短期内基本不可改变（人口属性、历史存量）
GMSC_MANIPULABILITY = {
    "utilization": "high",
    "debt_ratio": "high",
    "past_due_30_59": "medium",
    "past_due_60_89": "medium",
    "past_due_90": "medium",
    "monthly_income": "medium",
    "open_credit_lines": "low",
    "real_estate_lines": "low",
    "dependents": "low",
    "age": "low",
}

# GMSC 数据中已知的编码异常：逾期计数出现 96/98（数据采集错误），需截断
GMSC_DELINQUENCY_COLS = ["past_due_30_59", "past_due_60_89", "past_due_90"]
GMSC_DELINQUENCY_CAP = 20

# ---------- 评分卡刻度 ----------
# 标准 FICO 风格刻度：基准分 600 对应好坏比 50:1，每 20 分好坏比翻倍
BASE_SCORE = 600.0
BASE_GOOD_BAD_ODDS = 50.0
PDO = 20.0  # points to double odds

# ---------- WOE / IV ----------
IV_MIN = 0.02   # 低于该值视为无预测力
IV_MAX = 0.50   # 高于该值警惕过拟合/泄漏
MIN_BIN_PCT = 0.05  # 每个分箱最小样本占比
MAX_BINS = 6

# ---------- 实验 ----------
RANDOM_STATE = 42
TEST_SIZE = 0.25
APPROVAL_QUANTILE = 0.50  # 按评分中位数作为审批阈值（基线通过率约50%）
