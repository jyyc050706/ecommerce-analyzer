"""
概览页 — KPI 卡片 + 日趋势 + 漏斗概览
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import pandas as pd
from data_pipeline.cache import load_cached, get_daily_metrics, get_funnel
from dashboard.components.charts import (
    kpi_card, daily_trend_chart, funnel_chart, pie_chart,
)
from dashboard.components.styles import COLORS


@st.cache_data
def load_data():
    return load_cached("retailrocket")


def show():
    st.title("电商数据分析平台")

    df = load_data()
    daily = get_daily_metrics("retailrocket")
    funnel = get_funnel("retailrocket")

    # ===== KPI 行 =====
    total_events = len(df)
    total_users = df["user_id"].nunique()
    total_items = df["item_id"].nunique()
    tx_count = int(df["is_purchase"].sum())
    cvr_overall = round(tx_count / total_events * 100, 2)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(kpi_card("总事件数", f"{total_events/1e6:.2f}M"), unsafe_allow_html=True)
    with col2:
        st.markdown(kpi_card("独立用户", f"{total_users/1e4:.1f}万"), unsafe_allow_html=True)
    with col3:
        st.markdown(kpi_card("独立商品", f"{total_items/1e4:.1f}万"), unsafe_allow_html=True)
    with col4:
        st.markdown(kpi_card("交易数", f"{tx_count:,}"), unsafe_allow_html=True)
    with col5:
        st.markdown(kpi_card("整体转化率", f"{cvr_overall}%"), unsafe_allow_html=True)

    st.markdown("")

    # ===== 日趋势 + 漏斗 =====
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown('<div class="section-title">每日事件趋势</div>', unsafe_allow_html=True)
        fig = daily_trend_chart(daily, ["view", "addtocart", "transaction"], "事件量日趋势")
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-title">总体转化漏斗</div>', unsafe_allow_html=True)
        funnel_row = funnel.iloc[0]
        labels = ["浏览 (View)", "加购 (Add to Cart)", "交易 (Transaction)"]
        values = [int(funnel_row["view_uv"]), int(funnel_row["addtocart_uv"]), int(funnel_row["transaction_uv"])]
        fig2 = funnel_chart(labels, values)
        st.plotly_chart(fig2, use_container_width=True)

    # ===== 事件类型分布 + 工作日/周末 =====
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">事件类型分布</div>', unsafe_allow_html=True)
        pie_labels = ["浏览", "加购", "交易"]
        pie_values = [
            int((df["event_type"] == "view").sum()),
            int((df["event_type"] == "addtocart").sum()),
            int((df["event_type"] == "transaction").sum()),
        ]
        st.plotly_chart(pie_chart(pie_labels, pie_values), use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">活跃时段分布</div>', unsafe_allow_html=True)
        hour_counts = df["hour"].value_counts().sort_index()
        hour_df = pd.DataFrame({"hour": hour_counts.index, "count": hour_counts.values})
        from dashboard.components.charts import bar_chart
        st.plotly_chart(bar_chart(hour_df, "hour", "count", "小时活跃分布"), use_container_width=True)

