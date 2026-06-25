# ecommerce-analyzer

基于 Kaggle RetailRocket 电商用户行为数据集的端到端数据分析平台，集成 AI Agent 智能分析引擎。
仅本地运行，数据一次性批量导入分析
## 技术栈

| 层 | V1 选型 | V2 补充 |
|----|---------|---------|
| AI 主模型 | DeepSeek（文本推理 / nl2sql） | 不变 |
| 视觉模型 | 不需要 | 智谱（chart_reader） |
| Web 框架 | Streamlit | 不变 |
| 数据处理 | Pandas + SQLite | 不变 |
| 可视化 | Plotly（交互优先） | 不变 |
| 预测 | — | Prophet |

## 交互设计

- **模式**：对话式深度追问。Agent 返回分析结果后，用户可连续追问"为什么"、"拆解到 XX 维度"，Agent 保持上下文持续下钻。
- **聊天框**：侧边栏。看板全屏沉浸，AI 助手始终可见于侧边栏底部。
- **对话布局**：AI 回复左侧（蓝底 + AI 头像），用户消息右侧（蓝底 + 用户头像）。
- **报告导出**：任意分析结果支持一键导出 Markdown / PDF。
- **持久化**：SQLite 存储对话历史 + 分析产物（图表截图、数据表），关闭重开完整还原分析现场。实现于 `dashboard/components/db.py`。

### 持久化存储结构

```sql
sessions (session_id, created_at, title)
messages (message_id, session_id, role, content, created_at)
artifacts (artifact_id, message_id, type, file_path, created_at)
```

## 多数据源抽象层

统一标准 Schema：`user_id | item_id | event_type | timestamp`

| 标准字段 | RetailRocket 映射 | CSV 新源映射 |
|----------|------------------|-------------|
| user_id | ← visitorid | ← 用户ID |
| item_id | ← itemid | ← 商品ID |
| event_type | ← event | ← 行为类型 |
| timestamp | ← timestamp | ← 时间 |

`BaseDataSource` 抽象基类，`RetailRocketSource` 和 `CSVGenericSource` 分别实现。
下游分析模块（画像/漏斗/RFM/异常检测）只认标准字段，不关心数据来源。

## 项目结构

```
ecommerce-analyzer/
├── config.py                      # 全局配置（路径、参数）
├── requirements.txt
├── .streamlit/
│   └── config.toml                # Streamlit 主题配置
│
├── data/                          # 原始数据集（已手动下载）
│
├── data_pipeline/                 # 数据清洗流水线
│   ├── base_source.py             #   BaseDataSource 抽象基类
│   ├── load_raw.py                #   加载原始数据（CSV）
│   ├── clean.py                   #   缺失值/异常值/类型转换
│   ├── validate.py                #   数据质量校验报告
│   ├── preprocess.py              #   特征工程
│   └── cache.py                   #   SQLite 缓存（加载后持久化）
│
├── eda/                           # 探索性分析
│   ├── user_profile.py            #   用户画像
│   ├── behavior_funnel.py         #   转化漏斗
│   ├── retention.py               #   留存分析
│   ├── rfm_analysis.py            #   RFM分层
│   ├── anomaly_detect.py          #   异常检测（3σ/IQR/Prophet残差三层）
│   └── forecaster.py              #   Prophet 时序预测器
│
├── monitor/                       # 指标监控（占位，待扩展）
│
├── dashboard/                     # Streamlit 可视化看板
│   ├── app.py                     #   主入口（路由、导出、持久化控制）
│   ├── pages/
│   │   ├── overview.py            #   概览页（KPI + 日趋势 + 事件分布）
│   │   ├── user.py                #   用户分析页（画像 + RFM）
│   │   ├── funnel.py              #   漏斗分析页
│   │   ├── anomaly.py             #   异常监控页（3层检测+明细）
│   │   └── forecast.py            #   时序预测页（Prophet预测图+表）
│   └── components/
│       ├── charts.py              #   通用图表组件
│       ├── chat_drawer.py         #   侧边栏 AI 聊天组件
│       ├── db.py                  #   SQLite 对话持久化
│       ├── export.py              #   报告导出（Markdown）
│       └── styles.py              #   主题配色
│
├── ai_layer/                      # AI 智能层
│   ├── agent.py                   #   混合模式 Agent（ReAct + 上下文感知）
│   ├── llm_client.py              #   LLM API 封装（DeepSeek）
│   ├── prompts.py                 #   Prompt 模板与 daily 快照
│   └── tools/
│       ├── nl2sql.py              #   自然语言转 SQL
│       ├── query_tools.py         #   KPI/下钻/漏斗/同环比
│       └── chart_reader.py        #   多模态图表识别（视觉 LLM）
│
└── output/                        # 导出报告产物
```

