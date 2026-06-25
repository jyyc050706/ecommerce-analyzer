"""
主题配色与样式 — 统一定义 Streamlit 看板视觉风格
"""

import streamlit as st


# 配色方案 — 冷蓝色系专业风
COLORS = {
    "primary": "#2563EB",        # 主色蓝
    "primary_light": "#DBEAFE", # 浅蓝背景
    "success": "#16A34A",       # 绿色（正向指标）
    "warning": "#F59E0B",       # 黄色（警示）
    "danger": "#DC2626",        # 红色（异常/负向）
    "dark": "#1E293B",          # 深色文字
    "gray": "#94A3B8",          # 灰色辅助
    "bg_card": "#FFFFFF",       # 卡片背景
    "bg_page": "#F8FAFC",       # 页面背景
    "border": "#E2E8F0",       # 边框
}

# 图表配色序列
CHART_COLORS = ["#2563EB", "#16A34A", "#F59E0B", "#DC2626", "#8B5CF6", "#EC4899"]


def apply_styles():
    """注入全局 CSS 样式"""
    css = f"""
    <style>
    /* 全局 */
    .stApp {{
        background-color: {COLORS["bg_page"]};
    }}

    /* KPI 卡片 */
    .kpi-card {{
        background: {COLORS["bg_card"]};
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border: 1px solid {COLORS["border"]};
        text-align: center;
    }}
    .kpi-card .label {{
        font-size: 13px;
        color: {COLORS["gray"]};
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .kpi-card .value {{
        font-size: 32px;
        font-weight: 700;
        color: {COLORS["dark"]};
    }}
    .kpi-card .delta {{
        font-size: 14px;
        margin-top: 4px;
    }}
    .kpi-card .delta.up {{ color: {COLORS["success"]}; }}
    .kpi-card .delta.down {{ color: {COLORS["danger"]}; }}

    /* 区块标题 */
    .section-title {{
        font-size: 18px;
        font-weight: 600;
        color: {COLORS["dark"]};
        margin: 24px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid {COLORS["primary"]};
        display: inline-block;
    }}

    /* 底部聊天抽屉 */
    .chat-drawer-container {{
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 9999;
    }}

    /* ===== 侧边栏导航 ===== */
    .sidebar-brand {{
        font-size: 22px;
        font-weight: 800;
        color: {COLORS["dark"]};
        padding: 8px 0 2px 0;
        letter-spacing: 0.5px;
    }}
    .sidebar-subtitle {{
        font-size: 12px;
        color: {COLORS["gray"]};
        margin-bottom: 4px;
    }}
    .sidebar-divider {{
        margin: 12px 0;
        border: none;
        border-top: 1px solid {COLORS["border"]};
    }}
    .sidebar-footer {{
        font-size: 11px;
        color: {COLORS["gray"]};
        line-height: 1.6;
        padding-top: 4px;
    }}

    /* 导航按钮 */
    div[data-testid="stSidebar"] .stButton > button {{
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 15px;
        font-weight: 500;
        text-align: left;
        transition: all 0.15s ease;
        margin-bottom: 2px;
        border: 1px solid {COLORS["border"]};
    }}
    div[data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
        background: transparent;
        color: {COLORS["dark"]};
    }}
    div[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {{
        background: {COLORS["primary_light"]};
        border-color: {COLORS["primary"]};
        color: {COLORS["primary"]};
    }}
    div[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background-color: #94A3B8 !important;
        color: #FFFFFF !important;
        border-color: #94A3B8 !important;
        box-shadow: none !important;
    }}

    /* 收缩侧边栏 padding */
    div[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        gap: 2px;
    }}

    /* Streamlit 自动导航 — 隐藏 */
    [data-testid="stSidebarNavItems"] {{
        display: none !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
