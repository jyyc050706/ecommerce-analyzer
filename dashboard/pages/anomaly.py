"""
异常监控页 — 多指标 3σ/IQR 异常检测可视化
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import pandas as pd
from data_pipeline.cache import load_cached, get_anomaly_report
from dashboard.components.charts import anomaly_chart, bar_chart
from dashboard.components.styles import COLORS

# 指标中英文映射
METRIC_LABELS = {
    "total_events": "总事件量",
    "view": "浏览",
    "addtocart": "加购",
    "transaction": "交易",
    "unique_users": "独立用户",
    "unique_items": "独立商品",
    "cvr_view_to_cart": "浏览→加购转化率",
    "cvr_cart_to_tx": "加购→交易转化率",
    "cvr_overall": "整体转化率",
}
LABEL_TO_COL = {v: k for k, v in METRIC_LABELS.items()}


@st.cache_data
def load_data():
    return load_cached("retailrocket")


def show():
    df = load_data()
    report = get_anomaly_report("retailrocket")
    daily = report["daily"]
    summary = report["summary"]

    st.title("异常监控")

    # ===== 异常摘要 =====
    st.markdown('<div class="section-title">异常检测摘要</div>', unsafe_allow_html=True)
    metric_cols = [c for c in summary if not c.startswith("_") and c != "prophet_residual"]
    
    summary_data = []
    for col in metric_cols:
        info = summary[col]
        summary_data.append({
            "指标": METRIC_LABELS.get(col, col),
            "3σ异常天数": info["3sigma_days"],
            "IQR异常天数": info["iqr_days"],
            "双规则命中": info["both_days"],
        })
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    multi_days = summary.get("_multi_anomaly_days", 0)
    if multi_days > 0:
        st.warning(f"综合异常日（≥3指标同时3σ异常）：{multi_days} 天")

    st.markdown("---")

    # ===== 选择指标查看 =====
    st.markdown('<div class="section-title">异常可视化</div>', unsafe_allow_html=True)
    label_options = [METRIC_LABELS.get(c, c) for c in metric_cols]
    selected_label = st.selectbox("选择指标", label_options)
    selected = LABEL_TO_COL[selected_label]

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(anomaly_chart(daily, selected), use_container_width=True)

    with col2:
        # 异常日列表
        anom_dates_3s = daily[daily[f"{selected}_3sigma"] == 1][["date", selected]]
        anom_dates_iqr = daily[daily[f"{selected}_iqr"] == 1][["date", selected]]
        
        if len(anom_dates_3s) > 0:
            st.caption(f"**3σ 异常日** ({len(anom_dates_3s)}天)")
            st.dataframe(anom_dates_3s.rename(columns={selected: "值"}), use_container_width=True, hide_index=True)
        else:
            st.success("3σ 检测：暂无异常日")
        
        if len(anom_dates_iqr) > 0:
            st.caption(f"**IQR 异常日** ({len(anom_dates_iqr)}天)")
            st.dataframe(anom_dates_iqr.rename(columns={selected: "值"}), use_container_width=True, hide_index=True)
        else:
            st.success("IQR 检测：暂无异常日")

    # ===== Prophet 残差异常检测 =====
    st.markdown("---")
    st.markdown('<div class="section-title">Prophet 残差异常检测（第三层）</div>', unsafe_allow_html=True)

    prop_summary = summary.get("prophet_residual", {})
    st.markdown(
        f"基于 Prophet 拟合历史日交易量 → 残差 3σ 检测。"
        f"异常日：{prop_summary.get('anomaly_days', 0)} 天 | "
        f"最大残差：{prop_summary.get('max_residual', 0):.1f} | "
        f"平均绝对残差：{prop_summary.get('mean_abs_residual', 0):.1f}"
    )

    if "transaction_prophet_pred" in daily.columns:
        import plotly.graph_objects as go
        fig = go.Figure()

        # 实际值
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["transaction"],
            mode="lines+markers", name="实际交易量",
            line=dict(color=COLORS["primary"], width=2),
            marker=dict(size=4),
        ))

        # Prophet 拟合值
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["transaction_prophet_pred"],
            mode="lines", name="Prophet 拟合",
            line=dict(color=COLORS["warning"], width=2, dash="dash"),
        ))

        # 残差异常点
        anom_mask = daily["transaction_prophet_flag"] == 1
        if anom_mask.any():
            fig.add_trace(go.Scatter(
                x=daily.loc[anom_mask, "date"],
                y=daily.loc[anom_mask, "transaction"],
                mode="markers", name="残差异常",
                marker=dict(color=COLORS["danger"], size=10, symbol="x"),
            ))

        fig.update_layout(
            title="Prophet 历史拟合 vs 实际（残差3σ异常标记）",
            template="plotly_dark",
            hovermode="x unified",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        # 残差异常日明细
        prop_anom = daily[anom_mask][["date", "transaction", "transaction_prophet_pred",
                                       "transaction_prophet_residual", "transaction_prophet_zscore"]]
        if len(prop_anom) > 0:
            st.caption(f"**残差 3σ 异常日明细** ({len(prop_anom)}天)")
            st.dataframe(
                prop_anom.round(2).rename(columns={
                    "transaction": "实际", "transaction_prophet_pred": "拟合",
                    "transaction_prophet_residual": "残差", "transaction_prophet_zscore": "Z-score",
                }),
                use_container_width=True, hide_index=True,
            )

    # ===== 综合异常日 =====
    if multi_days > 0:
        st.markdown('<div class="section-title">综合异常日详情</div>', unsafe_allow_html=True)
        multi = daily[daily["multi_anomaly"] == 1]
        for _, row in multi.iterrows():
            with st.expander(f"{row['date']}"):
                for col in metric_cols:
                    is_anom = row.get(f"{col}_3sigma", 0) == 1
                    emoji = "🔴" if is_anom else "🟢"
                    st.write(f"{emoji} {METRIC_LABELS.get(col, col)}: {row[col]}")

