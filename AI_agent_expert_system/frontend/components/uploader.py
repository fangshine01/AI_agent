"""
檔案上傳組件 - 拖放式上傳 + 進度追蹤
支援使用者自訂 API Key 直接處理入庫
"""

import time
import streamlit as st
from typing import List, Optional
from frontend.client.api_client import APIClient


def render_file_uploader(
    api_client: APIClient,
    doc_type: str = "Knowledge",
    api_key: str = "",
    base_url: str = "",
):
    """
    渲染拖放式檔案上傳組件

    Args:
        api_client: API 客戶端
        doc_type: 預設文件類型
        api_key: 使用者 API Key（若提供則直接處理，不經 Watcher）
        base_url: API Base URL
    """
    # 文件類型選擇
    upload_doc_type = st.selectbox(
        "📁 文件類型",
        options=["Knowledge", "Training", "Procedure", "Troubleshooting"],
        format_func=lambda x: {
            "Knowledge": "📚 知識文件",
            "Training": "🎓 教育訓練",
            "Procedure": "📋 日常手順",
            "Troubleshooting": "🔧 異常解析",
        }[x],
        key="upload_doc_type",
    )

    uploaded_files = st.file_uploader(
        "拖放或選擇檔案",
        type=["pptx", "md", "txt", "pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="支援批次上傳，可一次選擇多個檔案",
    )

    if uploaded_files:
        st.success(f"✅ 已選擇 {len(uploaded_files)} 個檔案")

        # 預覽列表
        with st.expander("📋 檔案清單", expanded=True):
            for file in uploaded_files:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📄 {file.name}")
                with col2:
                    st.caption(f"{file.size / 1024:.1f} KB")

        # 處理模式說明
        if api_key:
            st.info("🔑 將使用您的 API Key 直接處理入庫（即時完成）")
        else:
            st.info("⏳ 檔案將上傳到監控目錄，由系統排程自動處理")

        # 處理按鈕
        if st.button("🚀 開始處理", type="primary", use_container_width=True):
            _process_upload(api_client, uploaded_files, upload_doc_type, api_key, base_url)


def _process_upload(
    api_client: APIClient,
    uploaded_files: list,
    doc_type: str,
    api_key: str = "",
    base_url: str = "",
):
    """處理上傳並追蹤進度"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.container()

    total = len(uploaded_files)
    success_count = 0
    fail_count = 0

    for idx, file in enumerate(uploaded_files):
        status_text.text(f"📤 處理中 ({idx + 1}/{total}): {file.name}")

        if api_key:
            # 有 API Key: 使用直接處理端點（使用者自己的 API 消耗）
            result = api_client.upload_and_process(
                file_content=file.getvalue(),
                filename=file.name,
                doc_type=doc_type,
                api_key=api_key,
                base_url=base_url,
            )
        else:
            # 無 API Key: 只上傳到 raw_files，由 Watcher 處理
            result = api_client.upload_file(
                file_content=file.getvalue(),
                filename=file.name,
                doc_type=doc_type,
            )

        # 更新進度
        progress = (idx + 1) / total
        progress_bar.progress(progress)

        if result.get("success", False):
            success_count += 1
            with results_container:
                doc_id = result.get("data", {}).get("doc_id", "N/A")
                chunks = result.get("data", {}).get("chunks", "N/A")
                if api_key:
                    st.success(f"✅ {file.name} - 入庫成功 (doc_id={doc_id}, chunks={chunks})")
                else:
                    st.success(f"✅ {file.name} - 已上傳到監控目錄")
        else:
            fail_count += 1
            with results_container:
                error_msg = result.get("message", "未知錯誤")
                st.error(f"❌ {file.name} - {error_msg}")

    # 最終摘要
    status_text.empty()
    progress_bar.empty()

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📤 總計", total)
    with col2:
        st.metric("✅ 成功", success_count)
    with col3:
        st.metric("❌ 失敗", fail_count)

    if fail_count == 0:
        st.balloons()

    if not api_key and success_count > 0:
        # 無 API Key 時啟動輪詢狀態追蹤
        st.markdown("---")
        st.subheader("📊 處理狀態追蹤")
        _poll_processing_status(api_client, [f.name for f in uploaded_files])


def _poll_processing_status(api_client: APIClient, file_names: list):
    """輪詢檔案處理狀態（僅在透過 Watcher 處理時使用）"""
    status_container = st.container()
    max_wait = 120
    elapsed = 0

    while elapsed < max_wait:
        with status_container:
            pending = []
            completed = []
            failed = []

            for name in file_names:
                status = api_client.get_processing_status(name)
                s = status.get("status", "pending")
                if s == "completed":
                    completed.append(name)
                elif s == "failed":
                    failed.append(name)
                else:
                    pending.append(name)

            col1, col2, col3 = st.columns(3)
            col1.metric("⏳ 處理中", len(pending))
            col2.metric("✅ 已完成", len(completed))
            col3.metric("❌ 失敗", len(failed))

            if not pending:
                if failed:
                    st.warning(f"部分檔案處理失敗: {', '.join(failed)}")
                else:
                    st.balloons()
                break

        time.sleep(3)
        elapsed += 3

    if elapsed >= max_wait and pending:
        st.warning("⏰ 部分檔案仍在處理中，請稍後在管理介面查看")

