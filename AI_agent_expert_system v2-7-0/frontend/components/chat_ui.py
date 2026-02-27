"""
Chat UI 組件 - 可重用的聊天介面組件
"""

import streamlit as st
from typing import Dict, List, Optional


def render_search_results_cards(search_results: List[Dict]):
    """
    卡片式搜尋結果展示

    Args:
        search_results: 搜尋結果列表
    """
    if not search_results:
        return

    st.markdown("### 📚 參考資料")

    type_icons = {
        "Troubleshooting": "🔧",
        "Procedure": "📋",
        "Knowledge": "📚",
        "Training": "🎓",
    }

    for doc in search_results[:3]:
        with st.container():
            col_icon, col_content, col_score = st.columns([1, 8, 2])

            with col_icon:
                icon = type_icons.get(doc.get("file_type", ""), "📄")
                st.markdown(f"### {icon}")

            with col_content:
                st.markdown(f"**{doc.get('file_name', '未知檔案')}**")
                st.caption(
                    f"類型: {doc.get('file_type', 'N/A')} | "
                    f"匹配度: {doc.get('score', 0):.2%}"
                )
                preview = doc.get("preview", "")[:150]
                if preview:
                    st.text(f"{preview}...")

            with col_score:
                score = doc.get("score", 0)
                st.metric("相關度", f"{score:.0%}")
                st.progress(min(score, 1.0))

            st.markdown("---")


def render_troubleshooting_metadata(doc: Dict):
    """渲染 Troubleshooting 元數據"""
    meta_cols = st.columns(4)
    with meta_cols[0]:
        st.metric("產品型號", doc.get("product_model") or "未指定")
    with meta_cols[1]:
        st.metric("缺陷代碼", doc.get("defect_code") or "未指定")
    with meta_cols[2]:
        st.metric("檢出站點", doc.get("station") or "未指定")
    with meta_cols[3]:
        st.metric("Yield Loss", doc.get("yield_loss") or "N/A")


def render_8d_report(chunks: List[Dict]):
    """渲染 8D 報告內容"""
    field_order = [
        "Problem issue & loss",
        "Problem description",
        "Analysis root cause",
        "Containment action",
        "Corrective action",
        "Preventive action",
    ]

    chunk_map = {c.get("title"): c.get("content") for c in chunks}

    for field in field_order:
        chunk_content = chunk_map.get(field)
        if chunk_content:
            st.markdown(f"## 📌 {field}")
            st.markdown(chunk_content)
            st.markdown("---")

    # 顯示其他非標準欄位
    for chunk in chunks:
        if chunk.get("title") not in field_order:
            st.markdown(f"## 📄 {chunk.get('title')}")
            st.markdown(chunk.get("content", ""))
            st.markdown("---")
