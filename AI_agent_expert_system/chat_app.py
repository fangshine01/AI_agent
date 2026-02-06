"""
AI Expert System - Chat UI (使用者問答介面)
Port: 8502

功能：
- 專家問答（整合 v2.0 搜尋）
- 分類範圍選擇
- Session Token 統計
"""

import streamlit as st
from datetime import datetime
from core import database, ai_core
from core import search  # v3.0 重構後的 search 模組
import config
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

# 標題
st.title("💬 AI Expert System - 專家問答")
st.caption("由 v3.0 向量搜尋引擎驅動")

# 側邊欄:API 設定與搜尋設定
with st.sidebar:
    st.header("🔑 API 設定")
    st.caption("輸入您自己的 API 資訊(可選)")
    
    # 使用 session_state 儲存 API 設定
    if 'user_api_key' not in st.session_state:
        st.session_state.user_api_key = ""
    if 'user_base_url' not in st.session_state:
        st.session_state.user_base_url = "https://api.openai.com/v1"
    
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
    
    st.header("⚙️ 搜尋設定")
    
    # 分類過濾
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
    
    # 搜尋限制
    search_limit = st.slider("搜尋結果數", 1, 20, 5)
    
    # v3.0 新增: 搜尋模式選擇
    st.markdown("**🔬 v3.0 搜尋模式**")
    search_mode = st.radio(
        "選擇搜尋策略",
        options=["hybrid", "vector", "keyword"],
        format_func=lambda x: {
            "hybrid": "🔀 混合搜尋 (推薦)",
            "vector": "🎯 向量搜尋",
            "keyword": "🔤 關鍵字搜尋"
        }[x],
        horizontal=True
    )
    
    # v3.0 新增: 問答模型選擇
    st.markdown("**🤖 問答模型**")
    chat_model = st.selectbox(
        "選擇推理模型",
        options=["gpt-4o-mini", "gpt-4o", "gemini-2.0-flash-exp"],
        format_func=lambda x: f"{x} {config.MODEL_COST_LABELS.get(x, '')}"
    )
    
    # 模糊搜尋
    enable_fuzzy = st.checkbox("啟用模糊搜尋", value=True)
    
    st.markdown("---")
    
    st.header("📊 Session 狀態")
    st.metric("本次對話 Token", f"{st.session_state.session_tokens:,}")
    
    if st.button("清空對話記錄"):
        st.session_state.messages = []
        st.session_state.session_tokens = 0
        st.rerun()
    
    st.markdown("---")
    st.caption("提示：使用模糊搜尋可以容忍拼寫錯誤")

# 主要對話區
st.markdown("### 對話記錄")

# 顯示歷史訊息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # 顯示 Token 使用（如果是 assistant 訊息）
        if message["role"] == "assistant" and "tokens" in message:
            st.caption(f"💡 本次使用: {message['tokens']} tokens")

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
            # 正常搜尋流程 (v3.0)
            with st.spinner("正在搜尋相關資料..."):
                # 準備 API 金鑰與 URL (優先使用側邊欄輸入，否則使用系統預設)
                api_key_used = user_api_key if user_api_key else None
                base_url_used = user_base_url if user_base_url else None
                
                # 1. 根據搜尋模式選擇搜尋函數
                if search_mode == "vector":
                    # 純向量搜尋
                    raw_results = search.search_by_vector(
                        query=prompt,
                        top_k=search_limit,
                        api_key=api_key_used,
                        base_url=base_url_used
                    )
                    # 轉換為統一格式
                    search_results = []
                    for r in raw_results:
                        search_results.append({
                            'id': r['doc_id'],
                            'file_name': r['document']['filename'],
                            'file_type': r['document']['doc_type'],
                            'content': r['content'],
                            'similarity': r['similarity']
                        })
                    
                elif search_mode == "hybrid":
                    # 混合搜尋
                    raw_results = search.hybrid_search(
                        query=prompt,
                        top_k=search_limit,
                        api_key=api_key_used,
                        base_url=base_url_used
                    )
                    # 轉換為統一格式
                    search_results = []
                    for r in raw_results:
                        search_results.append({
                            'id': r['doc_id'],
                            'file_name': r['document']['filename'],
                            'file_type': r['document']['doc_type'],
                            'content': r['content'],
                            'total_score': r['total_score']
                        })
                
                else:
                    # 關鍵字搜尋 (v2.0)
                    search_results = search.search_documents_v2(
                        query=prompt,
                        file_types=selected_types if selected_types else None,
                        fuzzy=enable_fuzzy,
                        top_k=search_limit
                    )
                
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
                    # 有搜尋結果,繼續正常流程
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
                    
                    # 3. 建立 Prompt
                    full_prompt = f"""{context_header}{context}

---

使用者問題:{prompt}

請根據上述參考資料,簡潔明確地回答使用者的問題。如果參考資料不足,請據實告知。
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
