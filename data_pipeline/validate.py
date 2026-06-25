"""
数据质量校验模块 — 生成结构化校验报告
"""

import pandas as pd
from datetime import datetime
from typing import Optional


def validate(df: pd.DataFrame) -> dict:
    """对清洗后 DataFrame 执行质量校验，返回报告字典。"""
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall": {},
        "fields": {},
        "consistency": {},
        "warnings": [],
    }

    total = len(df)

    # --- 整体 ---
    report["overall"] = {
        "total_rows": total,
        "total_columns": len(df.columns),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
    }

    # --- 字段级 ---
    for col in df.columns:
        nulls = int(df[col].isnull().sum())
        unique = int(df[col].nunique())
        report["fields"][col] = {
            "dtype": str(df[col].dtype),
            "nulls": nulls,
            "null_pct": round(nulls / total * 100, 4) if total else 0,
            "unique_values": unique,
            "unique_pct": round(unique / total * 100, 2) if total else 0,
        }

    # --- event_type 分布 ---
    if "event_type" in df.columns:
        report["fields"]["event_type"]["distribution"] = (
            df["event_type"].value_counts().to_dict()
        )

    # --- 时间范围 ---
    if "timestamp" in df.columns:
        report["fields"]["timestamp"]["min"] = str(df["timestamp"].min())
        report["fields"]["timestamp"]["max"] = str(df["timestamp"].max())
        report["fields"]["timestamp"]["days_span"] = (
            (df["timestamp"].max() - df["timestamp"].min()).days
        )

    # --- 一致性校验 ---
    # 1. 时间单调性
    report["consistency"]["timestamp_sorted"] = bool(
        df["timestamp"].is_monotonic_increasing
    )

    # 2. 无重复行
    report["consistency"]["no_duplicates"] = bool(df.duplicated().sum() == 0)

    # 3. 转化漏斗逻辑：transaction 的用户必然有 view 或 addtocart
    if "event_type" in df.columns:
        tx_users = set(df[df["event_type"] == "transaction"]["user_id"])
        view_users = set(df[df["event_type"] == "view"]["user_id"])
        orphan_tx = len(tx_users - view_users)
        report["consistency"]["orphan_transactions"] = orphan_tx
        if orphan_tx > 0:
            report["warnings"].append(
                f"{orphan_tx} users have transactions but no view events"
            )

    # 4. 统计概要
    report["consistency"]["user_count"] = int(df["user_id"].nunique())
    report["consistency"]["item_count"] = int(df["item_id"].nunique())
    report["consistency"]["event_types"] = (
        list(df["event_type"].cat.categories)
        if hasattr(df["event_type"], "cat")
        else list(df["event_type"].unique())
    )

    report["passed"] = (
        len(report["warnings"]) == 0
        and report["consistency"]["no_duplicates"]
        and all(v["nulls"] == 0 for v in report["fields"].values())
    )

    return report


def print_report(report: dict) -> str:
    """将报告字典格式化为可读文本"""
    lines = []
    lines.append("=" * 50)
    lines.append(f"  数据质量校验报告  {report['timestamp']}")
    lines.append("=" * 50)

    ov = report["overall"]
    lines.append(f"\n总行数: {ov['total_rows']:,}  列数: {ov['total_columns']}  内存: {ov['memory_mb']} MB")

    lines.append("\n--- 字段质量 ---")
    for col, info in report["fields"].items():
        lines.append(f"  {col}: dtype={info['dtype']}, nulls={info['nulls']}, unique={info['unique_values']}")
        if "distribution" in info:
            for event, cnt in info["distribution"].items():
                lines.append(f"    {event}: {cnt:,} ({cnt/ov['total_rows']*100:.2f}%)")
        if "days_span" in info:
            lines.append(f"    时间跨度: {info['days_span']} 天")
            lines.append(f"    时间范围: {info['min']} ~ {info['max']}")

    lines.append("\n--- 一致性检查 ---")
    for key, val in report["consistency"].items():
        lines.append(f"  {key}: {val}")

    if report["warnings"]:
        lines.append("\n--- 警告 ---")
        for w in report["warnings"]:
            lines.append(f"  ⚠ {w}")

    lines.append(f"\n{'✓ 校验通过' if report['passed'] else '✗ 存在问题'}")
    return "\n".join(lines)
