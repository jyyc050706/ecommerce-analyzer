"""
Agent 调度层 — 混合模式：预计算摘要 + Code Interpreter
- 摘要覆盖的问题秒出，其他问题 LLM 用 ```python 代码块输出查询代码
- Agent 解析代码块 → 执行 → 反馈结果 → LLM 继续回答
"""

import re
import streamlit as st
from ai_layer.llm_client import chat
from ai_layer.prompts import build_context

MAX_STEPS = 3


def run(user_question: str, max_steps: int = MAX_STEPS) -> str:
    """混合模式：摘要优先 + 代码块解析兜底。"""
    system, preloaded = _get_context()

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_question},
    ]

    for step in range(max_steps):
        response = chat(messages, temperature=0.1)

        code = _extract_python_block(response)
        if not code:
            return response  # 直接回答

        # 执行代码，反馈结果
        result = _execute_python(code, preloaded)
        messages.append({"role": "assistant", "content": response})
        messages.append({
            "role": "user",
            "content": f"代码执行结果:\n{result}",
        })

    return chat(messages, temperature=0.1)


def _extract_python_block(text: str) -> str | None:
    """从 LLM 回复中提取第一个 ```python 代码块的内容。"""
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else None


def _get_context() -> tuple[str, dict]:
    """初始化上下文，整个会话只构建一次。"""
    if "agent_context" not in st.session_state:
        st.session_state.agent_context = build_context()
    return st.session_state.agent_context


def _execute_python(code: str, data: dict) -> str:
    """在数据环境中执行 Python 代码。"""
    from ai_layer.tools.chart_reader import read_chart, analyze_chart
    namespace = {
        "df": data["df"],
        "daily": data["daily"],
        "profile": data["profile"],
        "rfm": data["rfm"],
        "pd": __import__("pandas"),
        "np": __import__("numpy"),
        "read_chart": read_chart,
        "analyze_chart": analyze_chart,
    }
    try:
        exec(code, namespace)
        result = namespace.get("result", "(no result variable)")
        return str(result)
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
