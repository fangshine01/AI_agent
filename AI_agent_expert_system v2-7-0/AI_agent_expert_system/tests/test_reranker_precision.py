
import sys
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import json

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.search.reranker import semantic_rerank

class TestRerankerPrecision(unittest.TestCase):
    def setUp(self):
        # 模擬搜尋結果
        self.mock_results = [
            {
                'source_title': 'N500 蝴蝶 Mura 解決方案',
                'content': '針對 N500 機種的 Mura 問題，建議調整...',
                'file_name': 'N500_Mura.pptx'
            },
            {
                'source_title': 'N706 蝴蝶 Mura 異常分析',
                'content': 'N706 產品線發生蝴蝶狀 Mura，原因是...',
                'file_name': 'N706_Mura.pptx'
            },
            {
                'source_title': '通用 Mura 處理原則',
                'content': '一般性的 Mura 處理方式，適用於多種機型...',
                'file_name': 'General_Mura.pdf'
            }
        ]
        
    @patch('core.ai_core.analyze_slide')
    def test_semantic_rerank_n706(self, mock_analyze_slide):
        # 模擬 AI 回傳的排序結果 (預期 N706 排第一)
        # 原始索引: 0=N500, 1=N706, 2=General
        # 預期排序: [1, 2, 0] (N706 > General > N500)
        # analyze_slide 回傳 (content, usage)
        mock_analyze_slide.return_value = ("[1, 2, 0]", {})
        
        query = "N706 蝴蝶 Mura"
        reranked = semantic_rerank(self.mock_results, query)
        
        # 驗證結果
        self.assertEqual(len(reranked), 3)
        self.assertEqual(reranked[0]['source_title'], 'N706 蝴蝶 Mura 異常分析')
        self.assertEqual(reranked[2]['source_title'], 'N500 蝴蝶 Mura 解決方案')
        
        print(f"\n查詢: '{query}'")
        print("排序結果:")
        for i, res in enumerate(reranked):
            print(f"{i+1}. {res['source_title']}")

if __name__ == '__main__':
    unittest.main()
