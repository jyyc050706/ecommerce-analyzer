"""
多模态图表识别 — 智谱 GLM-4V 提取图表数据 → DeepSeek 分析

调用链：用户上传图片 → vision_call 提取结构化数据 → parse → 结果喂给 DeepSeek 分析
"""

import json
import re
import base64
from pathlib import Path
from typing import Optional
from ai_layer.llm_client import vision_call, chat


CHART_EXTRACT_PROMPT = """请识别这张图表，提取以下信息：

1. 图表类型（柱状图/折线图/饼图/漏斗图/散点图/热力图/其他）
2. 标题
3. X轴/Y轴标签（如有）
4. 所有数据系列名称和对应的数值
5. 是否有异常点或突变
6. 整体趋势描述

以结构化 JSON 格式输出，不要额外解释。格式示例：
{
  "type": "折线图",
  "title": "日交易量趋势",
  "axes": {"x": "日期", "y": "交易数"},
  "series": [{"name": "交易数", "values": [100, 120, 95]}],
  "anomalies": ["2026-06-20 异常飙升至 500"],
  "trend": "整体平稳上升"
}"""


def read_chart(image_path: str) -> dict:
    """读取图表图片，返回结构化数据

    Returns
    -------
    dict
        成功: {"type", "title", "axes", "series", "anomalies", "trend", "raw", "success": True}
        失败: {"error": str, "success": False}
    """
    path = Path(image_path)
    if not path.exists():
        return {"error": f"图片不存在: {image_path}", "success": False}

    with open(path, "rb") as f:
        img_b64 = f"data:image/{path.suffix.lstrip('.')};base64,{base64.b64encode(f.read()).decode()}"

    result_text = vision_call(img_b64, CHART_EXTRACT_PROMPT)

    # 解析 JSON
    structured = _parse_json(result_text)
    if structured:
        structured["raw"] = result_text
        structured["success"] = True
        return structured

    # 解析失败时退回 raw 模式
    return {"raw": result_text, "success": True, "parse_error": True}


def _parse_json(text: str) -> Optional[dict]:
    """从 GLM-4V 返回中提取并校验 JSON"""
    # 尝试直接解析
    try:
        return _validate_schema(json.loads(text))
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 代码块
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return _validate_schema(json.loads(m.group(1).strip()))
        except json.JSONDecodeError:
            pass

    # 尝试提取花括号块
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return _validate_schema(json.loads(m.group(0)))
        except json.JSONDecodeError:
            pass

    return None


def _validate_schema(data: dict) -> dict:
    """Schema 校验 + 兜底填充"""
    result = {
        "type": data.get("type", "未知"),
        "title": data.get("title", ""),
        "axes": data.get("axes", {}),
        "series": data.get("series", []),
        "anomalies": data.get("anomalies", []),
        "trend": data.get("trend", ""),
    }
    return result


def analyze_chart(image_path: str, user_question: str = "") -> str:
    """端到端：识别图表 + DeepSeek 分析 → 返回自然语言分析结果"""
    result = read_chart(image_path)
    if result.get("error"):
        return result["error"]

    chart_data = result.get("raw", "")
    question = user_question or "请分析这张图表，解读数据含义"

    prompt = f"""以下是从图表中提取的结构化数据：

{chart_data}

用户问题：{question}

请基于图表数据分析回答用户问题。"""

    return chat([
        {"role": "system", "content": "你是一个数据分析师，擅长解读图表数据。"},
        {"role": "user", "content": prompt},
    ])