## AI 层设计

### 底层

| 文件 | 职责 |
|------|------|
| `llm_client.py` | DeepSeek API 封装（OpenAI 兼容接口），含视觉模型路由 |
| `agent.py` | 混合模式 Agent（ReAct + Python 代码执行），含上下文感知与 daily 快照注入 |
| `prompts.py` | Prompt 模板、`PAGE_CONTEXT` 页面感知文案、`DAILY_SNAPSHOT` 数据摘要构建 |

### 工具层

| 工具 | 阶段 | 功能 | 输入示例 | 输出 |
|------|------|------|---------|------|
| `nl2sql` | V1 | 自然语言转 SQL 查询 | "上月 GMV 最高的 10 个商品" | SQL + 结果 + 自动图表 |
| `query_tools` | V1 | KPI / 下钻 / 漏斗 / 同环比 | "转化率按渠道拆解" | 分维度数据表 + 图表 |
| `chart_reader` | V2 | 视觉 LLM 识别图表 | 看板截图 | 提取数据 + 对比分析 |
| `forecaster` | V2 | Prophet 时序预测（EDA 模块，Agent 通过 `get_forecast_result` 调用） | 历史 N 天交易量 | 未来 30 天预测 + 置信区间 |

### Agent 调度层

`agent.py` — 混合模式（ReAct + Python），运行时链路：

```
用户: "为什么上周转化率跌了？"
  ↓ Agent 自主规划
  ├─ query_tools.get_kpi("转化率", "上周")          → 2.1%, 环比 -18%
  ├─ query_tools.drill_down("转化率", "渠道")        → 移动端 -25%, PC 持平
  └─ query_tools.compare_period("转化率", "去年同期") → 去年同期 -12%
  ↓ LLM 汇总分析
  ↓ 返回完整分析报告（数据 + 归因 + 建议 + 图表）
  ↓ 用户追问："移动端具体哪个环节掉的？"
  ↓ Agent 继承上下文，继续下钻 → 漏斗按步骤拆解
```

## 开发计划（分阶段渐进）

### V1 — 核心闭环（P0 ~ P4）

| 板块 | 内容 | 交付物 | 状态 |
|------|------|--------|------|
| P0 | 项目骨架：目录结构、requirements.txt、配置管理、BaseDataSource 抽象基类 | 可运行空框架 | [✓] |
| P1 | 数据管道：RetailRocket 加载/清洗/校验/特征工程 | 清洗后数据集 + 质量报告 | [✓] |
| P2 | 探索分析：用户画像、转化漏斗、留存、RFM、异常检测（统计规则 3σ/IQR） | 各模块独立脚本 | [✓] |
| P3 | 看板 + 聊天底座：Streamlit 多页面、底部抽屉聊天框、报告导出 MD/PDF、对话持久化 | 完整可访问看板 | [✓] |
| P4 | AI 核心层：DeepSeek API 封装、ReAct Agent、nl2sql、query_tools、insight_generator | 看板内可对话分析 | [✓] |

### V2 — 预测增强（P5）

| 板块 | 内容 | 交付物 | 状态 |
|------|------|--------|------|
| P5 | Prophet 时序预测 + chart_reader 多模态（视觉模型） + 异常检测增强（统计+时序） | 预测 + 多模态能力 | [✓] |



## 数据集

[Kaggle RetailRocket E-commerce Dataset](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset)，140 万条用户行为记录（浏览、加购、交易）。已手动下载至 `data/` 目录。

## 启动

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```
