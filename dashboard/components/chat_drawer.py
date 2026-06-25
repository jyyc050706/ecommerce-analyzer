"""
右侧可收起 AI 分析助手 — 全局共享，始终可用
"""

import os, tempfile, streamlit as st
from config import LLM_CONFIG
from dashboard.components.db import init as db_init, save_chat_message, load_chat_history

PAGE_CONTEXT = {
    "overview": "当前页面是「概览」，展示KPI卡片、日趋势、事件分布。",
    "user":     "当前页面是「用户分析」，展示用户画像分布和RFM分层。",
    "funnel":   "当前页面是「转化漏斗」，展示各环节转化率和对比。",
    "anomaly":  "当前页面是「异常监控」，展示多指标异常检测结果。",
    "forecast": "当前页面是「时序预测」，展示Prophet预测指标、30天交易量预测图和明细表。",
}

SUGGESTIONS = [
    "整体转化率怎么样？",
    "最近7天浏览UV有什么变化？",
    "用户分层情况如何？",
    "漏斗哪个环节流失最严重？",
]

RIGHT_PANEL_CSS = """
<style>
.right-chat-scroll {
    max-height: calc(100vh - 120px);
    overflow-y: auto;
    padding-right: 4px;
}
.right-chat-scroll::-webkit-scrollbar {
    width: 6px;
}
.right-chat-scroll::-webkit-scrollbar-thumb {
    background: #c0c0c0;
    border-radius: 3px;
}
.right-chat-scroll::-webkit-scrollbar-track {
    background: transparent;
}
.right-chat-panel h3 {
    font-size: 15px;
    margin-top: 0;
    margin-bottom: 8px;
    color: #333;
}
.thinking-dots span {
    animation: dot-blink 1.4s infinite both;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-blink {
    0%, 80%, 100% { opacity: 0; }
    40% { opacity: 1; }
}
</style>
"""


def render_chat_drawer(page: str = ""):
    """在右侧面板渲染 AI 聊天。由 app.py 调用。"""
    st.markdown(RIGHT_PANEL_CSS, unsafe_allow_html=True)
    st.markdown("### AI 分析助手")

    ctx = PAGE_CONTEXT.get(page, "")

    if "chat_messages" not in st.session_state:
        db_init()
        st.session_state.chat_messages = load_chat_history()

    # 聊天内容区域 — 独立滚轮
    with st.container(height=500, border=False):
        visible = st.session_state.chat_messages[-20:]
        if len(st.session_state.chat_messages) > 20:
            st.caption(f"（共 {len(st.session_state.chat_messages)} 条，显示最近 20 条）")
        for msg in visible:
            with st.chat_message(msg["role"]):
                if msg["content"] == "…":
                    st.markdown('<span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span>', unsafe_allow_html=True)
                else:
                    st.markdown(msg["content"])

        # 快捷问题
        if not st.session_state.chat_messages:
            for i, s in enumerate(SUGGESTIONS):
                if st.button(s, key=f"sug_right_{i}", use_container_width=True):
                    st.session_state.chat_messages.append({"role": "user", "content": s})
                    save_chat_message("user", s)
                    st.session_state.chat_messages.append({"role": "assistant", "content": "…"})
                    st.session_state.pending_question = s
                    st.session_state.pending_context = ctx
                    st.rerun()

    # 附件暂存（图片路径列表）
    if "pending_attachments" not in st.session_state:
        st.session_state.pending_attachments = []

    # 输入框
    user_input = st.chat_input("问问数据……", key="right_chat_input")

    # 图片选择按钮（在输入框下方）
    if st.button("选择图片", key="select_image_btn", help="上传图片 / 点击上传区后 Ctrl+V 粘贴截图"):
        st.session_state.show_img_upload = not st.session_state.get("show_img_upload", False)

    if st.session_state.get("show_img_upload"):
        uploaded = st.file_uploader(
            "点击此处 → Ctrl+V 粘贴截图",
            type=["png", "jpg", "jpeg"],
            key="img_uploader",
            label_visibility="visible",
        )
        if uploaded is not None:
            os.makedirs("data/temp", exist_ok=True)
            import time
            ext = uploaded.name.rsplit(".", 1)[-1] if "." in uploaded.name else "png"
            safe_name = uploaded.name.rsplit(".", 1)[0].replace(" ", "_")[:30] if "." in uploaded.name else "clipboard"
            img_path = os.path.abspath(f"data/temp/chat_upload_{safe_name}_{int(time.time())}.{ext}")
            with open(img_path, "wb") as f:
                f.write(uploaded.getbuffer())
            st.session_state.pending_attachments.append(img_path)
            # 清空 uploader 状态避免 rerun 后反复触发
            if "img_uploader" in st.session_state:
                del st.session_state.img_uploader
            st.rerun()

    if user_input:
        import sys
        # 合并附件路径
        if st.session_state.pending_attachments:
            paths = "\n".join(f"图表图片路径: {p}" for p in st.session_state.pending_attachments)
            full_q = f"{user_input}\n{paths}"
            st.session_state.pending_attachments.clear()
        else:
            full_q = user_input

        print(f"[chat_drawer] 用户输入: full_q={full_q[:100]}", file=sys.__stderr__, flush=True)
        st.session_state.chat_messages.append({"role": "user", "content": full_q})
        save_chat_message("user", full_q)
        st.session_state.chat_messages.append({"role": "assistant", "content": "…"})
        st.session_state.pending_question = full_q
        st.session_state.pending_context = ctx
        print(f"[chat_drawer] pending_question 已设置, ctx={ctx[:30] if ctx else ''}", file=sys.__stderr__, flush=True)
        st.rerun()

    # 处理待回复
    if st.session_state.get("pending_question"):
        q = st.session_state.pop("pending_question")
        ctx_q = st.session_state.pop("pending_context")
        _reply(q, ctx_q)
        st.rerun()


def _reply(user_input: str, page_context: str = ""):
    """调用 Agent 生成回复，替换占位消息，并持久化"""
    import sys
    print(f"[chat_drawer] _reply 开始, user_input={user_input[:80]}...", file=sys.__stderr__, flush=True)

    if not LLM_CONFIG["api_key"]:
        reply = "未检测到 DeepSeek API Key。请在项目 `.env` 文件中配置 `DEEPSEEK_API_KEY`。"
    else:
        try:
            from ai_layer.agent import run
            # 有图片时不要注入页面上下文，专注图片内容
            has_image = "图表图片路径:" in user_input
            question = f"{page_context}\n用户问题：{user_input}" if (page_context and not has_image) else user_input
            print(f"[chat_drawer] 调用 agent.run, question_len={len(question)}", file=sys.__stderr__, flush=True)
            reply = run(question)
            print(f"[chat_drawer] agent.run 返回, reply_len={len(reply)}", file=sys.__stderr__, flush=True)

            # 清理本次对话用到的临时图片文件
            import os
            for line in user_input.splitlines():
                if line.startswith("图表图片路径:"):
                    path = line.split(":", 1)[1].strip()
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                            print(f"[chat_drawer] 已清理临时图片: {path}", file=sys.__stderr__, flush=True)
                    except Exception:
                        pass

        except Exception as e:
            import traceback
            reply = f"分析出错：{str(e)}"
            print(f"[chat_drawer] 异常: {traceback.format_exc()}", file=sys.__stderr__, flush=True)

    # 替换最后一条 "…" 占位消息
    st.session_state.chat_messages[-1]["content"] = reply
    save_chat_message("assistant", reply)
    print(f"[chat_drawer] 回复已写入 chat_messages[-1], 内容前80字: {reply[:80]}", file=sys.__stderr__, flush=True)
