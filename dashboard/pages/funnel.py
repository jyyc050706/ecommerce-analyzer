"""
漏斗分析页 — 总体漏斗 + 工作日/周末对比 + 每日转化率趋势
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import pandas as pd
from data_pipeline.cache import load_cached, get_funnel, get_daily_metrics
from dashboard.components.charts import funnel_chart, bar_chart, daily_trend_chart
from dashboard.components.styles import COLORS


@st.cache_data
def load_data():
    return load_cached("retailrocket")


def show():
    df = load_data()
    funnel = get_funnel("retailrocket")
    funnel_wd = get_funnel("retailrocket", "weekday")
    daily = get_daily_metrics("retailrocket")

    st.title("转化漏斗分析")

    # ===== 总体漏斗 =====
    st.markdown('<div class="section-title">总体转化漏斗</div>', unsafe_allow_html=True)
    row = funnel.iloc[0]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("浏览 → 加购", f"{row['addtocart_rate']}%",
                  f"{int(row['addtocart_uv']):,} / {int(row['view_uv']):,}")
    with col2:
        st.metric("加购 → 交易", f"{row['transaction_rate']}%",
                  f"{int(row['transaction_uv']):,} / {int(row['addtocart_uv']):,}")
    with col3:
        st.metric("整体转化率", f"{row['overall_cvr']}%")

    funnel_labels = ["浏览", "加购", "交易"]
    funnel_vals = [int(row["view_uv"]), int(row["addtocart_uv"]), int(row["transaction_uv"])]
    st.plotly_chart(funnel_chart(funnel_labels, funnel_vals), use_container_width=True)

    st.markdown("---")

    # ===== 工作日 vs 周末 =====
    st.markdown('<div class="section-title">工作日 vs 周末</div>', unsafe_allow_html=True)
    cols = st.columns(len(funnel_wd))
    for i, (_, seg) in enumerate(funnel_wd.iterrows()):
        with cols[i]:
            st.metric(
                seg["group"],
                f"转化率 {seg['overall_cvr']}%",
                delta=f"浏览 {int(seg['view_uv']):,}",
            )
            st.caption(f"加购率 {seg['addtocart_rate']}% | 交易率 {seg['transaction_rate']}%")

    # ===== 每日转化率趋势 =====
    st.markdown('<div class="section-title">每日转化率趋势</div>', unsafe_allow_html=True)
    fig = daily_trend_chart(daily, ["cvr_view_to_cart", "cvr_cart_to_tx"], "转化率日趋势")
    fig.update_layout(yaxis_title="转化率 (%)")
    st.plotly_chart(fig, use_container_width=True)

    # ===== 每日各层 UV =====
    st.markdown('<div class="section-title">每日各层UV</div>', unsafe_allow_html=True)
    funnel_daily = get_funnel("retailrocket", "date")
    fig2 = daily_trend_chart(funnel_daily, ["view_uv", "addtocart_uv", "transaction_uv"], "各层UV日趋势")
    fig2.update_layout(yaxis_title="UV")
    st.plotly_chart(fig2, use_container_width=True)

