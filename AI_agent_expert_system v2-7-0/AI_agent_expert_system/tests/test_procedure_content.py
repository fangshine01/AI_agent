# -*- coding: utf-8 -*-
import sys
import os
import sqlite3

# 加入專案路徑
sys.path.append('d:/Python/程式開發/AI agent/AI_agent_expert_system')
import config
from core.database.vector_ops import get_chunks_by_doc_id, get_chunk_content

def test_procedure_content():
    """測試 Procedure 文件內容檢索"""
    print("=" * 60)
    print("Testing Procedure Content Retrieval")
    print("=" * 60)
    
    # 1. 查詢所有 procedure_full 類型的切片
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT v.chunk_id, v.doc_id, v.source_type, v.source_title, 
               LENGTH(v.text_content) as content_length,
               d.filename, d.doc_type
        FROM vec_chunks v
        JOIN documents d ON v.doc_id = d.id
        WHERE v.source_type = 'procedure_full'
        LIMIT 5
    """)
    
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        print("[WARN] No procedure_full chunks found in database.")
        return
    
    print(f"\n[INFO] Found {len(rows)} procedure chunks:\n")
    
    for row in rows:
        chunk_id, doc_id, source_type, source_title, content_len, filename, doc_type = row
        print(f"Chunk ID: {chunk_id}")
        print(f"  Document: {filename} (Type: {doc_type})")
        print(f"  Title: {source_title}")
        print(f"  Content Length: {content_len} chars")
        
        # 測試 get_chunk_content
        content = get_chunk_content(chunk_id)
        if content:
            print(f"  [OK] get_chunk_content() returned {len(content)} chars")
            # 儲存到檔案以避免編碼問題
            test_file = f"test_output_chunk_{chunk_id}.md"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  [OK] Content saved to: {test_file}")
        else:
            print(f"  [FAIL] get_chunk_content() returned None")
        
        print("-" * 60)
    
    print("\n[INFO] Test completed. Check test_output_*.md files for content.")

if __name__ == "__main__":
    test_procedure_content()
