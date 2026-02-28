"""
系統資源監控 — @st.fragment(run_every=300s)

1.50+ 特性: border=True, Material icons
"""

import streamlit as st
import os
import pathlib
import logging

logger = logging.getLogger(__name__)


@st.fragment(run_every="300s")
def render_system_resources():
    """系統資源 — 低頻更新（每 5 分鐘）"""
    st.markdown("### :material/memory: 系統資源")

    try:
        _project_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent

        col1, col2, col3 = st.columns(3)
        with col1:
            db_path = str(_project_root / "backend" / "data" / "documents" / "knowledge_v2.db")
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path) / (1024 * 1024)
                st.metric(
                    ":material/database: 知識庫大小",
                    f"{db_size:.1f} MB",
                    border=True,
                )
            else:
                st.metric(":material/database: 知識庫大小", "N/A", border=True)
        with col2:
            raw_dir = str(_project_root / "backend" / "data" / "raw_files")
            if os.path.exists(raw_dir):
                file_count = len([
                    f for f in os.listdir(raw_dir)
                    if os.path.isfile(os.path.join(raw_dir, f))
                ])
                st.metric(
                    ":material/folder_open: 待處理檔案",
                    file_count,
                    border=True,
                )
            else:
                st.metric(":material/folder_open: 待處理檔案", 0, border=True)
        with col3:
            archived_dir = str(_project_root / "backend" / "data" / "archived_files")
            if os.path.exists(archived_dir):
                archived_count = len([
                    f for f in os.listdir(archived_dir)
                    if os.path.isfile(os.path.join(archived_dir, f))
                ])
                st.metric(
                    ":material/inventory_2: 已歸檔檔案",
                    archived_count,
                    border=True,
                )
            else:
                st.metric(":material/inventory_2: 已歸檔檔案", 0, border=True)
    except Exception as e:
        st.warning(f"無法載入系統資源: {e}")
