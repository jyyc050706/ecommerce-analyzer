"""
数据缓存工具 — 加速看板加载

用法：
    df = load_cached("retailrocket")               # 预处理数据
    daily = get_daily_metrics("retailrocket")       # 每日指标
    funnel = get_funnel("retailrocket")             # 总体漏斗
    profile = get_user_profile("retailrocket")      # 用户画像
    rfm = get_rfm("retailrocket")                   # RFM 分层
    report = get_anomaly_report("retailrocket")     # 异常检测

首次运行：走完整计算管道，存入 data/cache/{source}.xxx
后续运行：直接读缓存，秒级加载
"""

import pickle
import pandas as pd
from pathlib import Path
from config import CACHE_DIR

CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
#  预处理数据缓存
# ============================================================

def load_cached(source_name: str) -> pd.DataFrame:
    """加载预处理数据（优先读 parquet 缓存）"""
    cache_path = CACHE_DIR / f"{source_name}.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    from data_pipeline.load_raw import RetailRocketSource
    from data_pipeline.clean import clean_from_source
    from data_pipeline.preprocess import preprocess
    from config import DATA_DIR

    source = RetailRocketSource(DATA_DIR)
    df_clean, _ = clean_from_source(source)
    df_aug = preprocess(df_clean)
    df_aug.to_parquet(cache_path, index=False)
    return df_aug


# ============================================================
#  EDA 结果缓存（parquet / pickle）
# ============================================================

def _eda_path(source_name: str, key: str, ext: str = "parquet") -> Path:
    return CACHE_DIR / f"{source_name}_{key}.{ext}"


def get_daily_metrics(source_name: str) -> pd.DataFrame:
    """每日核心指标（缓存）"""
    cache_path = _eda_path(source_name, "daily_metrics")
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    from eda.anomaly_detect import daily_metrics
    df = load_cached(source_name)
    result = daily_metrics(df)
    result.to_parquet(cache_path, index=False)
    return result


def get_funnel(source_name: str, group_by: str = "overall") -> pd.DataFrame:
    """
    转化漏斗（缓存）。
    group_by: "overall" | "weekday" | "date"
    """
    cache_path = _eda_path(source_name, f"funnel_{group_by}")
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    from eda.behavior_funnel import build_funnel
    df = load_cached(source_name)
    if group_by == "date":
        result = build_funnel(df, group_by="date").rename(columns={"group": "date"})
    else:
        result = build_funnel(df, group_by=None if group_by == "overall" else group_by)
    result.to_parquet(cache_path, index=False)
    return result


def get_user_profile(source_name: str) -> pd.DataFrame:
    """用户画像宽表（缓存）"""
    cache_path = _eda_path(source_name, "user_profile")
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    from eda.user_profile import build_user_profile
    df = load_cached(source_name)
    result = build_user_profile(df)
    result.to_parquet(cache_path, index=False)
    return result


def get_rfm(source_name: str) -> pd.DataFrame:
    """RFM 分层宽表（缓存）"""
    cache_path = _eda_path(source_name, "rfm")
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    from eda.rfm_analysis import build_rfm
    df = load_cached(source_name)
    result = build_rfm(df)
    result.to_parquet(cache_path, index=False)
    return result


def get_anomaly_report(source_name: str) -> dict:
    """异常检测报告（pickle 缓存，因返回值为 dict）"""
    cache_path = _eda_path(source_name, "anomaly_report", "pkl")
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            return pickle.load(f)

    from eda.anomaly_detect import anomaly_report
    df = load_cached(source_name)
    result = anomaly_report(df)
    with open(cache_path, "wb") as f:
        pickle.dump(result, f)
    return result


def get_forecast_result(source_name: str, periods: int = 30) -> dict:
    """时序预测结果（pickle 缓存）"""
    cache_path = _eda_path(source_name, f"forecast_{periods}d", "pkl")
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            return pickle.load(f)

    from eda.forecaster import Forecaster
    daily = get_daily_metrics(source_name)
    fc = Forecaster(daily, date_col="date", target_col="transaction")
    fc.fit()
    pred = fc.predict(periods=periods)
    metrics = fc.metrics()

    result = {
        "daily": daily,
        "forecast": pred,
        "metrics": metrics,
    }
    with open(cache_path, "wb") as f:
        pickle.dump(result, f)
    return result


def clear_cache(source_name: str = ""):
    """清除指定或全部缓存"""
    if source_name:
        for f in CACHE_DIR.glob(f"{source_name}*"):
            f.unlink()
    else:
        for f in CACHE_DIR.iterdir():
            f.unlink()
