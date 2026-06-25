"""
全局配置管理
所有路径和可变参数集中于此，其他模块通过 import config 引用。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

# ===== 项目根目录 =====
ROOT_DIR = Path(__file__).resolve().parent

# ===== 数据路径 =====
DATA_DIR = ROOT_DIR / "data"
DB_PATH = ROOT_DIR / "storage" / "ecommerce.db"

# ===== 标准 Schema 字段 =====
STANDARD_SCHEMA = {
    "user_id":    "用户唯一标识",
    "item_id":    "商品唯一标识",
    "event_type": "行为类型 (view/addtocart/transaction)",
    "timestamp":  "行为时间戳 (datetime)",
}

# ===== LLM 配置（环境变量优先） =====
LLM_CONFIG = {
    "api_key":      os.getenv("DEEPSEEK_API_KEY", ""),
    "base_url":     os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "model":        os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    "temperature":  0.1,
    "max_tokens":   4096,
}

# ===== 多模态配置（智谱 GLM-4V，仅识图时调用） =====
VISION_CONFIG = {
    "api_key":  os.getenv("ZHIPU_API_KEY", ""),
    "base_url": os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
    "model":    os.getenv("ZHIPU_VISION_MODEL", "glm-4v-flash"),
}

# ===== Streamlit 配置 =====
STREAMLIT_CONFIG = {
    "page_title": "ecommerce-analyzer",
    "layout":     "wide",
}

# ===== 预处理缓存 =====
CACHE_DIR = ROOT_DIR / "data" / "cache"
CURRENT_SOURCE = os.getenv("EAN_SOURCE", "retailrocket")  # 当前数据源名称

# ===== 异常检测阈值 =====
ANOMALY_CONFIG = {
    "sigma_threshold":   3.0,   # 3σ 离群值
    "iqr_multiplier":    1.5,   # IQR 系数
}
