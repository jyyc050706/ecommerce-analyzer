"""
ecommerce-analyzer 看板主入口
"""

import os, streamlit as st
from dashboard.components.styles import apply_styles
from dashboard.components.export import export_md
from dashboard.components.chat_drawer import render_chat_drawer

NAV_ITEMS = [
    ("◉", "概览",      "overview"),
    ("👤", "用户分析",  "user"),
    ("▼", "转化漏斗",  "funnel"),
    ("⊗", "异常监控",  "anomaly"),
    ("↗", "时序预测",  "forecast"),
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def render_sidebar():
    """渲染侧边栏导航"""
    st.sidebar.markdown(
        '<div class="sidebar-brand">电商数据分析平台</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)

    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "overview"

    for icon, label, key in NAV_ITEMS:
        active = st.session_state.nav_page == key
        if st.sidebar.button(
            f"{icon}  {label}",
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            st.session_state.nav_page = key
            st.rerun()

    st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="sidebar-footer">数据源: RetailRocket<br>275 万事件 · 140 万用户</div>',
        unsafe_allow_html=True,
    )

    if st.sidebar.button("📄 导出报告", use_container_width=True, type="secondary"):
        st.session_state.trigger_export = True

    return st.session_state.nav_page


def _route_page(page):
    """根据 nav_page 路由到对应页面"""
    if page == "overview":
        from dashboard.pages.overview import show
        show()
    elif page == "user":
        from dashboard.pages.user import show
        show()
    elif page == "funnel":
        from dashboard.pages.funnel import show
        show()
    elif page == "anomaly":
        from dashboard.pages.anomaly import show
        show()
    elif page == "forecast":
        from dashboard.pages.forecast import show
        show()


def main():
    st.set_page_config(
        page_title="ecommerce-analyzer",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_styles()

    page = render_sidebar()

    # 右侧 AI 助手切换按钮
    c1, c2 = st.columns([14, 1])
    with c2:
        show_chat = st.toggle(
            "AI",
            value=st.session_state.get("show_chat", False),
            key="chat_toggle",
        )
        st.session_state.show_chat = show_chat

    if show_chat:
        col_main, col_chat = st.columns([7, 3])
        with col_chat:
            render_chat_drawer(page)
        with col_main:
            _route_page(page)
    else:
        _route_page(page)

    # 导出报告
    if st.session_state.get("trigger_export"):
        _do_export()
        st.session_state.trigger_export = False


def _do_export():
    from data_pipeline.cache import (
        get_daily_metrics, get_funnel, get_user_profile,
        get_rfm, get_anomaly_report, get_forecast_result, load_cached,
    )
    from eda.user_profile import summary_stats
    from eda.rfm_analysis import rfm_summary
    import pandas as pd

    with st.spinner("正在生成报告..."):
        daily = get_daily_metrics("retailrocket")
        funnel = get_funnel("retailrocket")
        funnel_wd = get_funnel("retailrocket", group_by="weekday")
        profile = get_user_profile("retailrocket")
        rfm = get_rfm("retailrocket")
        anomaly = get_anomaly_report("retailrocket")
        df = load_cached("retailrocket")

        stats = summary_stats(profile)

        # ---- 1. 数据规模 ----
        total_events = int(profile["total_events"].sum())
        total_items = int(df["item_id"].nunique())
        tx_count = int(profile["transaction_count"].sum())
        cvr_events = round(tx_count / total_events * 100, 4)
        date_min = str(daily["date"].min())[:10]
        date_max = str(daily["date"].max())[:10]

        scale = {
            "total_events": total_events,
            "total_users": stats["total_users"],
            "total_items": total_items,
            "tx_count": tx_count,
            "cvr": cvr_events,
            "date_range": f"{date_min} ~ {date_max}",
        }

        # ---- 2. 事件类型分布 ----
        et = {
            "view": int(profile["view_count"].sum()),
            "addtocart": int(profile["addtocart_count"].sum()),
            "transaction": int(profile["transaction_count"].sum()),
        }
        et["view_pct"] = round(et["view"] / total_events * 100, 1)
        et["addtocart_pct"] = round(et["addtocart"] / total_events * 100, 1)
        et["transaction_pct"] = round(et["transaction"] / total_events * 100, 1)

        # ---- 3. KPI 多时段 ----
        max_date = daily["date"].max()
        mask_30d = daily["date"] >= max_date - pd.Timedelta(days=30)
        mask_7d = daily["date"] >= max_date - pd.Timedelta(days=7)

        def _agg_period(mask):
            d = daily[mask]
            if len(d) == 0:
                return {}
            cvr_vc = round(d["cvr_view_to_cart"].mean(), 2)
            cvr_ct = round(d["cvr_cart_to_tx"].mean(), 2)
            cvr_ov = round(d["cvr_overall"].mean(), 4)
            return {
                "total_events": f"{int(d['total_events'].sum()):,}",
                "unique_users": f"{d['unique_users'].max():,}",
                "view": f"{int(d['view'].sum()):,}",
                "addtocart": f"{int(d['addtocart'].sum()):,}",
                "transaction": f"{int(d['transaction'].sum()):,}",
                "cvr(view→cart)": f"{cvr_vc}%",
                "cvr(cart→tx)": f"{cvr_ct}%",
                "cvr(overall)": f"{cvr_ov}%",
            }

        overall_kpi = _agg_period(pd.Series(True, index=daily.index))
        kpi_30d = _agg_period(mask_30d)
        kpi_7d = _agg_period(mask_7d)

        kpi_rows = []
        for key in overall_kpi:
            kpi_rows.append({
                "label": key,
                "overall": overall_kpi.get(key, "N/A"),
                "last_30d": kpi_30d.get(key, "N/A"),
                "last_7d": kpi_7d.get(key, "N/A"),
            })

        # ---- 5. 用户分析 ----
        hour_pcts = {
            "dawn_pct": round(profile["dawn_pct"].mean(), 1),
            "morning_pct": round(profile["morning_pct"].mean(), 1),
            "afternoon_pct": round(profile["afternoon_pct"].mean(), 1),
            "night_pct": round(profile["night_pct"].mean(), 1),
        }
        users = dict(stats)
        users.update(hour_pcts)

        # ---- RFM 分层 ----
        rfm_data = rfm_summary(rfm)
        # 只保留各分层数据，排除 thresholds 和 total_users
        rfm_segments = {k: v for k, v in rfm_data.items() if k not in ("total_users", "thresholds")}

        # ---- 6. 总体漏斗 ----
        funnel_row = funnel.iloc[0]
        funnel_data = {
            "view_uv": int(funnel_row["view_uv"]),
            "addtocart_uv": int(funnel_row["addtocart_uv"]),
            "addtocart_rate": funnel_row["addtocart_rate"],
            "transaction_uv": int(funnel_row["transaction_uv"]),
            "transaction_rate": funnel_row["transaction_rate"],
            "overall_cvr": funnel_row["overall_cvr"],
        }

        # ---- 8. 时序预测 ----
        forecast = get_forecast_result("retailrocket", periods=30)
        fc_metrics = forecast["metrics"]
        fc_df = forecast["forecast"]
        max_date = pd.Timestamp(daily["date"].max())
        future_only = fc_df[fc_df["ds"] > max_date].copy()
        forecast_data = {
            "mae": fc_metrics["MAE"],
            "rmse": fc_metrics["RMSE"],
            "mape": fc_metrics["MAPE"],
            "future": future_only,
        }

        # 组装
        report = {
            "scale": scale,
            "event_types": et,
            "kpi": kpi_rows,
            "daily": daily,
            "users": users,
            "rfm": rfm_segments,
            "funnel": funnel_data,
            "funnel_wd": funnel_wd,
            "anomaly": anomaly,
            "forecast": forecast_data,
        }

        path = export_md(OUTPUT_DIR, report)
        st.success(f"报告已生成：{path}")


if __name__ == "__main__":
    main()
