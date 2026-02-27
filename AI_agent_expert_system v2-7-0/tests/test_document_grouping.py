# -*- coding: utf-8 -*-
"""
測試文件分組模組
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.search.document_grouping import (
    group_chunks_by_document,
    select_chunks_dynamically,
    format_grouped_results
)


def test_dynamic_chunk_selection():
    """測試動態chunk選擇邏輯"""
    print("\n=== 測試 1: 動態Chunk選擇 ===")
    
    # 模擬chunks (相似度遞減)
    chunks = [
        {'chunk_id': 1, 'similarity': 0.90, 'content': 'High similarity chunk'},
        {'chunk_id': 2, 'similarity': 0.88, 'content': 'High similarity chunk 2'},
        {'chunk_id': 3, 'similarity': 0.75, 'content': 'Medium similarity chunk'},
        {'chunk_id': 4, 'similarity': 0.72, 'content': 'Medium similarity chunk 2'},
        {'chunk_id': 5, 'similarity': 0.60, 'content': 'Low similarity chunk'},
    ]
    
    # 問答模式
    selected_qa = select_chunks_dynamically(chunks, mode='qa')
    print(f"問答模式: {len(chunks)} -> {len(selected_qa)} 個chunks")
    for chunk in selected_qa:
        print(f"  - Chunk {chunk['chunk_id']}: {chunk['similarity']:.2f}")
    
    # 訓練模式
    selected_training = select_chunks_dynamically(chunks, mode='training')
    print(f"訓練模式: {len(chunks)} -> {len(selected_training)} 個chunks")
    
    assert len(selected_qa) <= len(chunks), "問答模式應該選擇較少chunks"
    assert len(selected_training) == len(chunks), "訓練模式應該返回所有chunks"
    print("[PASS] 測試通過")


def test_document_grouping():
    """測試文件分組功能"""
    print("\n=== 測試 2: 文件分組 ===")
    
    # 模擬搜尋結果 (3個文件,每個文件多個chunks)
    search_results = [
        # 文件1
        {'chunk_id': 1, 'doc_id': 101, 'similarity': 0.90, 'content': 'Doc1 Chunk1', 
         'document': {'filename': 'N706 Oven Pin.txt', 'doc_type': 'Troubleshooting'}},
        {'chunk_id': 2, 'doc_id': 101, 'similarity': 0.85, 'content': 'Doc1 Chunk2',
         'document': {'filename': 'N706 Oven Pin.txt', 'doc_type': 'Troubleshooting'}},
        {'chunk_id': 3, 'doc_id': 101, 'similarity': 0.70, 'content': 'Doc1 Chunk3',
         'document': {'filename': 'N706 Oven Pin.txt', 'doc_type': 'Troubleshooting'}},
        
        # 文件2
        {'chunk_id': 4, 'doc_id': 102, 'similarity': 0.88, 'content': 'Doc2 Chunk1',
         'document': {'filename': 'N706 蝴蝶Mura.txt', 'doc_type': 'Troubleshooting'}},
        {'chunk_id': 5, 'doc_id': 102, 'similarity': 0.75, 'content': 'Doc2 Chunk2',
         'document': {'filename': 'N706 蝴蝶Mura.txt', 'doc_type': 'Troubleshooting'}},
        
        # 文件3
        {'chunk_id': 6, 'doc_id': 103, 'similarity': 0.65, 'content': 'Doc3 Chunk1',
         'document': {'filename': 'N706 ITO issue.txt', 'doc_type': 'Troubleshooting'}},
    ]
    
    # 執行分組
    grouped = group_chunks_by_document(
        chunks=search_results,
        mode='qa',
        token_budget=2500
    )
    
    print(f"原始結果: {len(search_results)} 個chunks")
    print(f"分組後: {len(grouped)} 個文件")
    
    for doc_id, data in grouped.items():
        print(f"\n文件 {doc_id}:")
        print(f"  - 檔名: {data['document_info'].get('filename')}")
        print(f"  - 總chunks: {len(data['all_chunks'])}")
        print(f"  - 選中chunks: {len(data['selected_chunks'])}")
        print(f"  - 平均相似度: {data['total_similarity'] / len(data['selected_chunks']):.2f}")
    
    assert len(grouped) == 3, "應該有3個文件"
    assert all(len(d['selected_chunks']) > 0 for d in grouped.values()), "每個文件至少有1個chunk"
    print("\n[PASS] 測試通過")


def test_format_grouped_results():
    """測試格式化功能"""
    print("\n=== 測試 3: 格式化分組結果 ===")
    
    # 模擬分組結果
    grouped = {
        101: {
            'doc_id': 101,
            'document_info': {'filename': 'Test.txt', 'doc_type': 'Knowledge'},
            'all_chunks': [{'chunk_id': 1}, {'chunk_id': 2}],
            'selected_chunks': [
                {'chunk_id': 1, 'source_title': 'Chapter 1', 'content': 'Content 1', 'similarity': 0.9}
            ],
            'total_similarity': 0.9,
            'summary': None
        }
    }
    
    formatted = format_grouped_results(grouped, include_summary=False)
    
    print(f"格式化結果: {len(formatted)} 個文件")
    for doc in formatted:
        print(f"\n文件: {doc['file_name']}")
        print(f"  - 類型: {doc['file_type']}")
        print(f"  - Chunks: {doc['chunk_count']}/{doc['total_chunks']}")
        print(f"  - 平均相似度: {doc['avg_similarity']:.2f}")
    
    assert len(formatted) == 1, "應該有1個文件"
    assert formatted[0]['chunk_count'] == 1, "應該有1個chunk"
    print("\n[PASS] 測試通過")


if __name__ == "__main__":
    print("開始測試文件分組模組...")
    
    try:
        test_dynamic_chunk_selection()
        test_document_grouping()
        test_format_grouped_results()
        
        print("\n" + "=" * 50)
        print("[SUCCESS] 所有測試通過!")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n[FAIL] 測試失敗: {e}")
    except Exception as e:
        print(f"\n[ERROR] 測試錯誤: {e}")
        import traceback
        traceback.print_exc()
