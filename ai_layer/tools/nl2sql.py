"""
自然语言转 SQL — 将用户问题转为 SQL 查询，在 SQLite 临时库执行
"""

import sqlite3, json
import pandas as pd
from ai_layer.llm_client import chat


N2SQL_SYSTEM = """你是一个 SQL 专家。用户会描述数据分析需求，你需要将其转换为 SQLite SQL 查询。

数据库表 daily_metrics 结构：
- date TEXT PRIMARY KEY           -- 日期 YYYY-MM-DD
- view INTEGER                    -- 浏览独立用户数
- addtocart INTEGER               -- 加购独立用户数
- transaction INTEGER             -- 交易独立用户数
- cvr_view_to_cart REAL           -- 浏览→加购转化率(%)
- cvr_cart_to_tx REAL             -- 加购→交易转化率(%)

要求：
1. 只输出 SQL 语句，不要任何解释或 markdown 标记
2. 使用 SQLite 语法
3. 查询结果命名为 result
4. 如果用户需求无法转换为有效 SQL，输出 NO_SQL"""


def _build_db(daily: pd.DataFrame) -> sqlite3.Connection:
    """将 daily_metrics DataFrame 加载到内存 SQLite"""
    conn = sqlite3.connect(":memory:")
    daily.to_sql("daily_metrics", conn, index=False, if_exists="replace")
    return conn


def nl2sql(question: str, daily: pd.DataFrame) -> dict:
    """将自然语言问题转为 SQL 查询并执行

    返回: {"sql": str, "result": pd.DataFrame | str, "success": bool}
    """
    # 1. LLM 生成 SQL
    messages = [
        {"role": "system", "content": N2SQL_SYSTEM},
        {"role": "user", "content": question},
    ]
    sql = chat(messages, temperature=0).strip()

    # 清理 markdown 标记
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1]
        sql = sql.rsplit("\n```", 1)[0]
    sql = sql.strip()

    if sql.upper() == "NO_SQL" or not sql:
        return {"sql": "", "result": "无法将问题转换为 SQL 查询", "success": False}

    # 2. 执行
    try:
        conn = _build_db(daily)
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description] if cursor.description else []

        if not cols:
            conn.close()
            return {"sql": sql, "result": "查询无返回列", "success": False}

        result = pd.DataFrame(rows, columns=cols)
        conn.close()
        return {"sql": sql, "result": result, "success": True}

    except Exception as e:
        return {"sql": sql, "result": f"SQL 执行出错: {str(e)}", "success": False}
