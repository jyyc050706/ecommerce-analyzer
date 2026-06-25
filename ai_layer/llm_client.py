"""
LLM API 统一封装 — DeepSeek (OpenAI 兼容) + 智谱 GLM-4V (多模态)
"""

from openai import OpenAI
from config import LLM_CONFIG, VISION_CONFIG


_client = None
_vision_client = None


def get_client():
    global _client
    if _client is None:
        if not LLM_CONFIG["api_key"]:
            raise RuntimeError(
                "未设置 DEEPSEEK_API_KEY 环境变量。\n"
                "请在终端执行: set DEEPSEEK_API_KEY=你的API密钥"
            )
        _client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )
    return _client


def get_vision_client():
    global _vision_client
    if _vision_client is None:
        if not VISION_CONFIG["api_key"]:
            raise RuntimeError(
                "未设置 ZHIPU_API_KEY 环境变量。\n"
                "请在终端执行: set ZHIPU_API_KEY=你的API密钥"
            )
        _vision_client = OpenAI(
            api_key=VISION_CONFIG["api_key"],
            base_url=VISION_CONFIG["base_url"],
        )
    return _vision_client


def chat(messages: list[dict], model: str = None, temperature: float = None,
         max_tokens: int = None, reasoning_effort: str = None) -> str:
    """发送对话请求，返回模型回复文本"""
    client = get_client()
    kwargs = dict(
        model=model or LLM_CONFIG["model"],
        messages=messages,
        temperature=temperature if temperature is not None else LLM_CONFIG["temperature"],
        max_tokens=max_tokens or LLM_CONFIG["max_tokens"],
        extra_body={"thinking": {"type": "enabled"}},
    )
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def chat_with_tools(messages: list[dict], tools: list[dict], model: str = None,
                    temperature: float = None, max_tokens: int = None) -> str | dict | None:
    """带工具调用的对话请求。
    返回 str = LLM 直接回答；返回 dict = LLM 请求调用工具，含 arguments/tool_call_message/tool_call_id。"""
    client = get_client()
    kwargs = dict(
        model=model or LLM_CONFIG["model"],
        messages=messages,
        tools=tools,
        temperature=temperature if temperature is not None else LLM_CONFIG["temperature"],
        max_tokens=max_tokens or LLM_CONFIG["max_tokens"],
        extra_body={"thinking": {"type": "enabled"}},
    )
    resp = client.chat.completions.create(**kwargs)
    msg = resp.choices[0].message

    if msg.tool_calls:
        tc = msg.tool_calls[0]
        return {
            "arguments": __import__("json").loads(tc.function.arguments),
            "tool_call_message": {"role": "assistant", "tool_calls": msg.to_dict()["tool_calls"]},
            "tool_call_id": tc.id,
        }
    return msg.content


def chat_stream(messages: list[dict], model: str = None, temperature: float = None,
                max_tokens: int = None, reasoning_effort: str = None):
    """流式对话，逐 token yield"""
    client = get_client()
    kwargs = dict(
        model=model or LLM_CONFIG["model"],
        messages=messages,
        temperature=temperature if temperature is not None else LLM_CONFIG["temperature"],
        max_tokens=max_tokens or LLM_CONFIG["max_tokens"],
        stream=True,
        extra_body={"thinking": {"type": "enabled"}},
    )
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort
    stream = client.chat.completions.create(**kwargs)
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def vision_call(image_base64: str, prompt: str) -> str:
    """多模态识图 — 智谱 GLM-4V，传入 base64 图片 + 文字指令，返回识别结果

    典型用法：chart_reader 调用此方法提取图表数据，然后将结果发给 DeepSeek 做分析。
    """
    client = get_vision_client()
    resp = client.chat.completions.create(
        model=VISION_CONFIG["model"],
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_base64}},
            ],
        }],
        max_tokens=2048,
    )
    return resp.choices[0].message.content
