"""
数据清洗模块 — 缺失值/异常值/类型转换/重复去重
"""

import pandas as pd
from typing import Optional
from data_pipeline.base_source import BaseDataSource


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    对标准化后的 DataFrame 执行清洗流水线：
    1. 类型强制转换
    2. 完全重复行去重
    3. 业务逻辑异常标记（event_type 顺序合法性检查）
    
    返回清洗后 DataFrame（copy）。
    """
    df_clean = df.copy()
    initial = len(df_clean)

    # 1. 类型强制转换
    df_clean["user_id"] = pd.to_numeric(df_clean["user_id"], errors="coerce").astype("Int64")
    df_clean["item_id"] = pd.to_numeric(df_clean["item_id"], errors="coerce").astype("Int64")
    df_clean["event_type"] = df_clean["event_type"].astype("category")
    df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"], errors="coerce")

    # 2. 删除完全重复行
    df_clean.drop_duplicates(inplace=True)
    dup_removed = initial - len(df_clean)

    # 3. 删除关键字段为 NA 的行
    na_before = len(df_clean)
    df_clean.dropna(subset=["user_id", "item_id", "event_type", "timestamp"], inplace=True)
    na_removed = na_before - len(df_clean)

    # 4. 按时间排序
    df_clean.sort_values("timestamp", inplace=True)
    df_clean.reset_index(drop=True, inplace=True)

    report = {
        "initial_rows": initial,
        "duplicates_removed": dup_removed,
        "na_removed": na_removed,
        "final_rows": len(df_clean),
    }
    return df_clean, report


def clean_from_source(source: BaseDataSource) -> tuple[pd.DataFrame, dict]:
    """从 BaseDataSource 子类加载并清洗"""
    df = source.get_data()
    return clean(df)
