"""
用户画像分析 — 多维度用户行为特征
"""

import pandas as pd
import numpy as np
from typing import Optional


def build_user_profile(df: pd.DataFrame) -> pd.DataFrame:
    """
    从预处理后数据构建用户画像宽表。
    
    维度：
    - 活跃度：总事件数、活跃天数
    - 生命周期：首次/最近活跃时间
    - 时段偏好：工作日活跃占比、活跃时段（上午/下午/夜间/凌晨）
    - 行为构成：view/addtocart/transaction 次数
    - 转化状态：是否购买、加购转化率、购买转化率
    """
    g = df.groupby("user_id")

    profile = pd.DataFrame(index=g.groups.keys())
    profile.index.name = "user_id"

    # --- 活跃度 ---
    profile["total_events"] = g.size().astype("int32")
    profile["active_days"] = g["date"].nunique().astype("int16")

    # --- 生命周期 ---
    ts_agg = g["timestamp"].agg(["min", "max"])
    profile["first_active"] = ts_agg["min"]
    profile["last_active"] = ts_agg["max"]
    profile["lifespan_days"] = (
        (profile["last_active"] - profile["first_active"]).dt.days.astype("int16")
    )

    # --- 时段偏好 ---
    profile["weekday_pct"] = (g["is_weekend"].apply(lambda x: (x == 0).mean()) * 100).round(1).astype("float32")

    # 时段分类: 凌晨(0-5) 上午(6-11) 下午(12-17) 晚上(18-23)
    hour_bins = [0, 6, 12, 18, 24]
    hour_labels = ["dawn", "morning", "afternoon", "night"]
    hour_group = pd.cut(df["hour"], bins=hour_bins, labels=hour_labels, right=False)
    hour_pivot = df.assign(hour_group=hour_group).pivot_table(
        index="user_id", columns="hour_group", aggfunc="size", fill_value=0
    )
    hour_pivot = hour_pivot.div(profile["total_events"], axis=0) * 100
    for col in hour_labels:
        profile[col + "_pct"] = hour_pivot.get(col, 0).astype("float32").round(1)

    # --- 行为构成 ---
    event_pivot = df.pivot_table(
        index="user_id", columns="event_type", aggfunc="size", fill_value=0
    )
    for event_type in ["view", "addtocart", "transaction"]:
        profile[event_type + "_count"] = (
            event_pivot.get(event_type, 0).astype("int32")
        )

    # --- 转化状态 ---
    profile["is_buyer"] = (profile["transaction_count"] > 0).astype("int8")
    profile["cart_to_buy_rate"] = np.where(
        profile["addtocart_count"] > 0,
        (profile["transaction_count"] / profile["addtocart_count"] * 100).round(2).astype("float32"),
        0.0,
    )

    return profile


def summary_stats(profile: pd.DataFrame) -> dict:
    """生成用户画像摘要统计"""
    total_users = len(profile)
    buyers = int(profile["is_buyer"].sum())
    return {
        "total_users": total_users,
        "buyers": buyers,
        "buyer_rate": round(buyers / total_users * 100, 2),
        "avg_events_per_user": round(profile["total_events"].mean(), 1),
        "median_events_per_user": int(profile["total_events"].median()),
        "avg_active_days": round(profile["active_days"].mean(), 1),
        "median_active_days": int(profile["active_days"].median()),
        "avg_lifespan_days": round(profile["lifespan_days"].mean(), 1),
        "median_lifespan_days": int(profile["lifespan_days"].median()),
        "event_distribution": {
            "1_event": int((profile["total_events"] == 1).sum()),
            "2_5_events": int(profile["total_events"].between(2, 5).sum()),
            "6_20_events": int(profile["total_events"].between(6, 20).sum()),
            "21_plus_events": int((profile["total_events"] > 20).sum()),
        },
    }
