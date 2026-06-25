"""
异常检测模块 — 统计规则 3σ + IQR
检测每日指标（事件量、UV、转化率）中的异常点
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict


def daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """计算每日核心指标"""
    daily = df.groupby("date").agg(
        total_events=("event_type", "count"),
        view=("event_type", lambda x: (x == "view").sum()),
        addtocart=("event_type", lambda x: (x == "addtocart").sum()),
        transaction=("event_type", lambda x: (x == "transaction").sum()),
        unique_users=("user_id", "nunique"),
        unique_items=("item_id", "nunique"),
    ).reset_index()

    daily["cvr_view_to_cart"] = np.where(
        daily["view"] > 0,
        (daily["addtocart"] / daily["view"] * 100).round(2),
        0.0,
    )
    daily["cvr_cart_to_tx"] = np.where(
        daily["addtocart"] > 0,
        (daily["transaction"] / daily["addtocart"] * 100).round(2),
        0.0,
    )
    daily["cvr_overall"] = np.where(
        daily["view"] > 0,
        (daily["transaction"] / daily["view"] * 100).round(4),
        0.0,
    )
    return daily


def detect_3sigma(series: pd.Series) -> pd.Series:
    """3σ 异常检测，返回布尔 Series（True=异常）"""
    mean = series.mean()
    std = series.std()
    if std == 0:
        return pd.Series(False, index=series.index)
    return (series < mean - 3 * std) | (series > mean + 3 * std)


def detect_iqr(series: pd.Series, multiplier: float = 1.5) -> pd.Series:
    """IQR 异常检测，返回布尔 Series"""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return (series < lower) | (series > upper)


def detect_prophet_residual(daily: pd.DataFrame) -> pd.DataFrame:
    """
    Prophet 残差异常检测 — 第三层独立检测

    步骤：Prophet 拟合历史日交易量 → 计算残差 → 3σ 标记异常日
    与现有 3σ+IQR 独立，不投票融合。

    Returns
    -------
    pd.DataFrame
        在原 daily 上追加 4 列：
        - transaction_prophet_pred: Prophet 拟合值
        - transaction_prophet_residual: 残差 (actual - pred)
        - transaction_prophet_zscore: 残差 Z-score
        - transaction_prophet_flag: 残差 3σ 异常标记
    """
    from eda.forecaster import Forecaster

    fc = Forecaster(
        daily, date_col="date", target_col="transaction",
        freq="D", changepoint_prior_scale=0.05,
    )
    fc.fit()

    # in-sample 预测
    model = fc.get_model()
    hist_pred = model.predict(daily[["date"]].rename(columns={"date": "ds"}))

    result = daily.copy()
    result["transaction_prophet_pred"] = hist_pred["yhat"].values
    result["transaction_prophet_residual"] = (
        result["transaction"] - result["transaction_prophet_pred"]
    )
    mean_resid = result["transaction_prophet_residual"].mean()
    std_resid = result["transaction_prophet_residual"].std()
    result["transaction_prophet_zscore"] = (
        (result["transaction_prophet_residual"] - mean_resid) / std_resid
    ).round(2)
    result["transaction_prophet_flag"] = (
        (result["transaction_prophet_residual"].abs() > 3 * std_resid)
    ).astype("int8")

    return result


def anomaly_report(df: pd.DataFrame) -> dict:
    """
    生成异常检测报告。
    
    返回 dict：
    {
      "daily": DataFrame (每日指标+异常标记列),
      "summary": { 各指标异常天数统计 },
      "anomalies": { 异常日详细信息 }
    }
    """
    daily = daily_metrics(df)

    # ==================== Prophet 残差层（第三层独立检测） ====================
    daily = detect_prophet_residual(daily)

    # 需要检测的指标列
    metric_cols = [
        "total_events", "view", "addtocart", "transaction",
        "unique_users", "unique_items",
        "cvr_view_to_cart", "cvr_cart_to_tx", "cvr_overall",
    ]

    summary = {}
    anomalies_detail = {}

    for col in metric_cols:
        # 3σ
        flag_3s = detect_3sigma(daily[col])
        daily[f"{col}_3sigma"] = flag_3s.astype("int8")

        # IQR
        flag_iqr = detect_iqr(daily[col])
        daily[f"{col}_iqr"] = flag_iqr.astype("int8")

        n_3s = int(flag_3s.sum())
        n_iqr = int(flag_iqr.sum())
        both = int((flag_3s & flag_iqr).sum())

        summary[col] = {"3sigma_days": n_3s, "iqr_days": n_iqr, "both_days": both}

        if both > 0:
            anomaly_dates = daily.loc[flag_3s & flag_iqr, ["date", col]]
            anomalies_detail[col] = anomaly_dates.to_dict("records")

    # 综合异常日：至少3个指标同时被3σ检测为异常
    flag_cols_3s = [f"{c}_3sigma" for c in metric_cols]
    daily["multi_anomaly"] = (daily[flag_cols_3s].sum(axis=1) >= 3).astype("int8")
    summary["_multi_anomaly_days"] = int(daily["multi_anomaly"].sum())

    # Prophet 残差层摘要
    summary["prophet_residual"] = {
        "anomaly_days": int(daily["transaction_prophet_flag"].sum()),
        "max_residual": float(daily["transaction_prophet_residual"].abs().max()),
        "mean_abs_residual": round(float(daily["transaction_prophet_residual"].abs().mean()), 2),
    }

    return {
        "daily": daily,
        "summary": summary,
        "anomalies": anomalies_detail,
    }
