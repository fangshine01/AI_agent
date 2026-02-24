# -*- coding: utf-8 -*-
"""
測試 SOP 查詢和匯出功能
"""
import sys
sys.path.append('d:/Python/程式開發/AI agent/AI_agent_expert_system')

import logging
logging.basicConfig(level=logging.INFO)

from core.search import query_router

def test_sop_query():
    """測試 SOP 查詢功能"""
    print("=" * 60)
    print("測試 SOP 查詢功能")
    print("=" * 60)
    
    # 測試查詢
    test_queries = [
        "AFM 量測",
        "Cary300",
        "穿透率量測"
    ]
    
    for query in test_queries:
        print(f"\n查詢: {query}")
        print("-" * 60)
        
        # 使用 universal_search
        result = query_router.universal_search(
            query=query,
            top_k=3,
            query_type='procedure',
            filters={'doc_type': 'Procedure'}
        )
        
        print(f"查詢意圖: {result['intent']}")
        print(f"搜尋策略: {result['strategy']}")
        print(f"找到結果: {result['meta']['total_found']} 筆")
        print(f"搜尋時間: {result['meta']['search_time']:.2f} 秒")
        print(f"直讀模式: {result['meta'].get('skip_llm', False)}")
        
        if result['results']:
            print(f"\n前 {len(result['results'])} 筆結果:")
            for i, doc in enumerate(result['results'], 1):
                print(f"\n  [{i}] {doc.get('file_name', 'Unknown')}")
                print(f"      類型: {doc.get('file_type', 'Unknown')}")
                print(f"      相似度: {doc.get('similarity', 0):.2%}")
                
                # 檢查內容
                raw_content = doc.get('raw_content', '')
                content = doc.get('content', '')
                
                print(f"      raw_content 長度: {len(raw_content)}")
                print(f"      content 長度: {len(content)}")
                
                if raw_content:
                    # 儲存到檔案
                    filename = f"test_query_result_{i}.md"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"# 查詢: {query}\n\n")
                        f.write(f"## 檔案: {doc.get('file_name')}\n\n")
                        f.write(raw_content)
                    print(f"      ✓ 內容已儲存到: {filename}")
                else:
                    print(f"      ✗ 內容為空!")
        else:
            print("\n  無結果")
    
    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)

if __name__ == "__main__":
    test_sop_query()
