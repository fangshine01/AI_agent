"""
Debug Script - 分析搜尋問題
檢查資料庫內容並測試搜尋功能
"""

import sqlite3
from core.database import get_connection

def check_database():
    """檢查資料庫內容"""
    print("=" * 80)
    print("資料庫內容檢查")
    print("=" * 80)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. 檢查所有文件
    print("\n[1] 所有文件列表:")
    cursor.execute("SELECT id, filename, doc_type FROM documents")
    docs = cursor.fetchall()
    for doc in docs:
        print(f"  - ID: {doc[0]}, 檔名: {doc[1]}, 類型: {doc[2]}")
    
    # 2. 搜尋包含 N706 或 Mura 的文件
    print("\n[2] 搜尋 N706/Mura 相關文件:")
    cursor.execute("""
        SELECT id, filename FROM documents 
        WHERE filename LIKE '%N706%' 
           OR filename LIKE '%蝴蝶%' 
           OR filename LIKE '%Mura%'
    """)
    matches = cursor.fetchall()
    if matches:
        for match in matches:
            print(f"  [OK] 找到: ID={match[0]}, 檔名={match[1]}")
    else:
        print("  [X] 沒有找到相關文件")
    
    # 3. 檢查 vec_chunks 數量
    print("\n[3] 檢查向量切片數量:")
    cursor.execute("SELECT doc_id, COUNT(*) as chunk_count FROM vec_chunks GROUP BY doc_id")
    chunks_per_doc = cursor.fetchall()
    for row in chunks_per_doc:
        cursor.execute("SELECT filename FROM documents WHERE id = ?", (row[0],))
        filename = cursor.fetchone()[0]
        print(f"  - 文件 ID {row[0]} ({filename}): {row[1]} 個切片")
    
    # 4. 測試關鍵字搜尋: 使用者的查詢
    query = "N706 蝴蝶Mura.pptx  內容詳細解析"
    print(f"\n[4] 測試關鍵字搜尋: '{query}'")
    
    # 4a. 搜尋檔名
    print("\n  4a. 檔名搜尋:")
    cursor.execute("SELECT id, filename FROM documents WHERE filename LIKE ?", (f'%{query}%',))
    results = cursor.fetchall()
    print(f"     結果: {len(results)} 筆")
    for r in results:
        print(f"       - {r[1]}")
    
    # 4b. 搜尋內容
    print("\n  4b. 內容搜尋:")
    cursor.execute("""
        SELECT d.id, d.filename, COUNT(*) as match_count
        FROM vec_chunks v
        JOIN documents d ON v.doc_id = d.id
        WHERE v.text_content LIKE ?
        GROUP BY d.id
    """, (f'%{query}%',))
    results = cursor.fetchall()
    print(f"     結果: {len(results)} 筆")
    for r in results:
        print(f"       - {r[1]} (匹配 {r[2]} 個切片)")
    
    # 5. 分詞測試 - 搜尋單個關鍵字
    print("\n[5] 分詞搜尋測試:")
    keywords = ["N706", "蝴蝶", "Mura", "pptx"]
    for kw in keywords:
        print(f"\n  關鍵字: '{kw}'")
        
        # 檔名
        cursor.execute("SELECT COUNT(*) FROM documents WHERE filename LIKE ?", (f'%{kw}%',))
        filename_count = cursor.fetchone()[0]
        
        # 內容
        cursor.execute("""
            SELECT COUNT(DISTINCT d.id)
            FROM vec_chunks v
            JOIN documents d ON v.doc_id = d.id
            WHERE v.text_content LIKE ?
        """, (f'%{kw}%',))
        content_count = cursor.fetchone()[0]
        
        print(f"    - 檔名匹配: {filename_count} 筆")
        print(f"    - 內容匹配: {content_count} 筆")
        
        if filename_count > 0:
            cursor.execute("SELECT filename FROM documents WHERE filename LIKE ? LIMIT 3", (f'%{kw}%',))
            for row in cursor.fetchall():
                print(f"      → {row[0]}")
    
    # 6. 檢查 keywords 欄位
    print("\n[6] 檢查 keywords 欄位:")
    cursor.execute("""
        SELECT chunk_id, keywords, source_title
        FROM vec_chunks 
        WHERE keywords IS NOT NULL 
        LIMIT 5
    """)
    kw_samples = cursor.fetchall()
    if kw_samples:
        print(f"  有 keywords 的切片範例:")
        for row in kw_samples:
            print(f"    - Chunk {row[0]}: {row[1]} (來源: {row[2]})")
    else:
        print("  [!] 沒有切片有 keywords 資料")
    
    conn.close()
    print("\n" + "=" * 80)
    print("檢查完成")
    print("=" * 80)

if __name__ == "__main__":
    check_database()
