"""
通用图表组件 — Plotly 封装的复用图表
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from dashboard.components.styles import COLORS, CHART_COLORS


def kpi_card(label: str, value: str, delta: str = "", delta_up: bool = True):
    """生成 KPI 卡片 HTML"""
    cls = "up" if delta_up else "down"
    delta_html = f'<div class="delta {cls}">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        {delta_html}
    </div>
    """


def daily_trend_chart(daily: pd.DataFrame, metric: str, title: str = "") -> go.Figure:
    """日趋势折线图（支持多指标）"""
    fig = go.Figure()
    metrics = metric if isinstance(metric, list) else [metric]
    for i, m in enumerate(metrics):
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily[m],
            mode="lines", name=m,
            line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=2),
        ))
    fig.update_layout(
        title=title or f"{metric} 日趋势",
        xaxis_title="日期",
        yaxis_title=metric if isinstance(metric, str) else "",
        template="plotly_white",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
    )
    return fig


def funnel_chart(labels: list, values: list, title: str = "转化漏斗") -> go.Figure:
    """漏斗图"""
    fig = go.Figure(go.Funnel(
        y=labels, x=values,
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=[COLORS["primary"], COLORS["primary_light"], COLORS["success"]]),
    ))
    fig.update_layout(
        title=title, template="plotly_white", height=350,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str = "",
              color: str = None, horizontal: bool = False) -> go.Figure:
    """通用柱状图"""
    if horizontal:
        fig = px.bar(df, y=x, x=y, title=title, orientation="h",
                      color=color, color_discrete_sequence=CHART_COLORS)
    else:
        fig = px.bar(df, x=x, y=y, title=title,
                      color=color, color_discrete_sequence=CHART_COLORS)
    fig.update_layout(
        template="plotly_white", height=350,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def pie_chart(labels: list, values: list, title: str = "") -> go.Figure:
    """饼图"""
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.4,
        marker=dict(colors=CHART_COLORS[:len(labels)]),
        textinfo="label+percent",
    ))
    fig.update_layout(
        title=title, template="plotly_white", height=350,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def retention_curve(days: list, rates: list, title: str = "留存曲线") -> go.Figure:
    """留存曲线"""
    fig = go.Figure(go.Scatter(
        x=days, y=rates, mode="lines+markers",
        line=dict(color=COLORS["primary"], width=3),
        marker=dict(size=8),
    ))
    fig.update_layout(
        title=title, template="plotly_white", height=350,
        xaxis_title="天数", yaxis_title="留存率 (%)",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def anomaly_chart(daily: pd.DataFrame, metric: str) -> go.Figure:
    """带异常标记的折线图"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily[metric],
        mode="lines", name=metric,
        line=dict(color=COLORS["primary"], width=2),
    ))

    # 异常点
    anomaly_col = f"{metric}_3sigma"
    if anomaly_col in daily.columns:
        anom = daily[daily[anomaly_col] == 1]
        if len(anom) > 0:
            fig.add_trace(go.Scatter(
                x=anom["date"], y=anom[metric],
                mode="markers", name="异常(3σ)",
                marker=dict(color=COLORS["danger"], size=10, symbol="x"),
            ))

    fig.update_layout(
        title=f"{metric} 异常检测",
        template="plotly_white", height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
    )

    # 3σ 上下界
    mean_val = daily[metric].mean()
    std_val = daily[metric].std()
    fig.add_hline(y=mean_val + 3*std_val, line_dash="dash", line_color=COLORS["warning"], opacity=0.5)
    fig.add_hline(y=mean_val - 3*std_val, line_dash="dash", line_color=COLORS["warning"], opacity=0.5)

    return fig
