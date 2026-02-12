"""
Gemini Image Processor 測試
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestGeminiImageProcessor:
    """GeminiImageProcessor 單元測試"""

    def test_get_prompt_table(self):
        """測試表格提示詞"""
        try:
            from backend.app.core.image_processor import GeminiImageProcessor
            processor = GeminiImageProcessor.__new__(GeminiImageProcessor)
            prompt = processor._get_prompt("table")
            assert "Markdown" in prompt or "表格" in prompt
        except ImportError:
            pytest.skip("無法匯入 image_processor 模組")

    def test_get_prompt_flowchart(self):
        """測試流程圖提示詞"""
        try:
            from backend.app.core.image_processor import GeminiImageProcessor
            processor = GeminiImageProcessor.__new__(GeminiImageProcessor)
            prompt = processor._get_prompt("flowchart")
            assert "Mermaid" in prompt or "流程" in prompt
        except ImportError:
            pytest.skip("無法匯入 image_processor 模組")

    def test_get_prompt_auto(self):
        """測試自動模式提示詞"""
        try:
            from backend.app.core.image_processor import GeminiImageProcessor
            processor = GeminiImageProcessor.__new__(GeminiImageProcessor)
            prompt = processor._get_prompt("auto")
            assert len(prompt) > 50  # 自動模式應有較長的提示詞
        except ImportError:
            pytest.skip("無法匯入 image_processor 模組")

    def test_get_prompt_unknown_defaults_to_auto(self):
        """測試未知類型預設為 auto"""
        try:
            from backend.app.core.image_processor import GeminiImageProcessor
            processor = GeminiImageProcessor.__new__(GeminiImageProcessor)
            prompt_auto = processor._get_prompt("auto")
            prompt_unknown = processor._get_prompt("unknown_type")
            assert prompt_auto == prompt_unknown
        except ImportError:
            pytest.skip("無法匯入 image_processor 模組")

    @patch("google.generativeai.GenerativeModel")
    def test_process_image_success(self, mock_model_class, tmp_path):
        """測試圖片處理成功"""
        try:
            from backend.app.core.image_processor import GeminiImageProcessor

            # 建立假圖片
            test_image = tmp_path / "test.png"
            test_image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

            # Mock Gemini 回應
            mock_response = MagicMock()
            mock_response.text = "| 欄位A | 欄位B |\n|-------|-------|\n| 1 | 2 |"

            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            processor = GeminiImageProcessor()
            result = processor.process_image(str(test_image), prompt_type="table")

            assert result is not None
            assert "欄位" in result
        except ImportError:
            pytest.skip("無法匯入 image_processor 模組")

    @patch("google.generativeai.GenerativeModel")
    def test_process_image_file_not_found(self, mock_model_class):
        """測試處理不存在的圖片"""
        try:
            from backend.app.core.image_processor import GeminiImageProcessor

            mock_model = MagicMock()
            mock_model_class.return_value = mock_model

            processor = GeminiImageProcessor()
            result = processor.process_image("/nonexistent/image.png")

            assert result is None
        except ImportError:
            pytest.skip("無法匯入 image_processor 模組")


class TestSingletonPattern:
    """測試單例模式"""

    def test_get_image_processor_singleton(self):
        """測試 get_image_processor 回傳同一實例"""
        try:
            import backend.app.core.image_processor as mod
            # 重設全域變數
            mod._processor = None
            with patch("google.generativeai.GenerativeModel"):
                p1 = mod.get_image_processor()
                p2 = mod.get_image_processor()
                assert p1 is p2
        except ImportError:
            pytest.skip("無法匯入 image_processor 模組")
