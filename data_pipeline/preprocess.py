"""
特征工程模块 — 在清洗后数据上构建时间特征和事件编码
"""

import pandas as pd
import numpy as np
from typing import Optional


# 事件权重映射（用于漏斗排序和分析权重）
EVENT_WEIGHTS = {
    "view": 1,
    "addtocart": 2,
    "transaction": 3,
}


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    在清洗后 DataFrame 上增加衍生特征。
    返回新 DataFrame（原数据不修改）。
    """
    df_aug = df.copy()

    # --- 时间衍生特征 ---
    df_aug["hour"] = df_aug["timestamp"].dt.hour.astype("int8")
    df_aug["day"] = df_aug["timestamp"].dt.day.astype("int8")
    df_aug["weekday"] = df_aug["timestamp"].dt.weekday.astype("int8")  # 0=周一
    df_aug["month"] = df_aug["timestamp"].dt.month.astype("int8")
    df_aug["is_weekend"] = (df_aug["weekday"] >= 5).astype("int8")
    df_aug["date"] = df_aug["timestamp"].dt.date

    # --- 事件权重 ---
    df_aug["event_weight"] = df_aug["event_type"].map(EVENT_WEIGHTS).astype("int8")

    # --- 是否购买 (用于快速筛选) ---
    df_aug["is_purchase"] = (df_aug["event_type"] == "transaction").astype("int8")

    return df_aug


def preprocess_from_csv(input_path: str, output_path: Optional[str] = None) -> pd.DataFrame:
    """
    从 CSV 读取、预处理、可选写入。用于流水线。
    默认写入 data/preprocessed_events.csv
    """
    df = pd.read_csv(input_path, parse_dates=["timestamp"])
    df_aug = preprocess(df)
    if output_path:
        df_aug.to_csv(output_path, index=False)
    return df_aug
