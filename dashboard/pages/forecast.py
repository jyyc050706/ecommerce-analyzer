"""
时序预测页 — Prophet 日交易量预测
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import pandas as pd
from data_pipeline.cache import get_forecast_result
from dashboard.components.styles import COLORS


@st.cache_data
def load_forecast():
    return get_forecast_result("retailrocket", periods=30)


def show():
    data = load_forecast()
    daily = data["daily"]
    forecast = data["forecast"]
    metrics = data["metrics"]

    st.title("时序预测")

    # ===== 指标卡片 =====
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="label">MAE</div>
            <div class="value">{metrics['MAE']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="label">RMSE</div>
            <div class="value">{metrics['RMSE']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="label">MAPE</div>
            <div class="value">{metrics['MAPE']}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ===== 预测图 =====
    st.markdown('<div class="section-title">交易量预测（未来30天）</div>', unsafe_allow_html=True)

    import plotly.graph_objects as go

    fig = go.Figure()

    # 历史实际值（近60天）
    hist = daily.tail(60)
    fig.add_trace(go.Scatter(
        x=hist["date"], y=hist["transaction"],
        mode="markers", name="历史实际",
        marker=dict(color=COLORS["primary"], size=4),
    ))

    # 预测值
    fig.add_trace(go.Scatter(
        x=forecast["ds"], y=forecast["yhat"],
        mode="lines", name="预测值",
        line=dict(color=COLORS["warning"], width=2),
    ))

    # 置信区间
    fig.add_trace(go.Scatter(
        x=list(forecast["ds"]) + list(forecast["ds"][::-1]),
        y=list(forecast["yhat_upper"]) + list(forecast["yhat_lower"][::-1]),
        fill="toself",
        fillcolor="rgba(245,158,11,0.1)",
        line=dict(color="rgba(255,255,255,0)"),
        name="95% 置信区间",
    ))

    fig.update_layout(
        title="日交易量 — Prophet 预测",
        xaxis_title="日期",
        yaxis_title="交易数",
        template="plotly_dark",
        hovermode="x unified",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ===== 预测数据表 =====
    st.markdown("---")
    st.markdown('<div class="section-title">预测明细（未来30天）</div>', unsafe_allow_html=True)

    max_date = pd.Timestamp(daily["date"].max())
    future_only = forecast[forecast["ds"] > max_date].copy()
    future_only["ds"] = future_only["ds"].dt.strftime("%Y-%m-%d")
    future_only["yhat"] = future_only["yhat"].round(1)
    future_only["yhat_lower"] = future_only["yhat_lower"].round(1)
    future_only["yhat_upper"] = future_only["yhat_upper"].round(1)

    st.dataframe(
        future_only.rename(columns={
            "ds": "日期", "yhat": "预测值",
            "yhat_lower": "下限", "yhat_upper": "上限",
        }),
        use_container_width=True,
        hide_index=True,
    )
