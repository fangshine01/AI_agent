"""
AI Expert System - Chat UI (使用者問答介面)
Port: 8502

功能：
- 專家問答（整合 v2.0 搜尋）
- 分類範圍選擇
- Session Token 統計
"""

import pandas as pd
import streamlit as st
import time
import os
import logging
from typing import List, Dict
from datetime import datetime
from core import database, ai_core
from core import search  # v3.0 重構後的 search 模組
import config

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 頁面設定
st.set_page_config(
    page_title="AI Expert System - 專家問答",
    page_icon="💬",
    layout="wide"
)

# 初始化 Session State
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'session_tokens' not in st.session_state:
    st.session_state.session_tokens = 0

# 側邊欄導航
with st.sidebar:
    st.title("導航")
    page = st.radio("選擇頁面", ["💬 專家問答", "📚 知識庫清單"])
    st.markdown("---")

# 標題
if page == "💬 專家問答":
    st.title("💬 AI Expert System - 專家問答")
    st.caption("由 v1.5.0 通用查詢引擎驅動 🚀")
elif page == "📚 知識庫清單":
    st.title("📚 知識庫清單")
    st.caption("檢視所有已訓練的文件")

# 側邊欄:API 設定與搜尋設定 (只在問答頁面顯示或是共用? API Key 應該共用)
with st.sidebar:
    st.header("🔑 API 設定")
    # ... (API Key logic remains same) ...
    # 使用 session_state 儲存 API 設定
    if 'user_api_key' not in st.session_state:
        st.session_state.user_api_key = ""
    if 'user_base_url' not in st.session_state:
        st.session_state.user_base_url = "http://innoai.cminl.oa/agency/proxy/openai/platform"
    
    user_api_key = st.text_input(
        "API Key",
        value=st.session_state.user_api_key,
        type="password",
        help="請輸入您的 API Key"
    )
    
    user_base_url = st.text_input(
        "Base URL",
        value=st.session_state.user_base_url,
        help="API 端點 URL"
    )
    
    # 儲存到 session_state
    st.session_state.user_api_key = user_api_key
    st.session_state.user_base_url = user_base_url
    
    # 顯示狀態
    if user_api_key:
        st.success("✅ API Key 已設定")
    else:
        st.warning("⚠️ 請輸入 API Key")
    
    st.markdown("---")
    
    if page == "💬 專家問答":
        st.header("⚙️ 搜尋設定")
        
        # v4.1 搜尋模組: 類型化模板
        st.markdown("### 🎯 查詢類型與模板")
        
        display_options = {
            "general": "🔍 一般搜尋 (General)",
            "troubleshooting": "🔧 異常解析 (Troubleshooting)",
            "procedure": "📋 SOP、手順 (Procedure)",
            "knowledge": "📚 技術規格/參考資料 (Reference)",
            "training": "🎓 原理/培訓教材 (Training)"
        }
        
        query_type = st.radio(
            "選擇查詢情境",
            options=["general", "troubleshooting", "procedure", "knowledge", "training"],
            format_func=lambda x: display_options.get(x, x),
            help="選擇合適的類型以啟用專屬搜尋模板"
        )

        # 分類過濾 (僅在一般模式顯示)
        selected_types = []
        if query_type == "general":
            selected_types = st.multiselect(
                "搜尋範圍",
                options=['knowledge', 'training', 'procedure', 'troubleshooting'],
                default=[],
                format_func=lambda x: {
                    'knowledge': '📚 知識庫',
                    'training': '🎓 教育訓練',
                    'procedure': '📋 日常手順',
                    'troubleshooting': '🔧 異常解析'
                }[x],
                help="限定搜尋的文件類型，留空表示搜尋所有類型"
            )
        
        # 動態顯示欄位
        search_filters = {}
        
        if query_type == "troubleshooting":
            st.caption("針對特定產品異常尋找解決方案")
            col1, col2 = st.columns(2)
            with col1:
                prod = st.text_input("產品型號", placeholder="e.g. N706", help="輸入產品型號可精準鎖定")
            with col2:
                station = st.text_input("機台/站點", placeholder="e.g. Oven", help="選填")
            
            if prod: search_filters['product'] = prod
            if station: search_filters['station'] = station
            # 強制限定文件類型
            selected_types = ['troubleshooting']
            
        elif query_type == "procedure":
            st.caption("查詢標準操作步驟 (SOP)")
            station = st.text_input("站點/製程", placeholder="e.g. 黃光 / 貼合", help="輸入站點名稱")
            if station: search_filters['station'] = station
            # 強制限定文件類型
            selected_types = ['procedure']
            
        elif query_type == "knowledge":
            st.caption("查詢規格參數、Datasheet 或錯誤代碼")
            topic = st.text_input("主題/關鍵字", placeholder="e.g. N706 電壓上限")
            if topic: search_filters['topic'] = topic
            search_filters['doc_type'] = 'Knowledge'
            # 強制限定文件類型
            selected_types = ['knowledge']

        elif query_type == "training":
            st.caption("查詢技術原理、教育訓練或演算法說明")
            topic = st.text_input("主題/關鍵字", placeholder="e.g. 曝光機原理")
            if topic: search_filters['topic'] = topic
            search_filters['doc_type'] = 'Training'
            # 強制限定文件類型
            selected_types = ['training']
            
        # 搜尋限制
        search_limit = st.slider("搜尋結果數", 1, 20, 5)
        
        # v4.0 說明: 自動智慧選擇策略
        st.info("🤖 v1.5.0 會自動分析查詢意圖並選擇最佳搜尋策略")
        
        # v3.0 新增: 問答模型選擇
        st.markdown("**🤖 問答模型**")
        chat_model = st.selectbox(
            "選擇推理模型",
            options=["gpt-4o-mini", "gpt-4o", "gemini-2.0-flash-exp"],
            format_func=lambda x: f"{x} {config.MODEL_COST_LABELS.get(x, '')}"
        )
        
        # 模糊搜尋設定
        enable_fuzzy = st.checkbox("啟用模糊搜尋", value=True)
        
        # 將過濾條件存入 session_state 供主流程使用
        st.session_state.current_query_type = query_type
        st.session_state.current_filters = search_filters
        # 注意: 我們也需要將 selected_types 存入 session_state，因為這可能會被後續邏輯使用
        st.session_state.current_selected_types = selected_types
        
        st.markdown("---")
        
        st.header("📊 Session 狀態")
        st.metric("本次對話 Token", f"{st.session_state.session_tokens:,}")
        
        if st.button("清空對話記錄"):
            st.session_state.messages = []
            st.session_state.session_tokens = 0
            st.rerun()
        
        st.markdown("---")
        st.caption("提示：使用模糊搜尋可以容忍拼寫錯誤")

