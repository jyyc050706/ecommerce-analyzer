---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 74183af673f5cbc652e1643d5fb4a0aa_4982c28c707c11f1aabe5254007bceed
    ReservedCode1: aC3zcBMYmznab0zacJ+NgRmyBTKR5aIW4NgErdotiKoZVqtVmbJ1R9J8EJTbr+yvtl72I9/u4wU725qFHub3nCv7CIf9JausGdUjKE8YdHOO/wPdrgBEa5GBSQ59Rz6xMPPQaZKtAOuZvK/6p7klmt9SXdqPKQL5Uh6TNCBKPsnrD8O1Z8NSI37Iyt4=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 74183af673f5cbc652e1643d5fb4a0aa_4982c28c707c11f1aabe5254007bceed
    ReservedCode2: aC3zcBMYmznab0zacJ+NgRmyBTKR5aIW4NgErdotiKoZVqtVmbJ1R9J8EJTbr+yvtl72I9/u4wU725qFHub3nCv7CIf9JausGdUjKE8YdHOO/wPdrgBEa5GBSQ59Rz6xMPPQaZKtAOuZvK/6p7klmt9SXdqPKQL5Uh6TNCBKPsnrD8O1Z8NSI37Iyt4=
---

# ecommerce-analyzer

端到端电商数据分析平台，基于 Kaggle RetailRocket 140 万条用户行为数据，集成 AI Agent 智能分析引擎。

## 技术亮点

- **Agent 混合架构**：ReAct + Python 代码执行，支持自然语言对话式深度分析、自动 SQL 生成、图表识别
- **三层异常检测**：统计规则（3σ/IQR） + Prophet 时序残差 + 多维交叉标记
- **Prophet 时序预测**：30 天交易量预测 + 置信区间 + 模型评估指标（MAE/RMSE/MAPE）
- **5 页面 Streamlit 看板**：概览 / 用户分析 / 漏斗 / 异常监控 / 时序预测，含 AI 聊天抽屉
- **对话持久化**：SQLite 存储会话历史与分析产物，关闭重开完整还原
- **分阶段工程化**：P0~P5 渐进式开发，每阶段独立交付，方案文档与输出日志完整

## 快速开始

```bash
git clone https://github.com/xxx/ecommerce-analyzer.git
cd ecommerce-analyzer
pip install -r requirements.txt

# 需配置 DeepSeek API Key
# 编辑 config.py 或设置环境变量 DEEPSEEK_API_KEY

streamlit run dashboard/app.py
```

## 项目结构

```
ecommerce-analyzer/
├── config.py                      # 全局配置
├── data/                          # RetailRocket 数据集
├── data_pipeline/                 # 数据清洗（加载/校验/特征工程/缓存）
├── eda/                           # 探索分析（画像/漏斗/留存/RFM/异常/预测）
├── dashboard/                     # Streamlit 看板（5 页面 + AI 聊天 + 导出）
├── ai_layer/                      # AI 智能层（Agent/nl2sql/chart_reader）
├── output/                        # 导出报告
├── ecommerce-analyzer-方案.md      # 完整方案文档
└── output.md                      # 开发日志
```

## 技术栈

| 层 | 选型 |
|----|------|
| AI 模型 | DeepSeek（文本）+ 通义千问 VL（视觉） |
| Web 框架 | Streamlit |
| 数据处理 | Pandas + SQLite |
| 可视化 | Plotly |
| 时序预测 | Prophet |

## 数据集

[Kaggle RetailRocket E-commerce Dataset](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset) — 137 天用户行为记录（浏览 / 加购 / 交易），涵盖 140 万事件、31 万独立商品。

## 许可证

MIT
*（内容由AI生成，仅供参考）*
