"""信用评分卡特征操纵攻防研究。

模块：
- data_pipeline: 数据加载与清洗
- woe: 分箱、WOE、IV
- scorecard: 逻辑回归评分卡与风险指标
- attacker: 特征操纵攻击仿真
- defender: 稳健评分卡、突变检测、对抗训练
- visualization: 汇报用图
"""

__all__ = [
    "config",
    "data_pipeline",
    "woe",
    "scorecard",
    "attacker",
    "defender",
    "visualization",
]