# Main Logic Switching
if page == "💬 專家問答":
    # === Chat Interface ===
    st.markdown("### 對話記錄")

    # 顯示歷史訊息
    for index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # 顯示 Token 使用（如果是 assistant 訊息）
            if message["role"] == "assistant":
                if "tokens" in message:
                    st.caption(f"💡 本次使用: {message['tokens']} tokens")
                
                # 顯示下載按鈕 (如果有的話)
                if "doc_data" in message:
                    st.download_button(
                        label=f"📥 下載 {message.get('doc_name', 'SOP')} (Markdown)",
                        data=message["doc_data"],
                        file_name=f"{message.get('doc_name', 'document')}.md",
                        mime="text/markdown",
                        key=f"dl_{index}"  # 使用 index 確保 key 唯一
                    )

    # 使用者輸入
    if prompt := st.chat_input("請輸入您的問題..."):
        # 檢查 API Key
        if not user_api_key:
            st.error("❌ 請先在左側設定 API Key 才能進行對話")
            st.stop()

        # 顯示使用者訊息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # AI 回應
        with st.chat_message("assistant"):
            # 檢查是否為列表查詢
            list_query_keywords = ['有哪些', '列出', '目錄', '清單', '全部', '所有文件', '知識庫']
            is_list_query = any(keyword in prompt for keyword in list_query_keywords)
            
            if is_list_query:
                # 直接返回知識庫概覽
                with st.spinner("正在整理知識庫資訊..."):
                    overview = database.get_knowledge_overview()
                    
                    # 生成知識庫概覽文字
                    response_parts = ["📚 **知識庫概覽**\n"]
                    response_parts.append(f"目前共有 **{overview['total']}** 個文件\n")
                    
                    if overview['by_type']:
                        response_parts.append("\n**文件類型統計:**")
                        type_names = {
                            'knowledge': '知識庫',
                            'training': '教育訓練',
                            'procedure': '日常手順',
                            'troubleshooting': '異常解析'
                        }
                        for ftype, count in overview['by_type'].items():
                            response_parts.append(f"- {type_names.get(ftype, ftype)}: {count} 個")
                    
                    if overview['recent_files']:
                        response_parts.append("\n\n**最近上傳的文件:**")
                        for doc in overview['recent_files'][:5]:
                            response_parts.append(f"- {doc['file_name']} ({type_names.get(doc['file_type'], doc['file_type'])})")
                    
                    if overview['all_keywords']:
                        response_parts.append(f"\n\n**熱門關鍵字:** {', '.join(overview['all_keywords'][:20])}")
                    
                    response_parts.append("\n\n💡 **使用建議:** 您可以輸入上述關鍵字或文件名來查詢具體內容!")
                    
                    response = "\n".join(response_parts)
                    usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 100}
                    
                    st.markdown(response)
                    st.caption("💡 本次使用: 100 tokens (列表查詢)")
                    
            else:
                # 正常搜尋流程 (v4.0 - 使用通用查詢引擎)
                with st.spinner("正在搜尋相關資料..."):
                    # 準備 API 金鑰與 URL (優先使用側邊欄輸入,否則使用系統預設)
                    api_key_used = user_api_key if user_api_key else None
                    base_url_used = user_base_url if user_base_url else None
                    
                    # 取得當前設定的類型與過濾器
                    current_query_type = st.session_state.get('current_query_type', 'general')
                    current_filters = st.session_state.get('current_filters', {})
                    
                    # 使用 v4.1 通用查詢引擎 (支援類型化搜尋)
                    search_result = search.universal_search(
                        query=prompt,
                        top_k=search_limit,
                        doc_type=selected_types[0] if selected_types else None,
                        auto_strategy=True,  # 自動選擇策略
                        api_key=api_key_used,
                        base_url=base_url_used,
                        query_type=current_query_type,
                        filters=current_filters
                    )
                    
                    # 顯示查詢元資訊
                    st.info(f"🎯 查詢意圖: **{search_result['intent']}** | 🔍 搜尋策略: **{search_result['strategy']}** | ⏱️ 搜尋時間: **{search_result['meta']['search_time']:.2f}秒** | 💯 信心度: **{search_result['meta']['confidence']:.0%}**")
                    
                    # 轉換為統一格式
                    search_results = search_result['results']
                    
                    # 2. 檢查是否有搜尋結果
                    if not search_results:
                        # 無結果時的後備機制
                        overview = database.get_knowledge_overview()
                        
                        response_parts = ["抱歉,我找不到與您問題直接相關的資料。\n"]
                        response_parts.append("**知識庫概覽:**")
                        response_parts.append(f"- 目前共有 {overview['total']} 個文件")
                        
                        if overview['all_keywords']:
                            response_parts.append(f"- 可查詢的關鍵字: {', '.join(overview['all_keywords'][:15])}")
                        
                        response_parts.append("\n💡 **建議:**")
                        response_parts.append("1. 嘗試使用更簡單的關鍵字")
                        response_parts.append("2. 輸入「有哪些」查看完整文件目錄")
                        response_parts.append("3. 參考上述關鍵字重新提問")
                        
                        response = "\n".join(response_parts)
                        usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 50}
                        
                        st.markdown(response)
                        st.caption("💡 本次使用: 50 tokens (無結果)")
                        
                    else:
                        # Check for Direct Retrieval (Skip LLM)
                        if search_result.get('meta', {}).get('skip_llm', False) or \
                           (search_results and search_results[0].get('file_type') == 'Troubleshooting'):
                             
                            # 直接檢索模式 (針對 SOP/Procedure/Knowledge/Training/Troubleshooting)
                            doc = search_results[0]
                            file_type = doc.get('file_type')
                            
                            doc_type_label = {
                                'Procedure': 'SOP',
                                'Training': '教材',
                                'Knowledge': '技術文件',
                                'Troubleshooting': '8D報告'
                            }.get(file_type, '文件')
                            
                            st.success(f"✅ 已找到精準匹配的 {doc_type_label}: **{doc['file_name']}**")
                            
                            # 初始化 content 變數 (避免作用域問題)
                            content = ""
                            
                            # Troubleshooting 專用顯示邏輯 (8D 欄位)
                            if file_type == 'Troubleshooting':
                                # 顯示 8D 元數據 (Product, Defect, etc.) - 如果有的話
                                meta_cols = st.columns(4)
                                with meta_cols[0]:
                                    st.metric("產品型號", doc.get('product_model') or "未指定")
                                with meta_cols[1]:
                                    st.metric("缺陷代碼", doc.get('defect_code') or "未指定")
                                with meta_cols[2]:
                                    st.metric("檢出站點", doc.get('station') or "未指定")
                                with meta_cols[3]:
                                    loss = doc.get('yield_loss')
                                    st.metric("Yield Loss", loss if loss else "N/A")
                                
                                st.markdown("### 📋 8D 報告內容")
                                
                                # 除錯日誌
                                logger.info(f"[8D 直讀] 檔案: {doc.get('file_name')}")
                                logger.info(f"  - doc keys: {list(doc.keys())}")
                                logger.info(f"  - chunks 存在: {'chunks' in doc}")
                                logger.info(f"  - chunks 數量: {len(doc.get('chunks', []))}")
                                logger.info(f"  - raw_content 長度: {len(doc.get('raw_content', ''))}")
                                logger.info(f"  - doc_id: {doc.get('doc_id')}")
                                
                                # 建立 Markdown 格式的完整內容 (用於下載)
                                content_parts = [f"# {doc['file_name']}\n"]
                                content_parts.append("## 基本資訊\n")
                                content_parts.append(f"- **產品型號**: {doc.get('product_model') or '未指定'}")
                                content_parts.append(f"- **缺陷代碼**: {doc.get('defect_code') or '未指定'}")
                                content_parts.append(f"- **檢出站點**: {doc.get('station') or '未指定'}")
                                content_parts.append(f"- **Yield Loss**: {doc.get('yield_loss') or 'N/A'}\n")
                                
                                # v5.0: 優先使用合併後的 raw_content (單一 chunk)
                                chunks = doc.get('chunks', [])
                                
                                # 如果有 raw_content 且是完整的 markdown, 直接顯示
                                raw_content = doc.get('raw_content', '')
                                if raw_content and ('## Problem' in raw_content or '## Analysis' in raw_content or '## Containment' in raw_content):
                                    st.markdown(raw_content)
                                    content = raw_content
                                elif len(chunks) == 1 and len(chunks[0].get('content', '')) > 100:
                                    # v5.0 合併格式: 單一 chunk 包含完整報告
                                    chunk_content = chunks[0].get('content', '')
                                    st.markdown(chunk_content)
                                    content = chunk_content
                                else:
                                    # 舊版格式: 多個 field chunks, 或從 DB 重新取得
                                    if len(chunks) < 6 and doc.get('doc_id'):
                                        logger.warning(f"  ⚠️ 只找到 {len(chunks)} 個 chunks，從資料庫取得完整資料")
                                        try:
                                            from core.database.vector_ops import get_chunks_by_doc_id
                                            db_chunks = get_chunks_by_doc_id(doc['doc_id'])
                                            logger.info(f"  ✓ 從資料庫取得 {len(db_chunks)} 個 chunks")
                                            
                                            chunks = []
                                            for chunk in db_chunks:
                                                chunks.append({
                                                    'chunk_id': chunk.get('id'),
                                                    'title': chunk.get('source_title', '未命名'),
                                                    'content': chunk.get('text_content', chunk.get('content', '')),
                                                    'similarity': 1.0
                                                })
                                        except Exception as e:
                                            logger.error(f"  ✗ 從資料庫取得 chunks 失敗: {e}")
                                    
                                    # 顯示 chunks 內容
                                    if chunks and len(chunks) > 0:
                                        # 定義 8D 欄位順序
                                        field_order = [
                                            "Problem issue & loss", "Problem description", "Analysis root cause",
                                            "Containment action", "Corrective action", "Preventive action"
                                        ]
                                        
                                        chunk_map = {c.get('title'): c.get('content') for c in chunks}
                                        
                                        for field in field_order:
                                            chunk_content = chunk_map.get(field)
                                            if chunk_content:
                                                with st.expander(f"📌 {field}", expanded=True):
                                                    st.markdown(chunk_content)
                                                content_parts.append(f"## {field}\n")
                                                content_parts.append(f"{chunk_content}\n")
                                        
                                        # 顯示其他非標準欄位的 chunks
                                        for chunk in chunks:
                                            if chunk.get('title') not in field_order:
                                                chunk_title = chunk.get('title')
                                                chunk_content = chunk.get('content')
                                                if chunk_content:
                                                    with st.expander(f"📄 {chunk_title}"):
                                                        st.markdown(chunk_content)
                                                    content_parts.append(f"## {chunk_title}\n")
                                                    content_parts.append(f"{chunk_content}\n")
                                        
                                        content = "\n".join(content_parts)
                                    else:
                                        st.warning("⚠️ 此 8D 報告無內容片段")
                                        content = ""
                                     
                            else:
                                # 其他類型 (SOP, etc.) 使用原有的直讀顯示
                                content = doc.get('raw_content', doc.get('content', ''))
                            
                                # 除錯日誌
                                logger.info(f"[直讀] 檔案: {doc.get('file_name')} ({file_type})")
                                
                                # Fallback: 若內容仍為空, 嘗試從 DB 讀取
                                if not content and doc.get('chunk_id'):
                                    try:
                                        from core.database.vector_ops import get_chunk_content
                                        content = get_chunk_content(doc['chunk_id'])
                                        if content: 
                                            doc['content'] = content 
                                            logger.info(f"  ✓ 從 DB 補回內容 (長度: {len(content)})")
                                    except Exception as e:
                                        logger.error(f"  ✗ 讀取失敗: {e}")
                                
                                if not content:
                                    st.warning("⚠️ 無法讀取文件內容")
                                else:
                                    st.markdown(content)
                            
                            # 下載按鈕 (通用)
                            if content:
                                st.download_button(
                                    label=f"📥 下載 {doc_type_label} (Markdown)",
                                    data=content,
                                    file_name=f"{doc['file_name']}.md",
                                    mime="text/markdown"
                                )
                            
                            # 顯示來源
                            with st.expander(f"📚 來源文件: {doc['file_name']}"):
                                st.write(f"**類型**: {doc['file_type']}")
                                st.write(f"**匹配度**: {doc.get('score', 0):.2f}")
                                
                            # 記錄 (Zero Token)
                            st.caption("💡 本次使用: 0 tokens (直接檢索)")
                            
                            # Store in history (不需要 rerun，內容已經顯示在上方)
                            # 注意：不要呼叫 st.rerun()，否則會清空剛才顯示的內容
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"**[{doc_type_label} 直讀]** {doc['file_name']}",
                                "tokens": 0,
                                "doc_type": file_type,
                                "doc_data": content,
                                "doc_name": doc['file_name'],
                                "doc_metadata": {
                                    "product_model": doc.get('product_model'),
                                    "defect_code": doc.get('defect_code'),
                                    "station": doc.get('station'),
                                    "yield_loss": doc.get('yield_loss')
                                } if file_type == 'Troubleshooting' else None,
                                "chunks": doc.get('chunks', []) if file_type == 'Troubleshooting' else None
                            })
                        
                        # 新增:單一文件摘要模式 (非交叉查詢且有摘要)
                        elif not search_result.get('meta', {}).get('cross_query', False):
                            # 單一文件查詢:檢查是否有摘要
                            doc = search_results[0]
                            
                            # 檢查是否有摘要資料
                            has_summary = doc.get('summary') or doc.get('key_points')
                            
                            if has_summary:
                                # 有摘要:直接顯示,不調用 GPT
                                doc_type_label = {
                                    'Procedure': 'SOP',
                                    'Training': '教材',
                                    'Knowledge': '技術文件',
                                    'Troubleshooting': '8D報告'
                                }.get(doc.get('file_type'), '文件')
                                
                                st.success(f"✅ 已找到文件: **{doc['file_name']}** ({doc_type_label})")
                                
                                # 顯示摘要
                                if doc.get('summary'):
                                    st.markdown("### 📝 文件摘要")
                                    st.markdown(doc['summary'])
                                
                                # 顯示重點
                                if doc.get('key_points'):
                                    st.markdown("### 🎯 重點摘要")
                                    st.markdown(doc['key_points'])
                                
                                # 顯示相關內容片段
                                if doc.get('chunks'):
                                    with st.expander("📄 相關內容片段"):
                                        for idx, chunk in enumerate(doc['chunks'], 1):
                                            chunk_title = chunk.get('title', f'片段 {idx}')
                                            chunk_content = chunk.get('content', '')
                                            chunk_similarity = chunk.get('similarity', 0)
                                            
                                            st.markdown(f"**{chunk_title}** (相似度: {chunk_similarity:.2%})")
                                            st.markdown(chunk_content)
                                            if idx < len(doc['chunks']):
                                                st.markdown("---")
                                
                                # 顯示來源資訊
                                with st.expander(f"📚 來源文件資訊"):
                                    st.write(f"**檔案名稱**: {doc['file_name']}")
                                    st.write(f"**文件類型**: {doc['file_type']}")
                                    st.write(f"**平均相似度**: {doc.get('avg_similarity', 0):.2%}")
                                    st.write(f"**內容片段數**: {doc.get('chunk_count', 0)} / {doc.get('total_chunks', 0)}")
                                
                                # 記錄 (Zero Token)
                                st.caption("💡 本次使用: 0 tokens (摘要直讀)")
                                
                                # 組合完整內容供歷史記錄
                                full_content = f"**[{doc_type_label}]** {doc['file_name']}\n\n"
                                if doc.get('summary'):
                                    full_content += f"📝 **摘要**\n{doc['summary']}\n\n"
                                if doc.get('key_points'):
                                    full_content += f"🎯 **重點**\n{doc['key_points']}"
                                
                                # 儲存到歷史
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": full_content,
                                    "tokens": 0
                                })
                                st.rerun()
                        
                        else:
                            # 有搜尋結果,繼續正常流程 (需要 GPT 處理)
                            # 2. 組合上下文 (Context)
                            context_parts = []
                            context_header = "以下是相關的參考資料:\n\n"
                            
        
                            for i, doc in enumerate(search_results, 1):
                                # 動態調整 Context 長度: 如果結果少(針對特定文件), 則提供更多內容
                                max_len = 8000 if len(search_results) <= 2 else 3000
                                content = doc.get('raw_content', '')
                                if content:
                                    content = content[:max_len]
                                else:
                                    content = doc.get('preview', '')
                                    
                                context_parts.append(f"[文件{i}] {doc['file_name']}\n{content}\n")
                            
                            context = "\n".join(context_parts)
                            
                            # 3. 建立 Prompt based on Query Type
                            if current_query_type == 'troubleshooting':
                                system_role = "你是工廠維修專家 (Troubleshooting Expert)。"
                                instruction = "請根據參考資料中的異常現象與解決方案，提供具體的維修建議。若涉及多個可能性，請依可能性高低排列。"
                            elif current_query_type == 'procedure':
                                system_role = "你是資深工程師 (SOP Expert)。"
                                instruction = "請根據參考資料，清晰條列出操作步驟。請保持步驟的順序性與完整性。"
                            elif current_query_type == 'knowledge':
                                system_role = "你是技術資料管理員 (Reference Expert)。"
                                instruction = "請根據參考資料，精準回答規格參數或錯誤代碼定義。請直接給出數據或定義，不需過多解釋。"
                            elif current_query_type == 'training':
                                system_role = "你是資深企業講師 (Training Expert)。"
                                instruction = "請根據參考資料，深入淺出地解釋技術原理或演算法概念。請使用教學口吻，適當舉例說明。"
                            else:
                                system_role = ""
                                instruction = "請根據上述參考資料,簡潔明確地回答使用者的問題。如果參考資料不足,請據實告知。"
        
                            full_prompt = f"""{system_role}
        {context_header}{context}
        
        ---
        
    使用者問題:{prompt} ({current_query_type} mode)
    
    {instruction}
    """
                        
                            # 4. 呼叫 AI (傳遞使用者的 API 設定)
                            with st.spinner("AI 思考中..."):
                                # 準備 API 應證
                                api_key_used = user_api_key if user_api_key else None
                                base_url_used = user_base_url if user_base_url else None
                                
                                # v3.0: 使用選擇的問答模型
                                response, usage = ai_core.analyze_slide(
                                    text=full_prompt,
                                    image_paths=None,
                                    api_mode="text_only",
                                    api_key=api_key_used,
                                    base_url=base_url_used,
                                    text_model=chat_model  # v3.0 動態模型
                                )
                            # 5. 顯示回應
                            st.markdown(response)
                            
                            # 顯示 Token 使用
                            tokens_used = usage.get('total_tokens', 0)
                            st.caption(f"💡 本次使用: {tokens_used} tokens")
            
                            # 顯示參考資料來源
                            if search_results:
                                # 取得匹配層級
                                match_level = search_results[0].get('match_level', 'unknown')
                                match_level_display = {
                                    'keywords': '🎯 關鍵字',
                                    'summary': '📝 摘要',
                                    'raw_content': '📄 全文',
                                    'unknown': '🔍 一般'
                                }
                                
                                with st.expander(f"📚 參考資料來源 ({len(search_results)} 筆) - 匹配層級: {match_level_display.get(match_level, '🔍 一般')}"):
                                    for doc in search_results:
                                        st.write(f"- **{doc['file_name']}** ({doc['file_type']})")
        
                            # 記錄 Token
                            database.log_token_usage(
                                file_name=None,
                                operation='qa',
                                usage=usage
                            )
                            
                            # 更新 Session 統計
                            st.session_state.session_tokens += tokens_used
                            
                            # 儲存訊息
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": response,
                                "tokens": tokens_used
                            })
            
                        # 重新載入以更新側邊欄
                        st.rerun()
    
    # 頁面底部說明
    st.markdown("---")
    st.caption("💡 提示：")
    st.caption("- 您可以在左側限定搜尋範圍，例如只搜尋「日常手順」")
    st.caption("- 模糊搜尋可以自動修正錯字，如 'polars' 打成 'polar'")
    st.caption("- 系統會根據您的問題，自動從資料庫中找出最相關的文件作為參考")

