"""
SQLite 持久化模块 — 将预计算结果写入本地 DB，看板按日期/用户/商品维度查询
"""

import sqlite3, json, os
import pandas as pd
from datetime import datetime
from config import DATA_DIR


DB_PATH = os.path.join(os.path.dirname(__file__), "dashboard.db")


def init():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS daily_metrics (
        date TEXT PRIMARY KEY,
        view_uv INTEGER,
        addtocart_uv INTEGER,
        transaction_uv INTEGER,
        cvr_view_to_cart REAL,
        cvr_cart_to_tx REAL,
        anomaly_flags TEXT
    );
    CREATE TABLE IF NOT EXISTS user_segments (
        segment TEXT,
        user_count INTEGER,
        pct REAL,
        updated_at TEXT,
        PRIMARY KEY (segment)
    );
    CREATE TABLE IF NOT EXISTS rfm_thresholds (
        dimension TEXT PRIMARY KEY,
        score_5 REAL,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)
    conn.commit()
    conn.close()


def upsert_daily(df: pd.DataFrame):
    """写入/更新每日指标"""
    conn = sqlite3.connect(DB_PATH)
    for _, row in df.iterrows():
        date_str = str(row.get("date", ""))
        flags = json.dumps({
            "view_uv_3sigma": int(row.get("view_uv_3sigma", 0)),
            "addtocart_uv_3sigma": int(row.get("addtocart_uv_3sigma", 0)),
            "transaction_uv_3sigma": int(row.get("transaction_uv_3sigma", 0)),
        })
        conn.execute("""
            INSERT OR REPLACE INTO daily_metrics (date, view_uv, addtocart_uv, transaction_uv, cvr_view_to_cart, cvr_cart_to_tx, anomaly_flags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            date_str,
            int(row.get("view_uv", 0)),
            int(row.get("addtocart_uv", 0)),
            int(row.get("transaction_uv", 0)),
            float(row.get("cvr_view_to_cart", 0)),
            float(row.get("cvr_cart_to_tx", 0)),
            flags,
        ))
    conn.commit()
    conn.close()


def upsert_segments(segments: dict):
    """写入用户分层"""
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    for seg, count in segments.items():
        conn.execute("""
            INSERT OR REPLACE INTO user_segments (segment, user_count, pct, updated_at)
            VALUES (?, ?, ?, ?)
        """, (seg, count, 0.0, now))
    conn.commit()
    conn.close()


def upsert_thresholds(thresholds: dict):
    """写入 RFM 阈值"""
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    for dim, info in thresholds.items():
        conn.execute("""
            INSERT OR REPLACE INTO rfm_thresholds (dimension, score_5, updated_at)
            VALUES (?, ?, ?)
        """, (dim, info.get("5", 0), now))
    conn.commit()
    conn.close()


def save_chat_message(role: str, content: str):
    """持久化单条聊天消息"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO chat_history (role, content) VALUES (?, ?)",
        (role, content),
    )
    conn.commit()
    conn.close()


def load_chat_history(limit: int = 50) -> list[dict]:
    """加载最近 N 条聊天记录"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT role, content FROM chat_history ORDER BY id ASC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]
