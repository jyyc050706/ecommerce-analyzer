"""
RetailRocket 数据源适配器
实现 BaseDataSource，加载 events.csv 并映射为标准 Schema。
"""
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_pipeline.base_source import BaseDataSource


class RetailRocketSource(BaseDataSource):
    """RetailRocket 电商用户行为数据集适配器"""

    @property
    def column_mapping(self) -> dict:
        return {
            "visitorid":  "user_id",
            "itemid":     "item_id",
            "event":      "event_type",
            "timestamp":  "timestamp",
        }

    def load(self) -> pd.DataFrame:
        events_path = self.source_path / "events.csv"

        if not events_path.exists():
            raise FileNotFoundError(f"events.csv 未找到: {events_path}")

        dtypes = {
            "visitorid":     "int64",
            "itemid":        "int64",
            "event":         "category",
            "timestamp":     "int64",
            "transactionid": "Int64",   # 可空整数
        }

        df = pd.read_csv(events_path, dtype=dtypes)
        # timestamp 是 Unix 毫秒时间戳
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        self.df = df
        return df

    def load_item_properties(self) -> pd.DataFrame:
        """按需加载商品属性表（合并 part1 + part2）"""
        p1 = self.source_path / "item_properties_part1.csv"
        p2 = self.source_path / "item_properties_part2.csv"

        dfs = []
        for path in [p1, p2]:
            if path.exists():
                dfs.append(pd.read_csv(
                    path,
                    dtype={"itemid": "int64", "property": "category", "value": "str"},
                ))

        if not dfs:
            raise FileNotFoundError("item_properties 文件未找到")

        merged = pd.concat(dfs, ignore_index=True)
        merged["timestamp"] = pd.to_datetime(merged["timestamp"], unit="ms")
        return merged

    def load_category_tree(self) -> pd.DataFrame:
        """加载商品类目树"""
        path = self.source_path / "category_tree.csv"
        if not path.exists():
            raise FileNotFoundError(f"category_tree.csv 未找到: {path}")
        return pd.read_csv(path, dtype={"categoryid": "int64", "parentid": "Int64"})


# ===== 快速测试入口 =====
if __name__ == "__main__":
    from config import DATA_DIR

    source = RetailRocketSource(DATA_DIR)
    df = source.get_data()
    info = source.info()

    print("=== 数据加载成功 ===")
    print(f"总行数: {info['rows']:,}")
    print(f"用户数: {info['users']:,}")
    print(f"商品数: {info['items']:,}")
    print(f"日期范围: {info['date_range'][0]} ~ {info['date_range'][1]}")
    print(f"事件分布: {info['event_types']}")
    print(f"\n前5行预览:\n{df.head()}")
