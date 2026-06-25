"""
转化漏斗分析 — view → addtocart → transaction 各层转化率
"""

import pandas as pd
import numpy as np
from typing import Optional


FUNNEL_ORDER = ["view", "addtocart", "transaction"]


def build_funnel(df: pd.DataFrame, group_by: Optional[str] = None) -> pd.DataFrame:
    """
    构建转化漏斗。
    
    - 不分组：总体漏斗
    - group_by='weekday'：按周中/周末分组
    - group_by='date'：按日分组（趋势）
    
    返回漏斗 DataFrame，每行为一个分组，列为各层 UV 和转化率。
    """
    if group_by is None:
        groups = [("总体", df)]
    elif group_by == "weekday":
        df_c = df.copy()
        df_c["_group"] = df_c["weekday"].apply(lambda w: "工作日" if w < 5 else "周末")
        groups = [(name, grp) for name, grp in df_c.groupby("_group")]
    elif group_by == "date":
        groups = [(str(d), grp) for d, grp in df.groupby("date")]
    else:
        groups = [(str(k), grp) for k, grp in df.groupby(group_by)]

    rows = []
    for name, grp in groups:
        row = {"group": name}
        for i, stage in enumerate(FUNNEL_ORDER):
            uv = int(grp[grp["event_type"] == stage]["user_id"].nunique())
            row[f"{stage}_uv"] = uv
            if i == 0:
                row[f"{stage}_rate"] = 100.0
            else:
                prev_uv = row[f"{FUNNEL_ORDER[i-1]}_uv"]
                row[f"{stage}_rate"] = round(uv / prev_uv * 100, 2) if prev_uv > 0 else 0.0
        # 整体转化率 (view → transaction)
        if row["view_uv"] > 0:
            row["overall_cvr"] = round(row["transaction_uv"] / row["view_uv"] * 100, 4)
        else:
            row["overall_cvr"] = 0.0
        rows.append(row)

    return pd.DataFrame(rows)


def funnel_summary_text(funnel_df: pd.DataFrame) -> str:
    """将漏斗 DataFrame 格式化为可读摘要"""
    row = funnel_df.iloc[0] if len(funnel_df) == 1 else funnel_df
    lines = []
    for i, stage in enumerate(FUNNEL_ORDER):
        uv = row.get(f"{stage}_uv", "N/A") if len(funnel_df) == 1 else funnel_df[f"{stage}_uv"].sum()
        rate = row.get(f"{stage}_rate", "N/A") if len(funnel_df) == 1 else "—"
        lines.append(f"  {stage}: {uv:,} UV (转化率 {rate}%)")
    return "\n".join(lines)
