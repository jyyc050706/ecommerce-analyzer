"""
留存分析 — 用户次日/3日/7日/14日/30日留存率
"""

import pandas as pd
import numpy as np
from typing import Optional, List


def _retention_cohort(df: pd.DataFrame, days_list: List[int]) -> pd.DataFrame:
    """
    基于队列的留存计算。
    每个用户以首次活跃日期为 D0，检查 D0+N 天是否仍有事件。
    """
    first_day = df.groupby("user_id")["date"].min().reset_index()
    first_day.columns = ["user_id", "d0"]
    
    all_dates = df[["user_id", "date"]].drop_duplicates()

    merged = all_dates.merge(first_day, on="user_id")
    merged["day_n"] = merged.apply(lambda r: (r["date"] - r["d0"]).days, axis=1)

    total_users = first_day["user_id"].nunique()
    result = {"total_users": total_users}

    for n in days_list:
        retained = merged[merged["day_n"] == n]["user_id"].nunique()
        result[f"day_{n}"] = retained
        result[f"day_{n}_rate"] = round(retained / total_users * 100, 2)

    return result


def retention_report(df: pd.DataFrame) -> dict:
    """生成留存报告（包含次日/3日/7日/14日/30日）"""
    return _retention_cohort(df, [1, 3, 7, 14, 30])


def retention_by_segment(df: pd.DataFrame, segment_col: str = "weekday") -> dict:
    """按分段（如工作日/周末首次活跃）计算留存差异"""
    # 获取每个用户的首次活跃日及其时段特征
    first_day_df = df.groupby("user_id").agg(
        d0=("date", "min"),
        first_hour=("hour", "first"),
        first_weekday=("weekday", "first")
    ).reset_index()

    if segment_col == "weekday":
        first_day_df["segment"] = first_day_df["first_weekday"].apply(
            lambda w: "工作日首访" if w < 5 else "周末首访"
        )
    elif segment_col in first_day_df.columns:
        first_day_df["segment"] = first_day_df[segment_col]
    else:
        return {}

    segments = {}
    for seg_name, group in first_day_df.groupby("segment"):
        seg_user_ids = set(group["user_id"])
        seg_df = df[df["user_id"].isin(seg_user_ids)]
        segments[seg_name] = _retention_cohort(seg_df, [1, 3, 7])

    return segments
