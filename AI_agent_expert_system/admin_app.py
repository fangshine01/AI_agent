"""
AI Expert System - Admin UI (後台管理介面)
Port: 8501 (預設)

功能：
- 文件上傳與解析（支援四種類型）
- 資料庫管理與統計
- Token 使用監控
- 系統設定
"""

import streamlit as st
import os
from datetime import datetime
from core import database, ingestion
from core import ingestion_v3  # v3.0 新模組
from core import search  # v3.0 重構後的 search 模組
import config

# 頁面設定
st.set_page_config(
    page_title="AI Expert System - 管理後台",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ AI Expert System - 管理後台")
st.markdown("---")

# 側邊欄：系統資訊
with st.sidebar:
    st.header("📊 系統資訊")
    
    # 資料庫統計
    db_stats = database.get_document_stats()
    st.metric("總文件數", db_stats['total_documents'])
    
    st.subheader("文件分類")
    for doc_type, count in db_stats.get('by_type', {}).items():
        st.write(f"- {doc_type}: {count} 份")
    
    # Token 統計
    token_stats = database.get_token_stats()
    st.subheader("Token 使用")
    st.metric("總使用量", f"{token_stats['total_tokens']:,} tokens")
    
    st.markdown("---")
    st.caption(f"Database: {config.DB_PATH}")


# 主要內容區：Tab 分頁
tab1, tab2, tab3, tab4 = st.tabs([
    "📤 文件上傳",
    "🗂️ 資料庫管理",
    "📈 Token 監控",
    "⚙️ 系統設定"
])

# ========== Tab 1: 文件上傳 ==========
with tab1:
    st.header("文件上傳與解析")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("選擇文件類型")
        file_type = st.selectbox(
            "文件分類",
            options=['knowledge', 'training', 'procedure', 'troubleshooting'],
            format_func=lambda x: {
                'knowledge': '📚 知識庫',
                'training': '🎓 教育訓練',
                'procedure': '📋 日常手順',
                'troubleshooting': '🔧 異常解析'
            }[x]
        )
        
        st.info({
            'knowledge': '適合技術文件、手冊、教科書等有章節結構的內容',
            'training': '適合培訓教材、課程講義',
            'procedure': '適合 SOP、操作手順、流程說明',
            'troubleshooting': '適合異常報告、8D 報告、維修記錄'
        }[file_type])
        
        doc_dir = st.text_input(
            "文件資料夾路徑",
            value="",
            placeholder="例如: D:/Documents/SOP"
        )
        
        file_extensions = st.multiselect(
            "支援的檔案格式",
            options=['.pptx', '.md', '.txt', '.pdf'],
            default=['.pptx', '.md', '.txt']
        )
    
    with col2:
        st.subheader("處理選項")
        
        # 取得系統預設設定
        current_config = config.get_api_config()
        default_analysis_mode = current_config.get('analysis_mode', 'auto')
        default_text_model = current_config.get('model_text', 'gpt-4o-mini')
        default_vision_model = current_config.get('model_vision', 'gpt-4o')

        # v3.0 新增: Analysis Mode 選擇
        st.write("**📊 分析模式 (預設值來自系統設定)**")
        
        analysis_mode_options = ["text_only", "vision", "auto"]
        # 確保預設值在選項中
        if default_analysis_mode not in analysis_mode_options:
            analysis_mode_options.append(default_analysis_mode)
            
        analysis_mode = st.radio(
            "Analysis Mode",
            options=analysis_mode_options,
            index=analysis_mode_options.index(default_analysis_mode),
            format_func=lambda x: {
                "text_only": "💰 純文字 (經濟)",
                "vision": "👁️ 圖文分析 (高階)",
                "auto": "🤖 自動判斷"
            }.get(x, x),
            horizontal=True
        )
        
        # v3.0 新增: 模型選擇
        col_model1, col_model2 = st.columns(2)
        with col_model1:
            # 定義選項 (與系統設定一致)
            text_model_options = [
                "gpt-4o-mini", "gpt-4.1-mini", "gemini-2.5-flash-lite", 
                "gemini-2.5-flash", "gpt-4o", "gpt-4.1", "gemini-2.5-pro"
            ]
            
            # 確保預設值在選項中
            if default_text_model and default_text_model not in text_model_options:
                text_model_options.append(default_text_model)
                
            text_model = st.selectbox(
                "解析模型 (Text)",
                options=text_model_options,
                index=text_model_options.index(default_text_model) if default_text_model in text_model_options else 0,
                format_func=lambda x: f"{x} {config.MODEL_COST_LABELS.get(x, '')}"
            )
        
        with col_model2:
            # 定義選項
            vision_model_options = ["gpt-4o", "gemini-2.5-flash", "gemini-2.5-pro", "gpt-4.1"]
            
            # 確保預設值在選項中
            if default_vision_model and default_vision_model not in vision_model_options:
                vision_model_options.append(default_vision_model)

            vision_model = st.selectbox(
                "視覺模型 (Vision)",
                options=vision_model_options,
                index=vision_model_options.index(default_vision_model) if default_vision_model in vision_model_options else 0,
                format_func=lambda x: f"{x} {config.MODEL_COST_LABELS.get(x, '')}"
            ) if analysis_mode in ["vision", "auto"] else None
        
        st.write("**處理流程 (v3.0)**:")
        st.write("1. 讀取檔案內容")
        st.write("2. AI 解析 → 標準化切片")
        st.write("3. 向量化所有切片")
        st.write("4. 寫入資料庫 (Parent-Child)")
        
        # 檢查 API 是否已設定
        api_config = config.get_api_config()
        if not api_config['api_key']:
            st.error("⚠️ 請先在「系統設定」頁面設定 API Key")
        else:
            st.info(f"✅ API 已設定: {api_config['base_url']}")
    
    if st.button("🚀 開始處理", type="primary", use_container_width=True):
        # 檢查 API 設定
        api_config = config.get_api_config()
        if not api_config['api_key']:
            st.error("❌ 請先在「系統設定」頁面設定 API Key!")
        elif not doc_dir or not os.path.exists(doc_dir):
            st.error("請輸入有效的資料夾路徑")
        else:
            with st.spinner(f"正在處理 {file_type} 文件..."):
                # 建立進度條
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(current, total, message):
                    progress_bar.progress(current / total)
                    status_text.text(f"[{current}/{total}] {message}")
                
                # 執行處理 (v3.0)
                stats = ingestion_v3.process_directory_v3(
                    doc_dir=doc_dir,
                    doc_type=file_type.capitalize(),  # v3.0 使用大寫
                    analysis_mode=analysis_mode,
                    text_model=text_model,
                    vision_model=vision_model,
                    file_extensions=file_extensions,
                    progress_callback=lambda msg: status_text.text(msg)
                )
                
                # 顯示結果
                st.success("✅ v3.0 處理完成！")
                
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("總檔案", stats['processed'])
                col_b.metric("成功", stats['success'])
                col_c.metric("錯誤數", len(stats['errors']))
                
                if stats['errors']:
                    with st.expander("查看錯誤詳情"):
                        for error in stats['errors']:
                            st.error(f"{error['file']}: {error['error']}")

# ========== Tab 2: 資料庫管理 ==========
with tab2:
    st.header("資料庫管理")
    
    # 搜尋功能
    st.subheader("🔍 搜尋文件")
    search_col1, search_col2 = st.columns([3, 1])
    
    with search_col1:
        search_query = st.text_input("搜尋關鍵字", placeholder="輸入關鍵字...")
    
    with search_col2:
        search_types = st.multiselect(
            "限定類型",
            options=['knowledge', 'training', 'procedure', 'troubleshooting'],
            default=[]
        )
    
    if search_query:
        results = search.search_documents_v2(
            query=search_query,
            file_types=search_types if search_types else None,
            fuzzy=True,
            top_k=20
        )
        
        st.write(f"找到 **{len(results)}** 筆結果")
        
        for doc in results:
            with st.expander(f"📄 {doc['file_name']} ({doc['file_type']})"):
                st.write(f"**ID**: {doc['id']}")
                if doc.get('author'):
                    st.write(f"**作者**: {doc['author']}")
                st.write(f"**上傳時間**: {datetime.fromtimestamp(doc['upload_time']).strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**預覽**: {doc.get('preview', '')}")
                
                if st.button(f"刪除", key=f"del_{doc['id']}"):
                    if database.delete_document(doc['id']):
                        st.success("已刪除")
                        st.rerun()
                    else:
                        st.error("刪除失敗")
    
    st.markdown("---")
    
    # 統計資訊
    st.subheader("📊 資料統計")
    stats = database.get_document_stats()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("總文件數", stats['total_documents'])
    
    with col2:
        st.write("**分類分佈**")
        for doc_type, count in stats.get('by_type', {}).items():
            st.write(f"- {doc_type}: {count}")

# ========== Tab 3: Token 監控 ==========
with tab3:
    st.header("Token 使用監控")
    
    # 時間範圍選擇
    time_range = st.selectbox(
        "時間範圍",
        options=[None, 1, 7, 30],
        format_func=lambda x: "全部" if x is None else f"最近 {x} 天"
    )
    
    token_stats = database.get_token_stats(days=time_range)
    
    # 總覽
    col1, col2, col3 = st.columns(3)
    col1.metric("總 Token", f"{token_stats['total_tokens']:,}")
    col2.metric("Input Tokens", f"{token_stats['total_prompt_tokens']:,}")
    col3.metric("Output Tokens", f"{token_stats['total_completion_tokens']:,}")
    
    st.markdown("---")
    
    # 按操作類型統計
    st.subheader("按操作類型")
    by_op = token_stats.get('by_operation', {})
    if by_op:
        for op, count in by_op.items():
            st.write(f"- {op}: {count:,} tokens")
    
    st.markdown("---")
    
    # Top 10 檔案
    st.subheader("Top 10 消耗檔案")
    by_file = token_stats.get('by_file', [])
    if by_file:
        for item in by_file[:10]:
            st.write(f"- {item['file_name']}: {item['total_tokens']:,} tokens")
    
    st.markdown("---")
    
    # 最近使用記錄
    st.subheader("最近 20 筆記錄")
    recent = token_stats.get('recent_usage', [])
    if recent:
        for record in recent[:20]:
            timestamp = datetime.fromtimestamp(record['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            st.text(f"{timestamp} | {record['operation']} | {record['file_name'] or 'N/A'} | {record['total_tokens']} tokens")

# ========== Tab 4: 系統設定 ==========
with tab4:
    st.header("系統設定")
    
    st.subheader("🔑 API 設定")
    st.info("請輸入您的 OpenAI API 相容服務的設定")
    
    # 取得當前設定
    current_config = config.get_api_config()
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_api_key = st.text_input(
            "API Key",
            value=current_config['api_key'],
            type="password",
            help="您的 OpenAI API Key 或相容服務的 API Key"
        )
        
        # 定義可用模型清單 (來自 model_pricing_comparison.md)
        vision_model_options = [
            "gpt-4o", 
            "gemini-2.5-flash", 
            "gemini-2.5-pro", 
            "gpt-4.1"
        ]
        
        # 確保當前設定的值在選項中，如果不在則加入
        current_vision = current_config['model_vision']
        if current_vision and current_vision not in vision_model_options:
            vision_model_options.append(current_vision)
            
        new_model_vision = st.selectbox(
            "Vision 模型名稱",
            options=vision_model_options,
            index=vision_model_options.index(current_vision) if current_vision in vision_model_options else 0,
            help="支援圖片分析的模型 (建議: gpt-4o)"
        )
    
    with col2:
        new_base_url = st.text_input(
            "Base URL",
            value=current_config['base_url'],
            help="API 端點 URL,例如 https://api.openai.com/v1"
        )
        
        # 定義可用模型清單 (來自 model_pricing_comparison.md)
        text_model_options = [
            "gpt-4o-mini",
            "gpt-4.1-mini", 
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gpt-4o", 
            "gpt-4.1", 
            "gemini-2.5-pro"
        ]
        
        # 確保當前設定的值在選項中
        current_text = current_config['model_text']
        if current_text and current_text not in text_model_options:
            text_model_options.append(current_text)
            
        new_model_text = st.selectbox(
            "Text 模型名稱",
            options=text_model_options,
            index=text_model_options.index(current_text) if current_text in text_model_options else 0,
            help="純文字模型 (建議: gpt-4o-mini 或 gemini-2.5-flash-lite)"
        )
        
    # 分析模式設定 (v3.0)
    st.markdown("---")
    st.subheader("📊 預設分析模式")
    
    analysis_mode_options = ["text_only", "vision", "auto"]
    current_mode = current_config.get('analysis_mode', 'auto')
    
    new_analysis_mode = st.radio(
        "選擇預設的分析模式",
        options=analysis_mode_options,
        index=analysis_mode_options.index(current_mode) if current_mode in analysis_mode_options else 2,
        format_func=lambda x: {
            "text_only": "💰 純文字 (經濟) - 僅分析文字內容",
            "vision": "👁️ 圖文分析 (高階) - 分析整張投影片截圖",
            "auto": "🤖 自動判斷 - (推薦)"
        }.get(x, x),
        horizontal=True
    )
    
    if st.button("💾 儲存 API 設定", type="primary"):
        config.set_api_config(
            api_key=new_api_key,
            base_url=new_base_url,
            model_vision=new_model_vision,
            model_text=new_model_text,
            analysis_mode=new_analysis_mode
        )
        st.success("✅ API 設定已儲存!")
        st.rerun()
    
    # 顯示當前狀態
    if current_config['api_key']:
        st.success("✅ API Key 已設定")
    else:
        st.warning("⚠️ 尚未設定 API Key,請輸入後點擊「儲存」")
    
    st.markdown("---")
    
    st.subheader("📁 資料庫路徑")
    st.code(config.DB_PATH, language="text")
    st.code(config.TOKEN_DB_PATH, language="text")
    
    st.markdown("---")
    
    st.subheader("⚠️ 危險操作")
    if st.button("🗑️ 清空所有文件", type="secondary"):
        st.warning("此功能尚未實作,請手動刪除資料庫檔案")
