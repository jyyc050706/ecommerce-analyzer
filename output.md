# ecommerce-analyzer 开发交付记录

## P0 — 项目骨架 [✓] 

| 文件 | 用途 | 验证方式 |
|------|------|----------|
| 7 个模块目录 + `__init__.py` | 项目骨架目录 | 目录已创建 |
| `requirements.txt` | V1 核心依赖清单 | `pip install` 批量安装通过 |
| `config.py` | 路径 / LLM / Schema / 异常检测全局配置 | `python -c "import config"` 通过 |
| `data_pipeline/base_source.py` | `BaseDataSource` 抽象基类，统一标准 Schema | `python -c "from data_pipeline.base_source import BaseDataSource"` 通过 |

### BaseDataSource 对外接口

| 接口 | 类型 | 说明 |
|------|------|------|
| `load()` | 抽象方法 | 子类实现，加载原始数据返回 DataFrame |
| `column_mapping` | 抽象属性 | 原始列名 → 标准列名映射 dict |
| `transform()` | 公共方法 | 调用 load() 后自动映射为标准 Schema |
| `get_data()` | 公共方法 | 首次调用自动 load+transform，返回标准 DataFrame |
| `info()` | 公共方法 | 返回数据源摘要 {source, rows, users, items, date_range, event_types} |

### 标准 Schema

`user_id | item_id | event_type | timestamp`

---

## P1 — 数据管道 [✓] 

| 文件 | 用途 | 验证结果 |
|------|------|----------|
| `data_pipeline/load_raw.py` | RetailRocketSource 继承 BaseDataSource，映射 visitorid/itemid/event/timestamp → 标准 Schema | 加载 2,756,101 行，4 列标准字段 |
| `data_pipeline/clean.py` | 去重(460行)、类型转换、时间排序 | 清洗后 2,755,641 行，0 缺失，单调时间 |
| `data_pipeline/validate.py` | 数据质量校验报告（字段/一致性/统计概要） | 通过，仅 428 孤 transaction 警告（数据特性） |
| `data_pipeline/preprocess.py` | 时间衍生特征(hour/day/weekday/month/is_weekend)、事件权重、购买标记 | 12 列宽表，purchase rate 0.81% |

### 数据集概要

| 指标 | 值 |
|------|-----|
| 清洗后行数 | 2,755,641 |
| 用户数 | 1,407,580 |
| 商品数 | 235,061 |
| 时间跨度 | 2015-05-03 ~ 2015-09-18 (137 天) |
| view | 2,664,218 (96.68%) |
| addtocart | 68,966 (2.50%) |
| transaction | 22,457 (0.81%) |

---

## P2 — 探索分析 [✓] 

| 文件 | 用途 | 验证结果 |
|------|------|----------|
| `eda/user_profile.py` | 用户画像：15维特征宽表（活跃度/时段/行为/转化） | 1,407,580 用户，买家率 0.83%，71% 单次事件 |
| `eda/behavior_funnel.py` | 转化漏斗：总体/工作日周末/每日趋势 | view→cart 2.69%, cart→tx 31.07%, 整体 0.83% |
| `eda/retention.py` | 留存分析：次日/3/7/14/30日，分段对比 | Day1 2.76%, Day7 0.54%, Day30 0.13% |
| `eda/rfm_analysis.py` | RFM分层：R/F/M 五分档+5级分层 | 高价值 12.11%, 潜力 33.75%, 流失风险 18.36% |
| `eda/anomaly_detect.py` | 异常检测：3σ+IQR 双规则，9指标+综合异常 | 2 综合异常日（7/26 激增, 9/18 截断） |

### 关键洞察
- 71% 用户仅 1 次事件，典型的"浏览即走"模式
- 工作日转化率 (0.88%) 优于周末 (0.61%)
- 9/18 数据仅半天（最后一天），属数据截断非真实异常
- 沉默用户（流失风险+已流失）占 21.3%

---

## P3 — 看板 & 交互 [✓] 