elif page == "📚 知識庫清單":
    # === Library Interface ===
    
    def format_size(size_bytes):
         if not size_bytes: return "Unknown"
         for unit in ['B', 'KB', 'MB', 'GB']:
             if size_bytes < 1024:
                 return f"{size_bytes:.1f} {unit}"
             size_bytes /= 1024
         return f"{size_bytes:.1f} TB"

    st.markdown("### 📂 文件管理")
    
    # Fetch all documents
    docs = database.document_ops.get_all_documents()
    
    if not docs:
        st.info("目前知識庫中沒有任何文件。")
    else:
        # Convert to DataFrame
        df = pd.DataFrame(docs)
        
        # Preprocess Columns
        df['size_display'] = df['file_size'].apply(format_size)
        df['tags'] = df['tags'].fillna('')
        
        # Rename columns for display
        df_display = df.rename(columns={
            'filename': '檔案名稱',
            'doc_type': '類型',
            'upload_date': '上傳日期',
            'size_display': '大小',
            'processing_time': '處理耗時(秒)',
            'tags': '標籤'
        })
        
        # Display Columns
        display_cols = ['檔案名稱', '類型', '大小', '上傳日期', '標籤', '處理耗時(秒)']
        
        # Tabs for filtering
        tabs = st.tabs(["全部", "📚 知識庫", "🎓 教育訓練", "📋 日常手順", "🔧 異常解析"])
        
        with tabs[0]:
            st.dataframe(
                df_display[display_cols],
                width="stretch",
                hide_index=True,
                column_config={
                    "上傳日期": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
                }
            )
            
        # Helper to filter by type
        type_mapping = {
            "📚 知識庫": "Knowledge",
            "🎓 教育訓練": "Training",
            "📋 日常手順": "Procedure",
            "🔧 異常解析": "Troubleshooting"
        }
        
        for i, (tab_name, db_type) in enumerate(type_mapping.items(), 1):
            with tabs[i]:
                filtered_df = df_display[df_display['類型'] == db_type]
                if filtered_df.empty:
                     st.info(f"此類別 ({db_type}) 尚無文件。")
                else:
                    st.dataframe(
                        filtered_df[display_cols],
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "上傳日期": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
                        }
                    )

