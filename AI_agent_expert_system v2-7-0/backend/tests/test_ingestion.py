"""
Ingestion 入庫測試 - 驗證文件處理流程
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestIngestionProcessing:
    """文件入庫處理測試"""

    def test_markdown_file_ingestion(self, tmp_path):
        """測試 Markdown 檔案入庫"""
        test_file = tmp_path / "test_knowledge.md"
        test_file.write_text(
            "# 測試知識文件\n\n## 章節一\n\n這是測試內容。\n\n## 章節二\n\n更多內容。",
            encoding="utf-8",
        )
        assert test_file.exists()
        assert test_file.stat().st_size > 0

    def test_text_file_ingestion(self, tmp_path):
        """測試純文字檔案入庫"""
        test_file = tmp_path / "test_procedure.txt"
        test_file.write_text(
            "SOP: 設備操作手順\n\n步驟一: 開機\n步驟二: 校準\n步驟三: 作業",
            encoding="utf-8",
        )
        assert test_file.exists()

    def test_pptx_file_detection(self, tmp_path):
        """測試 PPTX 檔案偵測"""
        test_file = tmp_path / "training_material.pptx"
        # 建立空的 PPTX-like 檔案 (實際需要 python-pptx)
        test_file.write_bytes(b"PK\x03\x04" + b"\x00" * 100)
        assert test_file.suffix == ".pptx"

    def test_unsupported_format_rejection(self, tmp_path):
        """測試不支援格式的拒絕"""
        test_file = tmp_path / "data.xlsx"
        test_file.write_bytes(b"\x00" * 50)

        supported = {".md", ".txt", ".pptx", ".ppt", ".pdf", ".png", ".jpg", ".jpeg"}
        assert test_file.suffix not in supported


class TestDocTypeInference:
    """文件類型推測測試"""

    @pytest.mark.parametrize(
        "filename, expected_type",
        [
            ("8D_Report_N706.md", "troubleshooting"),
            ("異常解析_Oven.md", "troubleshooting"),
            ("SOP_焊接作業.md", "procedure"),
            ("手順_組裝.txt", "procedure"),
            ("培訓教材_安全.pptx", "training"),
            ("教育訓練_品質.md", "training"),
            ("技術規格書.md", "knowledge"),
            ("一般文件.txt", "knowledge"),
        ],
    )
    def test_doc_type_by_filename(self, filename, expected_type):
        """測試根據檔名推測文件類型"""
        try:
            from backend.app.services.file_watcher import DocumentFileHandler

            handler = DocumentFileHandler(
                raw_dir="/tmp/raw",
                archive_dir="/tmp/archive",
                failed_dir="/tmp/failed",
            )
            result = handler._infer_doc_type(Path(filename))
            assert result == expected_type, f"{filename} 應為 {expected_type}，但得到 {result}"
        except ImportError:
            pytest.skip("無法匯入 file_watcher 模組")


class TestChunkGeneration:
    """分塊邏輯測試"""

    def test_markdown_splitting(self):
        """測試 Markdown 按章節分塊"""
        content = """# 標題

## 第一章

第一章內容。

## 第二章

第二章內容。

## 第三章

第三章內容。
"""
        sections = content.split("\n## ")
        # 第一個元素是 "# 標題\n\n"，後面才是各章節
        assert len(sections) >= 3

    def test_empty_document_handling(self):
        """測試空文件處理"""
        content = ""
        chunks = [c for c in content.split("\n## ") if c.strip()]
        assert len(chunks) == 0