| 文件 | 用途 | 验证结果 |
|------|------|----------|
| `dashboard/components/styles.py` | 配色方案 + KPI CSS 样式 | 导入通过 |
| `dashboard/components/charts.py` | 6个复用图表函数：日趋势/漏斗/柱状/饼图/留存/异常标记 | 导入通过 |
| `dashboard/pages/overview.py` | 概览页：KPI卡片+日趋势+漏斗+事件分布+小时分布 | 导入通过 |
| `dashboard/pages/user.py` | 用户分析页：用户画像分布+RFM分层+时段偏好 | 导入通过 |
| `dashboard/pages/funnel.py` | 漏斗分析页：总体/工作日周末/每日趋势 | 导入通过 |
| `dashboard/pages/anomaly.py` | 异常监控页：指标选择+异常日列表+综合异常详情 | 导入通过 |
| `dashboard/components/chat_drawer.py` | 底部弹出式聊天抽屉（AI分析助手） | 导入通过 |
| `dashboard/components/db.py` | SQLite持久化：daily_metrics/user_segments/rfm_thresholds 三表 | 导入通过 |
| `dashboard/components/export.py` | MD/PDF导出：report_YYYYMMDD_HHMM.md | 导入通过 |
| `dashboard/app.py` | Streamlit 主入口+侧边栏导航+报告导出 | 导入通过 |

### 看板启动

```bash
cd D:\ecommerce-analyzer
streamlit run dashboard\app.py
```

---

## P4 — AI 核心层 [✓] 

| 文件 | 用途 | 验证结果 |
|------|------|----------|
| `ai_layer/llm_client.py` | DeepSeek API + 智谱 GLM-4V vision_call（双模型路由） | 导入通过 |
| `ai_layer/prompts.py` | System Prompt + 5 场景分析模板 | 导入通过 |
| `ai_layer/tools/query_tools.py` | KPI/下钻/漏斗/环比/用户分层/Top商品 6 工具 | 导入通过 |
| `ai_layer/tools/nl2sql.py` | 自然语言→SQLite 查询 daily_metrics 表 | 导入通过 |
| `ai_layer/tools/chart_reader.py` | 智谱提取图表数据 → DeepSeek 分析（双模型接力） | 导入通过 |
| `ai_layer/insight_generator.py` | 数据→自然语言解读（解释/诊断/画像/异常/通用） | 导入通过 |
| `ai_layer/agent.py` | ReAct Agent：接收问题→规划工具→执行→回答，最多5步 | 导入通过 |
| `dashboard/components/chat_drawer.py` | 接入 Agent 替换 mock，快捷问题 + 自由输入 | 导入通过 |

### AI 使用前提

```bash
set DEEPSEEK_API_KEY=你的密钥
set ZHIPU_API_KEY=你的密钥    # 仅 chart_reader 需要，不设则图表识别不可用
```

未设置时聊天抽屉提示引导，看板其他功能不受影响。

---

## P4 补丁 — 环境配置 & UI 优化 [✓] 

| 文件 | 变更 | 说明 |
|------|------|------|
| `.env` | **新增** | 统一管理 DEEPSEEK_API_KEY / DEEPSEEK_MODEL / DEEPSEEK_BASE_URL / ZHIPU_VISION_MODEL / ZHIPU_API_KEY |
| `config.py` | **修改** | 新增 `from dotenv import load_dotenv` + `load_dotenv(..., override=True)`，`.env` 优先于系统环境变量 |
| `requirements.txt` | **修改** | 新增 `python-dotenv` |
| `dashboard/components/chat_drawer.py` | **重构** | 聊天框从独立组件升级为接收 `page` 参数，支持页面上下文感知 |
| `dashboard/pages/overview.py` | **修改** | 移除底部 `render_chat_drawer()` 调用 |
| `dashboard/pages/user.py` | **修改** | 移除底部 `render_chat_drawer()` 调用 + 清理重复 import |
| `dashboard/pages/funnel.py` | **修改** | 移除底部 `render_chat_drawer()` 调用 |
| `dashboard/pages/anomaly.py` | **修改** | 移除底部 `render_chat_drawer()` 调用 |

### .env 负载顺序

```
系统环境变量 → .env (override=True) → config.py → llm_client.py
```

---

## P5 — 侧边栏聊天重构 [✓] 

| 影响文件 | 变更 | 说明 |
|----------|------|------|
| `dashboard/app.py` | **修改** | `main()` 中新增 `render_chat_drawer(page)` 调用，聊天全局共享于侧边栏 |
| `dashboard/components/chat_drawer.py` | **重写** | 从页面底部独立组件改为侧边栏全局组件；使用 `st.sidebar.chat_input/chat_message`；仅渲染最近 6 条消息；传入当前页面 context 帮助 Agent 理解上下文 |

### 改造效果

- **始终可见**：聊天框固定于侧边栏底部（导出按钮下方），无需翻到页面末尾
- **全局共享**：四页共用同一聊天实例，消息历史跨页保持
- **页面感知**：Agent 知道用户当前在哪个页面（概览/用户/漏斗/异常），回答更精准

---

## P6 — 右侧可收起面板 [✓] 

