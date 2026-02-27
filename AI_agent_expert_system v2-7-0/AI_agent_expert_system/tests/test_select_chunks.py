# -*- coding: utf-8 -*-
"""
直接測試 document_grouping 的 select_chunks_dynamically 函數
"""
import sys
sys.path.append('d:/Python/程式開發/AI agent/AI_agent_expert_system')

import logging
logging.basicConfig(level=logging.DEBUG)

from core.search.document_grouping import select_chunks_dynamically

# 模擬一個關鍵字搜尋的結果
test_chunk = {
    'chunk_id': 21,
    'doc_id': 1,
    'file_name': 'AFM 量測.pptx',
    'file_type': 'Procedure',
    'raw_content': '# [SOP] AFM量測手法的標準作業程序...',
    'match_level': 'filename',  # 關鍵字搜尋標記
    'match_score': 2,
    'similarity': 0  # 關鍵字搜尋沒有 similarity
}

print("測試 select_chunks_dynamically:")
print("=" * 60)
print(f"輸入 chunk: {test_chunk}")
print("-" * 60)

result = select_chunks_dynamically([test_chunk], mode='qa')

print(f"\n輸出結果: {len(result)} 個 chunks")
if result:
    print("✓ 測試通過!")
else:
    print("✗ 測試失敗 - chunks 被過濾掉了!")
