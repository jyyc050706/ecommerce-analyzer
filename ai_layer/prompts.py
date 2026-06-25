"""
Prompt 模板 — System Prompt + 数据上下文构建
"""

from data_pipeline.cache import get_daily_metrics, load_cached, get_user_profile, get_rfm, get_funnel, get_anomaly_report
from eda.user_profile import summary_stats
from eda.rfm_analysis import rfm_summary


def build_context() -> tuple[str, dict]:
    """返回 (system_prompt, preloaded_data) 供 Agent 使用"""

    df = load_cached("retailrocket")
    daily = get_daily_metrics("retailrocket")
    profile = get_user_profile("retailrocket")
    rfm = get_rfm("retailrocket")
    anom = get_anomaly_report("retailrocket")
    funnel_df = get_funnel("retailrocket")

    # ── 预计算摘要 ──
    total_events = len(df)
    total_users = df["user_id"].nunique()
    total_items = df["item_id"].nunique()
    tx_count = int(df["is_purchase"].sum())
    cvr = round(tx_count / total_events * 100, 2)

    et = df["event_type"].value_counts()

    # KPI
    kpi_lines = []
    for p_name, p_data in [("全周期", daily), ("近30天", daily.tail(30)), ("近7天", daily.tail(7))]:
        v = int(p_data["view"].sum())
        a = int(p_data["addtocart"].sum())
        t = int(p_data["transaction"].sum())
        cv = round(float(p_data["cvr_view_to_cart"].mean()), 2)
        ct = round(float(p_data["cvr_cart_to_tx"].mean()), 2)
        kpi_lines.append(f"- {p_name}: 浏览UV={v:,} 加购UV={a:,} 交易UV={t:,} 浏览→加购={cv}% 加购→交易={ct}%")

    # 异常
    daily_anom = anom["daily"]
    multi = daily_anom[daily_anom["multi_anomaly"] == 1]
    anom_dates = [str(r["date"])[:10] for _, r in multi.iterrows()]
    prop_res = anom["summary"].get("prophet_residual", {})
    anom_lines = f"""异常日（多指标同时命中）: {', '.join(anom_dates) if len(anom_dates) else '无'}
Prophet 残差异常: {prop_res.get('anomaly_days', 0)}天, 最大残差={prop_res.get('max_residual', 0):.1f}"""

    # 漏斗
    f = funnel_df.iloc[0]
    funnel_line = f"浏览UV={int(f['view_uv']):,} → 加购UV={int(f['addtocart_uv']):,}({f['addtocart_rate']}%) → 交易UV={int(f['transaction_uv']):,}({f['transaction_rate']}%) 整体转化率={f['overall_cvr']}%"

    # 分层
    seg = rfm_summary(rfm)
    seg_line = " | ".join(f"{k}={v['count']:,}({v['pct']}%)" for k, v in seg.items() if k not in ("total_users", "thresholds"))

    # 时段
    dp = float(profile["dawn_pct"].mean())
    mp = float(profile["morning_pct"].mean())
    ap = float(profile["afternoon_pct"].mean())
    np_ = float(profile["night_pct"].mean())

    # 画像
    stats = summary_stats(profile)

    summary = f"""## 业务摘要
| 项目 | 数值 |
|------|------|
| 总事件数 | {total_events:,} |
| 独立用户 | {total_users:,} |
| 独立商品 | {total_items:,} |
| 交易数 | {tx_count:,} |
| 整体转化率(事件级) | {cvr}% |
| 浏览/加购/交易 事件占比 | {int(et.get('view',0))/total_events*100:.1f}% / {int(et.get('addtocart',0))/total_events*100:.1f}% / {int(et.get('transaction',0))/total_events*100:.1f}% |
| 时段分布(凌晨/上午/下午/晚上) | {dp:.1f}% / {mp:.1f}% / {ap:.1f}% / {np_:.1f}% |
| 买家数 / 买家率 | {stats['buyers']:,} / {stats['buyer_rate']}% |
| 人均事件数 | {stats['avg_events_per_user']} |

KPI:
{kpi_lines[0]}
{kpi_lines[1]}
{kpi_lines[2]}

异常: {anom_lines}

漏斗: {funnel_line}

RFM用户分层: {seg_line}"""

    schema = """## 数据表 Schema（```python 代码块中可访问）

### daily (DataFrame, {daily_rows}行) — 每日聚合
列: date(str), total_events(int), view(int), addtocart(int), transaction(int), unique_users(int), unique_items(int), cvr_view_to_cart(float), cvr_cart_to_tx(float), cvr_overall(float), transaction_prophet_pred(float:Prophet拟合值), transaction_prophet_residual(float:残差), transaction_prophet_zscore(float:Z分数), transaction_prophet_flag(int:残差异常标记 0/1)

### df (DataFrame, {df_rows}行) — 原始事件
列: user_id(int), item_id(int), event_type(str: view/addtocart/transaction), timestamp(datetime), hour(int:0-23), day(int:1-31), weekday(int:0=周一,6=周日), month(int:5-9), is_weekend(int:0/1), date(str: YYYY-MM-DD), event_weight(int), is_purchase(int:0/1)

### profile (DataFrame, {profile_rows}行, index=user_id) — 用户画像
列: total_events(int), active_days(int), first_active(datetime), last_active(datetime), lifespan_days(int), weekday_pct(float), dawn_pct(float), morning_pct(float), afternoon_pct(float), night_pct(float), view_count(int), addtocart_count(int), transaction_count(int), is_buyer(int:0/1), cart_to_buy_rate(float)

### rfm (DataFrame, {rfm_rows}行, index=user_id) — RFM评分
列: R(int:距上次天数), F(int:总事件数), M(float:交易金额), R_score(int:1-5), F_score(int:1-5), M_score(int:1-5), RFM_total(int:3-15), segment(str:高价值/潜力用户/需要激活/流失风险/已流失)""".format(
        daily_rows=len(daily), df_rows=len(df),
        profile_rows=len(profile), rfm_rows=len(rfm),
    )

    system = f"""你是一个电商数据分析助手，基于 RetailRocket 电商数据集回答用户问题。

数据概况：{total_events:,} 条用户行为事件，{total_users:,} 用户，{total_items:,} 商品，时间跨度 2015-05-03 ~ 2015-09-18。

回答规则：
1. 下面提供了预计算摘要，优先用它直接回答
2. 摘要覆盖不了的问题，输出一个 ```python 代码块来查询数据，像这样：
```python
# 用 df/daily/profile/rfm 查询
result = daily[条件]
```
3. 代码块中可直接使用变量 df / daily / profile / rfm，这些是 pandas DataFrame
4. 代码必须赋值给 result 变量，系统会自动执行并告诉你结果
5. 只输出一个代码块，代码会被立即执行，执行结果会附加在下一条消息中
6. 语言简洁专业，引用具体数值
7. 用户上传图表图片后，可在 Python 代码中调用 read_chart("图片路径") 读取分析

### 内置工具函数（Python 代码中直接调用）
- read_chart(image_path: str) → dict: 读取图表图片，JSON 结构化输出（标题/坐标轴/数据点/图例/异常区域）
- analyze_chart(image_path: str, user_question: str) → str: 端到端识别图片并返回自然语言分析结论

{summary}

{schema}"""

    preloaded = {
        "df": df,
        "daily": daily,
        "profile": profile,
        "rfm": rfm,
    }
    return system, preloaded