| 影响文件 | 变更 | 说明 |
|----------|------|------|
| `dashboard/app.py` | **重构** | AI 聊天从侧边栏移到可收起右侧面板；新增 `_route_page()` 提取路由逻辑；顶部增加 `st.toggle("AI")` 切换按钮 |
| `dashboard/components/chat_drawer.py` | **重写** | 恢复 `st.` 上下文渲染（非 `st.sidebar.`），在右侧列面板中展示 |

### 交互方式

- 关闭状态（默认）：主区域占满全宽，右上角显示 "AI" 切换开关
- 打开状态：主区域 + 右侧聊天面板按 7:3 分栏，面板内包含快捷问题 + 输入框

---

## P7 — 聊天历史持久化 [✓] 

| 文件 | 变更 | 说明 |
|------|------|------|
| `dashboard/components/db.py` | **修改** | 新增 `chat_history` 表（role/content/created_at）+ `save_chat_message()` / `load_chat_history()` 函数 |
| `dashboard/components/chat_drawer.py` | **修改** | 启动时从 DB 加载最近 50 条历史；每条新消息（含快捷问题和回复）写入 DB |

### 持久化链路

```
用户发消息 → st.session_state 追加 → save_chat_message() 写入 SQLite
看板重启 → load_chat_history() 读取 → st.session_state 恢复
```

## BugFix — Agent 缺失异常查询工具 [✓] 

**问题**：用户问"出现异常的是哪几天"，Agent 用 `compare_period` 回答"最近7天 UV 下降 28.4%"，无法直接给出异常日期。根因：Agent 的 7 个工具（get_kpi/compare_period/drill_down/get_user_segments/get_top_items/get_funnel_data/nl2sql）均不访问异常检测结果，`get_anomaly_report()` 的数据只在异常监控页面直调，Agent 无法触及。

**修复**：
- `query_tools.py` 新增 `get_anomalies()` — 返回各指标异常天数汇总 + 综合异常日（multi_anomaly=1）及对应命中指标
- `agent.py` 在 TOOLS_DEF 注册第 8 个工具，`_execute_tool` 中分派 `get_anomalies`

## Refactor — ReAct Agent → Data-in-Prompt [✓] 

**动机**：用户指出"每次问问题都要补工具"是面子工程。改 Data-in-Prompt 模式：预计算所有业务数据快照，直接注入 System Prompt，LLM 一步回答，零工具编排。

**变更**：
- `agent.py`：删掉 ReAct 循环（JSON 解析 / `_execute_tool` / `_format_result` 全部移除），`run()` 改为一行 `chat()`；`max_steps` 参数保留但不使用以兼容调用方
- `prompts.py`：新增 `build_data_snapshot()` — 预计算 KPI 总览、环比、转化漏斗、异常检测、用户分层、近7天逐日表，拼接为 1671 字符 Markdown 快照；SYSTEM_PROMPT 从"能力声明"改为"直接引用快照"指引

## UI — 右侧 AI 面板独立滚轮条 [✓] 

**变更**：
- `chat_drawer.py`：聊天内容用 `st.container(height=500, border=False)` 包裹实现独立滚轮；显示条数从 6 扩大到 20；输入框抽到滚动容器外固定可见
- CSS 新增自定义滚动条样式（宽 6px / 灰色滑块 / 圆角）

## Refactor — Data-in-Prompt → 混合模式（摘要 + Code Interpreter）[✓] 

**动机**：Data-in-Prompt 模式弊端暴露——纯快照 8000 字符塞进 prompt，每次问新维度（如"近两周"、"周三转化率"）都触及盲区，本质和补工具是同一病根。用户提出混合方案：预计算摘要秒出已知问题，`run_python` 工具兜底未知查询，避免"能预判的还要重新写代码"。

**变更**：
- `prompts.py`：删 `build_data_snapshot()` 和 `SYSTEM_PROMPT`，新增 `build_context()` 返回 `(system_prompt, preloaded_data)`。摘要精简为 KPI 总览 + 异常 + 漏斗 + RFM 分层（约 300 字符），附完整数据表 schema（df/daily/profile/rfm 四表列定义）
- `agent.py`：删纯 Data-in-Prompt 单步调用，新增混合 ReAct 循环——LLM 可调用 `run_python(code)` 工具在预加载 DataFrame 上实时查询，最多 3 步，无工具调用则直接回答
- `llm_client.py`：新增 `chat_with_tools()` — 带工具定义的对话请求，返回 LLM 直接回答文本或工具调用请求 dict
- 删除 `output/data_snapshot.md` 缓存文件（不再需要）

## UI — AI 回答等待动效 [✓] 

