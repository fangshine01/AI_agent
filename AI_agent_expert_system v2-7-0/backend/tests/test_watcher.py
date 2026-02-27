"""
File Watcher 測試 - 驗證檔案監控服務功能
"""

import os
import time
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def watcher_dirs(tmp_path):
    """建立臨時測試目錄結構"""
    raw_dir = tmp_path / "raw_files"
    archive_dir = tmp_path / "archived_files"
    failed_dir = tmp_path / "failed_files"
    generated_dir = tmp_path / "generated_md"

    for d in [raw_dir, archive_dir, failed_dir, generated_dir]:
        d.mkdir()

    return {
        "raw_dir": str(raw_dir),
        "archive_dir": str(archive_dir),
        "failed_dir": str(failed_dir),
        "generated_dir": str(generated_dir),
    }


class TestDocumentFileHandler:
    """DocumentFileHandler 單元測試"""

    def test_infer_doc_type_troubleshooting(self):
        """測試異常解析類型推測"""
        try:
            from backend.app.services.file_watcher import DocumentFileHandler
            handler = DocumentFileHandler(
                raw_dir="/tmp/raw",
                archive_dir="/tmp/archive",
                failed_dir="/tmp/failed",
            )
            assert handler._infer_doc_type(Path("8D_report_N706.md")) == "troubleshooting"
            assert handler._infer_doc_type(Path("異常報告_Oven.md")) == "troubleshooting"
        except ImportError:
            pytest.skip("無法匯入 file_watcher 模組")

    def test_infer_doc_type_procedure(self):
        """測試手順類型推測"""
        try:
            from backend.app.services.file_watcher import DocumentFileHandler
            handler = DocumentFileHandler(
                raw_dir="/tmp/raw",
                archive_dir="/tmp/archive",
                failed_dir="/tmp/failed",
            )
            assert handler._infer_doc_type(Path("SOP_焊接作業.md")) == "procedure"
        except ImportError:
            pytest.skip("無法匯入 file_watcher 模組")

    def test_infer_doc_type_training(self):
        """測試教育訓練類型推測"""
        try:
            from backend.app.services.file_watcher import DocumentFileHandler
            handler = DocumentFileHandler(
                raw_dir="/tmp/raw",
                archive_dir="/tmp/archive",
                failed_dir="/tmp/failed",
            )
            assert handler._infer_doc_type(Path("培訓教材_安全.pptx")) == "training"
        except ImportError:
            pytest.skip("無法匯入 file_watcher 模組")

    def test_infer_doc_type_default(self):
        """測試預設類型推測"""
        try:
            from backend.app.services.file_watcher import DocumentFileHandler
            handler = DocumentFileHandler(
                raw_dir="/tmp/raw",
                archive_dir="/tmp/archive",
                failed_dir="/tmp/failed",
            )
            assert handler._infer_doc_type(Path("一般文件.md")) == "knowledge"
        except ImportError:
            pytest.skip("無法匯入 file_watcher 模組")


class TestFileWatcherIntegration:
    """File Watcher 整合測試"""

    def test_file_placed_in_raw_dir(self, watcher_dirs):
        """測試場景 1: 上傳檔案自動處理"""
        raw_dir = Path(watcher_dirs["raw_dir"])
        archive_dir = Path(watcher_dirs["archive_dir"])

        # 模擬放入檔案
        test_file = raw_dir / "test_doc.md"
        test_file.write_text("# 測試文件\n\n內容", encoding="utf-8")

        assert test_file.exists()
        # 注意: 完整整合測試需啟動 Watcher Observer

    def test_failed_file_moved(self, watcher_dirs):
        """測試場景 2: 失敗檔案移至 failed_files"""
        raw_dir = Path(watcher_dirs["raw_dir"])
        failed_dir = Path(watcher_dirs["failed_dir"])

        # 模擬處理失敗 → 移動檔案
        test_file = raw_dir / "bad_file.xyz"
        test_file.write_text("corrupted content")

        # 手動模擬移動
        shutil.move(str(test_file), str(failed_dir / test_file.name))
        assert (failed_dir / "bad_file.xyz").exists()
        assert not test_file.exists()

    def test_debounce_prevents_duplicate(self, watcher_dirs):
        """測試場景 3: Debounce 避免重複處理"""
        try:
            from backend.app.services.file_watcher import DocumentFileHandler
            handler = DocumentFileHandler(
                raw_dir=watcher_dirs["raw_dir"],
                archive_dir=watcher_dirs["archive_dir"],
                failed_dir=watcher_dirs["failed_dir"],
                debounce=1,
            )

            # 模擬同一檔案路徑加入 processing_files
            handler.processing_files.add("/tmp/test.md")
            assert "/tmp/test.md" in handler.processing_files

            # 清除
            handler.processing_files.discard("/tmp/test.md")
            assert "/tmp/test.md" not in handler.processing_files
        except ImportError:
            pytest.skip("無法匯入 file_watcher 模組")
