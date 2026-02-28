"""
文件管理列表 — @st.fragment 局部更新

從 admin.py 拆出，負責：
- 文件列表 (搜尋/篩選/排序)
- 刪除操作
"""

import streamlit as st
import pandas as pd
from utils.cache import cached_list_documents
from config import API_BASE_URL


@st.fragment
def render_document_manager(client):
    """文件管理列表 — 搜尋/篩選只重繪此 fragment，不觸發全頁 rerun"""
    st.subheader(":material/description: 已入庫文件列表")

    try:
        docs = cached_list_documents(API_BASE_URL)

        if docs:
            df = pd.DataFrame(docs)
            # 對映可能的欄位別名
            if "filename" in df.columns and "file_name" not in df.columns:
                df = df.rename(columns={"filename": "file_name"})
            elif "name" in df.columns and "file_name" not in df.columns:
                df = df.rename(columns={"name": "file_name"})

            display_cols = [
                c for c in ["id", "file_name", "doc_type", "chunk_count", "created_at", "status"]
                if c in df.columns
            ] or list(df.columns)

            if display_cols:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    search_text = st.text_input(
                        ":material/search: 搜尋文件名", placeholder="輸入關鍵字過濾"
                    )
                with col2:
                    if "doc_type" in df.columns:
                        type_filter = st.selectbox(
                            ":material/folder: 類型",
                            ["全部"] + sorted(df["doc_type"].dropna().unique().tolist()),
                        )
                    else:
                        type_filter = "全部"
                with col3:
                    sort_col = st.selectbox("排序", display_cols)

                # 過濾
                filtered_df = df.copy()
                if search_text and "file_name" in filtered_df.columns:
                    filtered_df = filtered_df[
                        filtered_df["file_name"].str.contains(search_text, case=False, na=False)
                    ]
                if type_filter != "全部" and "doc_type" in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df["doc_type"] == type_filter]

                if sort_col in filtered_df.columns:
                    filtered_df = filtered_df.sort_values(sort_col, ascending=False)

                st.dataframe(
                    filtered_df[display_cols],
                    width="stretch",
                    hide_index=True,
                    height=400,
                    column_config={
                        "id": st.column_config.NumberColumn("ID", width="small"),
                        "file_name": st.column_config.TextColumn("檔案名稱", width="large"),
                        "doc_type": st.column_config.TextColumn("文件類型", width="medium"),
                        "chunk_count": st.column_config.NumberColumn("分塊數", width="small"),
                        "created_at": st.column_config.TextColumn("建立時間", width="medium"),
                        "status": st.column_config.TextColumn("狀態", width="small"),
                    },
                )

                st.caption(f"顯示 {len(filtered_df)} / {len(df)} 筆文件")

                # 刪除操作
                st.subheader(":material/delete: 刪除文件")
                if "id" in df.columns:
                    del_id = st.number_input("輸入文件 ID", min_value=1, step=1)
                    if st.button("刪除文件", type="secondary"):
                        result = client.delete_document(int(del_id))
                        if result.get("status") == "success":
                            st.success(f"✅ 已刪除文件 ID={del_id}")
                            cached_list_documents.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ 刪除失敗: {result.get('message', 'unknown error')}")
            else:
                st.info("文件資料格式無法辨識")
        else:
            st.info(":material/inbox: 資料庫中尚無文件")
    except Exception as e:
        st.error(f"❌ 載入文件失敗: {e}")
