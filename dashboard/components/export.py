"""
导出模块 — Markdown / PDF 导出
"""

import os
import pandas as pd
from datetime import datetime


def export_md(output_dir: str, report: dict) -> str:
    """生成完整 Markdown 分析报告。report 字典包含所有预计算数据。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# ecommerce-analyzer 分析报告",
        f"生成时间: {now}",
        "",
    ]

    # ===== 1. 数据规模 =====
    s = report["scale"]
    lines += [
        "## 1. 数据规模",
        "",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总事件数 | {s['total_events']:,} |",
        f"| 独立用户 | {s['total_users']:,} |",
        f"| 独立商品 | {s['total_items']:,} |",
        f"| 交易数 | {s['tx_count']:,} |",
        f"| 整体转化率(事件级) | {s['cvr']}% |",
        f"| 时间跨度 | {s['date_range']} |",
        "",
    ]

    # ===== 2. 事件类型分布 =====
    et = report["event_types"]
    lines += [
        "## 2. 事件类型分布",
        "",
        "| 类型 | 数量 | 占比 |",
        "|------|------|------|",
    ]
    for etype in ["view", "addtocart", "transaction"]:
        lines.append(f"| {etype} | {et[etype]:,} | {et[f'{etype}_pct']}% |")
    lines.append("")

    # ===== 3. KPI 多时段 =====
    lines += [
        "## 3. KPI 多时段对比",
        "",
        "| 指标 | 全周期 | 近30天 | 近7天 |",
        "|------|--------|--------|-------|",
    ]
    for row in report["kpi"]:
        lines.append(f"| {row['label']} | {row['overall']} | {row['last_30d']} | {row['last_7d']} |")
    lines.append("")

    # ===== 4. 每日指标（近7天） =====
    daily = report["daily"]
    lines += [
        "## 4. 每日指标概览（近7天）",
        "",
        daily.tail(7).rename(columns={
            "date": "日期", "view": "浏览UV", "addtocart": "加购UV",
            "transaction": "交易UV", "cvr_view_to_cart": "浏览→加购(%)",
            "cvr_cart_to_tx": "加购→交易(%)",
        }).to_markdown(index=False),
        "",
    ]

    # ===== 5. 用户分析 =====
    us = report["users"]
    lines += [
        "## 5. 用户分析",
        "",
        f"- 总用户: {us['total_users']:,}",
        f"- 买家数: {us['buyers']:,}",
        f"- 买家率: {us['buyer_rate']}%",
        f"- 人均事件: {us['avg_events_per_user']}",
        f"- 人均活跃天数: {us['avg_active_days']}",
        f"- 人均生命周期(天): {us['avg_lifespan_days']}",
        "",
        "### 活跃度分布",
        "",
        "| 事件数 | 用户数 | 占比 |",
        "|--------|--------|------|",
    ]
    for label, count in us["event_distribution"].items():
        pct = round(count / us['total_users'] * 100, 1)
        lines.append(f"| {label} | {count:,} | {pct}% |")
    lines.append("")

    # 时段偏好
    lines += [
        "### 时段偏好（用户均值）",
        "",
        f"- 凌晨(0-5时): {us['dawn_pct']:.1f}%",
        f"- 上午(6-11时): {us['morning_pct']:.1f}%",
        f"- 下午(12-17时): {us['afternoon_pct']:.1f}%",
        f"- 晚上(18-23时): {us['night_pct']:.1f}%",
        "",
    ]

    # RFM 分层
    lines += [
        "### RFM 用户分层",
        "",
        "| 分层 | 用户数 | 占比 |",
        "|------|--------|------|",
    ]
    for seg_name, seg_info in report["rfm"].items():
        lines.append(f"| {seg_name} | {seg_info['count']:,} | {seg_info['pct']}% |")
    lines.append("")

    # ===== 6. 转化漏斗 =====
    f = report["funnel"]
    lines += [
        "## 6. 转化漏斗",
        "",
        "### 总体",
        f"- 浏览UV: {f['view_uv']:,}",
        f"- 加购UV: {f['addtocart_uv']:,} ({f['addtocart_rate']}%)",
        f"- 交易UV: {f['transaction_uv']:,} ({f['transaction_rate']}%)",
        f"- 整体转化率: {f['overall_cvr']}%",
        "",
        "### 工作日 vs 周末",
        "",
        "| 日期类型 | 浏览UV | 加购率 | 交易率 | 整体转化率 |",
        "|----------|--------|--------|--------|------------|",
    ]
    for _, seg in report["funnel_wd"].iterrows():
        lines.append(
            f"| {seg['group']} | {int(seg['view_uv']):,} | "
            f"{seg['addtocart_rate']}% | {seg['transaction_rate']}% | {seg['overall_cvr']}% |"
        )
    lines.append("")

    # ===== 7. 异常监控 =====
    lines += [
        "## 7. 异常监控",
        "",
        "### 各指标异常天数",
        "",
        "| 指标 | 3σ异常 | IQR异常 | 双规则命中 |",
        "|------|--------|---------|------------|",
    ]
    anom_summary = report["anomaly"]["summary"]
    metric_cols = [c for c in anom_summary if not c.startswith("_")]
    for col in metric_cols:
        info = anom_summary[col]
        lines.append(f"| {col} | {info['3sigma_days']} | {info['iqr_days']} | {info['both_days']} |")
    lines.append("")

    multi_days = anom_summary.get("_multi_anomaly_days", 0)
    if multi_days > 0:
        lines.append(f"### 综合异常日（≥3指标同时3σ异常）: {multi_days} 天")
        lines.append("")
        multi = report["anomaly"]["daily"]
        multi = multi[multi["multi_anomaly"] == 1]
        for _, row in multi.iterrows():
            date_str = str(row["date"])[:10]
            flagged = [c for c in metric_cols if row.get(f"{c}_3sigma", 0) == 1]
            lines.append(f"- **{date_str}**: {', '.join(flagged)}")
    else:
        lines.append("无综合异常日。")

    # ===== 8. 时序预测 =====
    if "forecast" in report:
        fc = report["forecast"]
        lines += [
            "## 8. 时序预测",
            "",
            "### 模型评估指标",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| MAE | {fc['mae']} |",
            f"| RMSE | {fc['rmse']} |",
            f"| MAPE | {fc['mape']}% |",
            "",
            "### 未来30天预测",
            "",
        ]
        future = fc["future"].copy()
        future["ds"] = future["ds"].dt.strftime("%Y-%m-%d")
        lines.append(future.rename(columns={
            "ds": "日期", "yhat": "预测值",
            "yhat_lower": "下限", "yhat_upper": "上限",
        }).to_markdown(index=False))
        lines.append("")

    # 写入文件
    path = os.path.join(output_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def export_pdf(output_dir: str, md_path: str) -> str:
    """将 Markdown 报告转为 PDF（需要安装 pandoc + wkhtmltopdf）"""
    pdf_path = md_path.replace(".md", ".pdf")
    import subprocess
    try:
        subprocess.run(
            ["pandoc", md_path, "-o", pdf_path, "--pdf-engine=wkhtmltopdf"],
            check=True, capture_output=True, text=True,
        )
        return pdf_path
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""  # pandoc 不可用时跳过
