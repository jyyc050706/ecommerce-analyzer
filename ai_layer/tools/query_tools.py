"""
查询工具集 — KPI / 下钻 / 漏斗 / 同环比
所有查询基于缓存 parquet 数据，直接操作 DataFrame
"""

import pandas as pd
import numpy as np
from data_pipeline.cache import load_cached, get_daily_metrics, get_funnel, get_user_profile, get_rfm, get_anomaly_report


SOURCE = "retailrocket"


def _df():
    return load_cached(SOURCE)


def get_kpi(metric: str, period: str = "overall") -> dict:
    """获取指定 KPI

    metric: view_uv / addtocart_uv / transaction_uv / cvr_view_to_cart / cvr_cart_to_tx / total_users / total_items / buyer_rate
    period: overall / last_7d / last_30d
    """
    daily = get_daily_metrics(SOURCE)
    if period == "last_7d":
        daily = daily.tail(7)
    elif period == "last_30d":
        daily = daily.tail(30)

    metric_map = {
        "view_uv": ("浏览UV", daily["view"].sum() if period != "overall" else int(daily["view"].sum())),
        "addtocart_uv": ("加购UV", int(daily["addtocart"].sum())),
        "transaction_uv": ("交易UV", int(daily["transaction"].sum())),
        "cvr_view_to_cart": ("浏览→加购(%)", round(float(daily["cvr_view_to_cart"].mean()), 2)),
        "cvr_cart_to_tx": ("加购→交易(%)", round(float(daily["cvr_cart_to_tx"].mean()), 2)),
    }

    if metric in metric_map:
        name, value = metric_map[metric]
        return {"metric": name, "value": value, "period": period}
    return {"error": f"未知指标: {metric}"}


def drill_down(metric: str, dimension: str) -> pd.DataFrame:
    """按维度下钻指标

    dimension: hour / weekday / event_type / is_weekend
    """
    df = _df()

    if metric == "event_count":
        if dimension == "hour":
            result = df.groupby("hour").size().reset_index(name="count")
        elif dimension == "weekday":
            result = df.groupby("weekday").size().reset_index(name="count")
        elif dimension == "event_type":
            result = df.groupby("event_type").size().reset_index(name="count")
        elif dimension == "is_weekend":
            result = df.groupby("is_weekend").size().reset_index(name="count")
        else:
            return pd.DataFrame({"error": [f"未知维度: {dimension}"]})
        return result

    return pd.DataFrame({"error": [f"未知指标: {metric}"]})


def compare_period(metric: str) -> dict:
    """环比对比：最近 7 天 vs 前 7 天"""
    daily = get_daily_metrics(SOURCE)
    if len(daily) < 14:
        return {"error": "数据不足14天，无法环比"}

    recent = daily.tail(7)
    prior = daily.iloc[-14:-7]

    if metric in ("view_uv", "addtocart_uv", "transaction_uv"):
        col_map = {"view_uv": "view", "addtocart_uv": "addtocart", "transaction_uv": "transaction"}
        col = col_map[metric]
        r_val = int(recent[col].sum())
        p_val = int(prior[col].sum())
    elif metric in ("cvr_view_to_cart", "cvr_cart_to_tx"):
        r_val = round(float(recent[metric].mean()), 2)
        p_val = round(float(prior[metric].mean()), 2)
    else:
        return {"error": f"不支持的环比指标: {metric}"}

    change = r_val - p_val
    change_pct = round(change / p_val * 100, 1) if p_val else 0

    return {
        "metric": metric,
        "recent_7d": r_val,
        "prior_7d": p_val,
        "change": change,
        "change_pct": change_pct,
    }


def get_funnel_data() -> dict:
    """获取漏斗各环节数据"""
    funnel = get_funnel(SOURCE)
    row = funnel.iloc[0]
    return {
        "view_uv": int(row["view_uv"]),
        "addtocart_uv": int(row["addtocart_uv"]),
        "transaction_uv": int(row["transaction_uv"]),
        "addtocart_rate": round(float(row["addtocart_rate"]), 2),
        "transaction_rate": round(float(row["transaction_rate"]), 2),
        "overall_cvr": round(float(row["overall_cvr"]), 2),
    }


def get_user_segments() -> dict:
    """获取用户分层统计"""
    rfm = get_rfm(SOURCE)
    from eda.rfm_analysis import rfm_summary
    summary = rfm_summary(rfm)
    segments = {}
    for seg, info in summary.items():
        if seg in ("total_users", "thresholds"):
            continue
        segments[seg] = {"count": info["count"], "pct": info["pct"]}
    return segments


def get_top_items(event_type: str = "transaction", top_n: int = 10) -> pd.DataFrame:
    """获取 Top N 商品"""
    df = _df()
    subset = df[df["event_type"] == event_type]
    result = subset.groupby("item_id").size().sort_values(ascending=False).head(top_n).reset_index(name="count")
    return result


def get_anomalies() -> dict:
    """获取异常检测结果：各指标异常天数 + 异常日详情"""
    report = get_anomaly_report(SOURCE)
    daily = report["daily"]
    summary = report["summary"]

    # 各指标异常汇总
    by_metric = {}
    for col, info in summary.items():
        if col.startswith("_"):
            continue
        by_metric[col] = info

    # 综合异常日详情
    multi = daily[daily["multi_anomaly"] == 1]
    anomaly_dates = []
    for _, row in multi.iterrows():
        date_str = str(row["date"])
        flagged = []
        for col in by_metric:
            if row.get(f"{col}_3sigma", 0) == 1:
                flagged.append({"metric": col, "value": float(row[col])})
        anomaly_dates.append({"date": date_str, "flagged_metrics": flagged})

    return {
        "summary": by_metric,
        "multi_anomaly_count": len(anomaly_dates),
        "anomaly_dates": anomaly_dates,
    }
