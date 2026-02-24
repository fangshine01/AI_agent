
import sys
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import json

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.parsers.procedure_parser import ProcedureParser

class TestProcedureParser(unittest.TestCase):

    def setUp(self):
        self.mock_ai_wrapper = MagicMock()
        self.parser = ProcedureParser(self.mock_ai_wrapper)
        
        # Mock AI response
        self.mock_ai_response = {
            "Goal": "Clean the Lens",
            "Target": "Exposure Machine A",
            "Tools": ["Wipes", "Alcohol"],
            "Safety": ["Wear gloves"],
            "Steps": ["1. Apply alcohol", "2. Wipe gently"]
        }
        
    def test_parse_success(self):
        """Test successful parsing of SOP content"""
        # Mock AI return value (AICoreWrapper in ingestion_v3 returns str, not tuple)
        self.mock_ai_wrapper.analyze_slide.return_value = json.dumps(self.mock_ai_response)
        
        content = "Raw content of SOP..."
        result = self.parser.parse(content)
        
        # Check result structure
        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertEqual(item['type'], 'procedure_full')
        self.assertEqual(item['title'], 'Clean the Lens')
        self.assertIn("# [SOP] Clean the Lens", item['content'])
        self.assertIn("## 🎯 適用範圍", item['content'])
        self.assertIn("Exposure Machine A", item['content'])
        self.assertIn("## ⚠️ 安全注意事項", item['content'])
        self.assertIn("- Wear gloves", item['content'])
        self.assertIn("## 🔢 操作步驟", item['content'])
        self.assertIn("1. Apply alcohol", item['content'])

    def test_parse_failure_fallback(self):
        """Test fallback to raw content on AI failure"""
        # Mock AI failure
        self.mock_ai_wrapper.analyze_slide.side_effect = Exception("AI Error")
        
        content = "Raw content of SOP..."
        result = self.parser.parse(content)
        
        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertEqual(item['type'], 'raw')
        self.assertEqual(item['content'], content)

if __name__ == '__main__':
    unittest.main()
