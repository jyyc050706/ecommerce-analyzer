"""
多数据源抽象基类
所有数据源（RetailRocket / CSV / 数据库等）必须实现此接口，
输出统一的标准 Schema 给下游分析模块使用。
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import STANDARD_SCHEMA


class BaseDataSource(ABC):
    """数据源抽象基类，子类只需实现 load() 和 _column_mapping"""

    def __init__(self, source_path: Path):
        self.source_path = Path(source_path)
        self.df: Optional[pd.DataFrame] = None

    # ---------- 子类必须实现 ----------

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """加载原始数据，返回原始 DataFrame"""
        ...

    @property
    @abstractmethod
    def column_mapping(self) -> dict:
        """原始列名 → 标准列名的映射字典，如 {'visitorid': 'user_id', ...}"""
        ...

    # ---------- 公共方法 ----------

    def transform(self) -> pd.DataFrame:
        """将原始 DataFrame 转为标准 Schema 格式"""
        if self.df is None:
            self.df = self.load()

        mapping = self.column_mapping

        # 检查必需字段
        missing = [k for k in STANDARD_SCHEMA if k not in mapping.values()]
        if missing:
            raise ValueError(f"列映射缺少标准字段: {missing}")

        # 提取并重命名
        reverse_map = {v: k for k, v in mapping.items()}
        cols_in_source = [reverse_map[std_col] for std_col in STANDARD_SCHEMA]
        df_std = self.df[cols_in_source].copy()
        df_std.rename(columns=mapping, inplace=True)

        # 时间标准化
        df_std["timestamp"] = pd.to_datetime(df_std["timestamp"], errors="coerce")

        # 剔除无效行
        df_std.dropna(subset=list(STANDARD_SCHEMA.keys()), inplace=True)

        return df_std.reset_index(drop=True)

    def get_data(self) -> pd.DataFrame:
        """获取标准格式数据（首次调用自动 load + transform）"""
        return self.transform()

    def info(self) -> dict:
        """返回数据源摘要信息"""
        df = self.get_data()
        return {
            "source":      str(self.source_path),
            "rows":        len(df),
            "users":       df["user_id"].nunique(),
            "items":       df["item_id"].nunique(),
            "date_range":  (df["timestamp"].min(), df["timestamp"].max()),
            "event_types": df["event_type"].value_counts().to_dict(),
        }
