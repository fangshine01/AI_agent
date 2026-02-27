import sys
import os
import sqlite3

# 加入專案路徑
sys.path.append('d:/Python/程式開發/AI agent/AI_agent_expert_system')
import config
from core.database.vector_ops import get_chunks_by_doc_id, get_chunk_content

def test_get_chunk_content():
    print("Testing get_chunk_content...")
    
    # 1. Get a valid chunk ID first
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chunk_id FROM vec_chunks WHERE source_type='procedure_full' LIMIT 1")
    row = c.fetchone()
    conn.close()
    
    if not row:
        print("No procedure chunks found.")
        return

    chunk_id = row[0]
    print(f"Testing with Chunk ID: {chunk_id}")
    
    # 2. Call the new function
    content = get_chunk_content(chunk_id)
    
    if content:
        print(f"[OK] Success! Content length: {len(content)}")
        print(f"Preview: {content[:100]}...")
    else:
        print("[FAIL] Failed to get content.")

if __name__ == "__main__":
    test_get_chunk_content()
