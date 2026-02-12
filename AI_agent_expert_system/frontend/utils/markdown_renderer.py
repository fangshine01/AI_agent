"""
Markdown / Mermaid 渲染工具
支援在 Streamlit 中渲染包含 Mermaid 圖表的 Markdown
"""

import re
import streamlit as st


def render_markdown_with_mermaid(content: str):
    """
    渲染包含 Mermaid 的 Markdown 內容

    自動偵測 ```mermaid 區塊並使用 streamlit-mermaid 渲染
    """
    if not content:
        return

    # 分離 Mermaid 和普通 Markdown
    mermaid_pattern = r"```mermaid\n(.*?)\n```"
    matches = list(re.finditer(mermaid_pattern, content, re.DOTALL))

    if not matches:
        # 無 Mermaid，直接顯示
        st.markdown(content)
        return

    # 嘗試匯入 streamlit-mermaid
    try:
        from streamlit_mermaid import st_mermaid

        has_mermaid = True
    except ImportError:
        has_mermaid = False

    # 分段顯示
    last_end = 0
    for match in matches:
        # 顯示 Mermaid 前的 Markdown
        if match.start() > last_end:
            st.markdown(content[last_end : match.start()])

        # 渲染 Mermaid
        mermaid_code = match.group(1)
        if has_mermaid:
            st_mermaid(mermaid_code)
        else:
            # Fallback: 顯示原始程式碼
            st.code(mermaid_code, language="mermaid")

        last_end = match.end()

    # 顯示最後一段 Markdown
    if last_end < len(content):
        st.markdown(content[last_end:])