**变更**：
- `chat_drawer.py`：用户发消息后立即显示用户气泡 + AI 侧 "..." 呼吸动效（CSS 动画三个点逐次闪烁），Agent 返回后替换为实际内容
- 实现方式：`pending_question` + `st.rerun()` 两段渲染——先渲染占位 "…" → 后台调用 Agent → 替换消息内容 → 再次 rerun 呈现结果

## Feature — 导出报告补全 [✓] 

**动机**：导出报告此前仅 4 节（每日指标/用户/漏斗/异常），看板上大部分分析维度未进报告。

**变更**：
- `export.py`：`export_md()` 从 5 参数改为接收 `report` 字典，报告扩至 7 节：数据规模、事件类型分布、KPI 多时段（全周期/近30天/近7天）、每日指标（近7天）、用户分析（活跃度分布+时段偏好+RFM分层）、转化漏斗（总体+工作日vs周末）、异常监控（各指标异常天数+综合异常日明细）
- `app.py`：`_do_export()` 重构，新增加载 `get_rfm` / `funnel_wd` / `load_cached`，构建完整 `report` 字典传入 `export_md`

## BugFix — 混合模式重构残留僵尸代码 [✓] 

**问题**：混合模式重构时删除了 `prompts.py` 中的 `SYSTEM_PROMPT` 和 `ANALYSIS_PROMPTS`，但有 3 处未同步清理：

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| 1 | `insight_generator.py` | `import SYSTEM_PROMPT, ANALYSIS_PROMPTS` → ImportError | 删除整个文件（功能已被 `agent.py` + `prompts.py` 替代） |
| 2 | `nl2sql.py` | `import SYSTEM_PROMPT` → ImportError（且从未使用） | 移除多余 import 行 |
| 3 | `query_tools.py:96` | `df.groupby("day_of_week")` → KeyError（实际列名为 `weekday`） | `day_of_week` → `weekday` |

## P5 — 时序预测 + 异常检测升级 [✓] 

三个模块全部实现：

| 模块 | 文件 | 变更 |
|------|------|------|
| Prophet 预测器 | `eda/forecaster.py`（新建，184行） | `Forecaster` 类：Prophet 封装，fit / predict / plot / components_plot / metrics 5 个公开方法。参数：日级频率、周季节性开启、无年/日季节性、changepoint_prior_scale=0.05 |
| 图表识别增强 | `ai_layer/tools/chart_reader.py`（增强） | `read_chart()` 新增 JSON parse + schema 校验，返回真正 dict 而非 raw 字符串；`_parse_json()` 3 种回退策略；`agent.py` 的 `_execute_python` 命名空间新增 `read_chart` / `analyze_chart` |
| 异常检测升级 | `eda/anomaly_detect.py`（+46行） + `dashboard/pages/anomaly.py`（+62行） | 新增 `detect_prophet_residual()`——Prophet 拟合历史日交易量 → 残差 3σ 标记，输出 4 列（pred/residual/zscore/flag）；接入 `anomaly_report` 作为独立第三层，不投票融合；看板新增 Prophet 拟合 vs 实际对比图 + 残差异常日明细表 |

## BugFix — 4项累积问题修复 [✓] 

| 序号 | 问题 | 根因 | 修复 |
|------|------|------|------|
| 1 | 导出报告缺少时序预测 | `_do_export` 未调用 `get_forecast_result`；`export.py` 无预测章节 | 新增 Part 8「时序预测」（模型评估指标 + 未来30天明细）；`export_md` 增加 `forecast` 段 |
| 2 | 导出报告导入缺失 | `get_forecast_result` 未加入 import | 添加到 `_do_export` 的 import 列表 |
| 3 | 预测页 AI 助手无上下文 | `PAGE_CONTEXT` 缺少 forecast | 添加 `"forecast": "当前页面是「时序预测」，展示Prophet预测指标、30天交易量预测图和明细表。"` |
| 4 | 概览页重复 `st.set_page_config` | `overview.py` show() 内重复调用（app.py 已调用） | 移除该行，消除 Streamlit 报错 |

## P5-Fix — 缓存不清 + 预测页缺失 [✓] 

| 问题 | 根因 | 修复 |
|------|------|------|
| 异常页 Prophet 图表不显示 | `retailrocket_anomaly_report.pkl` 旧缓存不含 Prophet 列 | 删除旧缓存文件，下次加载自动重新计算 |
| 时序预测未接入看板 | 只有模块无页面 | 新建 `dashboard/pages/forecast.py`，含 MAE/RMSE/MAPE 指标卡片、30天预测折线图、预测明细表；`cache.py` 新增 `get_forecast_result` 缓存；`app.py` 侧边栏注册「时序预测」导航项 |
