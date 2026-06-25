"""
用户分析页 — 用户画像分布 + RFM 分层
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import pandas as pd
import numpy as np
from data_pipeline.cache import load_cached, get_user_profile, get_rfm
from eda.user_profile import summary_stats
from eda.rfm_analysis import rfm_summary
from dashboard.components.charts import bar_chart, pie_chart, retention_curve
from dashboard.components.styles import COLORS


@st.cache_data
def load_data():
    return load_cached("retailrocket")


def show():
    df = load_data()
    profile = get_user_profile("retailrocket")
    rfm = get_rfm("retailrocket")

    st.title("用户分析")

    # ===== 用户画像摘要 =====
    stats = summary_stats(profile)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总用户", f"{stats['total_users']/1e4:.0f}万")
    with col2:
        st.metric("买家数", f"{stats['buyers']:,}")
    with col3:
        st.metric("买家率", f"{stats['buyer_rate']}%")
    with col4:
        st.metric("人均事件", f"{stats['avg_events_per_user']}")

    st.markdown("---")

    # ===== 活跃度分布 =====
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">用户活跃度分布</div>', unsafe_allow_html=True)
        dist = stats["event_distribution"]
        act_df = pd.DataFrame({
            "活跃度": list(dist.keys()),
            "用户数": list(dist.values()),
        })
        st.plotly_chart(bar_chart(act_df, "活跃度", "用户数", "事件数分段"), use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">时段偏好</div>', unsafe_allow_html=True)
        time_labels = ["凌晨(0-5)", "上午(6-11)", "下午(12-17)", "晚上(18-23)"]
        time_vals = [
            float(profile["dawn_pct"].mean()),
            float(profile["morning_pct"].mean()),
            float(profile["afternoon_pct"].mean()),
            float(profile["night_pct"].mean()),
        ]
        st.plotly_chart(pie_chart(time_labels, time_vals, "用户平均时段分布"), use_container_width=True)

    # ===== RFM 分层 =====
    st.markdown('<div class="section-title">RFM 用户分层</div>', unsafe_allow_html=True)
    rfm_sum = rfm_summary(rfm)
    
    seg_data = []
    for seg, info in rfm_sum.items():
        if seg in ("total_users", "thresholds"):
            continue
        seg_data.append({"分层": seg, "用户数": info["count"], "占比(%)": info["pct"]})
    seg_df = pd.DataFrame(seg_data)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            bar_chart(seg_df, "分层", "用户数", "RFM 分层分布"),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            pie_chart(seg_df["分层"].tolist(), seg_df["用户数"].tolist(), "分层占比"),
            use_container_width=True,
        )

    # ===== RFM 阈值 =====
    with st.expander("RFM 评分阈值"):
        thresholds = rfm_sum.get("thresholds", {})
        for dim, info in thresholds.items():
            st.write(f"**{dim}** — 5分阈值: {info.get('5', 'N/A')}")

