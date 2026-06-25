"""
RFM 分层分析 — 无金额数据场景下以交易次数代理 Monetary
"""

import pandas as pd
import numpy as np
from typing import Optional


def build_rfm(df: pd.DataFrame, reference_date: Optional[str] = None) -> pd.DataFrame:
    """
    构建用户 RFM 宽表。

    R (Recency): 距参考日期的天数（越小越活跃）
    F (Frequency): 总事件次数
    M (Monetary proxy): 交易次数 + 加购次数*0.5（无金额时的行为价值代理）

    返回 DataFrame，user_id 为索引，含 R/F/M 原始值和分档。
    """
    if reference_date is None:
        ref = df["timestamp"].max()
    else:
        ref = pd.Timestamp(reference_date)

    agg = df.groupby("user_id").agg(
        last_active=("timestamp", "max"),
        total_events=("event_type", "count"),
        transaction_count=("is_purchase", "sum"),
        addtocart_count=("event_type", lambda x: (x == "addtocart").sum()),
    )

    rfm = pd.DataFrame(index=agg.index)
    rfm["R"] = (ref - agg["last_active"]).dt.days.astype("int16")
    rfm["F"] = agg["total_events"].astype("int32")
    rfm["M"] = agg["transaction_count"] + agg["addtocart_count"] * 0.5
    rfm["M"] = rfm["M"].round(1).astype("float32")

    # 五分档（值越小越差，1=最低分位）
    rfm["R_score"] = pd.qcut(rfm["R"], q=5, labels=[5, 4, 3, 2, 1]).astype("int8")
    rfm["F_score"] = pd.qcut(
        rfm["F"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]
    ).astype("int8")
    rfm["M_score"] = pd.qcut(
        rfm["M"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]
    ).astype("int8")

    # 综合分
    rfm["RFM_total"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]

    # 分层标签
    def label_segment(score):
        if score >= 13:
            return "高价值"
        elif score >= 10:
            return "潜力用户"
        elif score >= 7:
            return "需要激活"
        elif score >= 4:
            return "流失风险"
        else:
            return "已流失"

    rfm["segment"] = rfm["RFM_total"].apply(label_segment)

    return rfm


def rfm_summary(rfm: pd.DataFrame) -> dict:
    """RFM 分层汇总统计"""
    seg_counts = rfm["segment"].value_counts()
    total = len(rfm)
    result = {"total_users": total}
    for seg, cnt in seg_counts.items():
        result[seg] = {"count": int(cnt), "pct": round(cnt / total * 100, 2)}
    result["thresholds"] = {
        "R (days)": {"5": int(rfm[rfm["R_score"] == 5]["R"].max())},
        "F (events)": {"5": int(rfm[rfm["F_score"] == 5]["F"].min())},
        "M (score)": {"5": float(rfm[rfm["M_score"] == 5]["M"].min())},
    }
    return result
