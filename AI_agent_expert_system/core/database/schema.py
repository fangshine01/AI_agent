"""
資料庫結構定義模組
定義所有資料表的 Schema
"""

import logging
from .connection import get_connection

logger = logging.getLogger(__name__)


def create_all_tables():
    """
    建立所有資料表
    包含主文件表與向量切片表
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 主文件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                doc_type TEXT NOT NULL,  -- 'Knowledge', 'Troubleshooting', 'Training'
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analysis_mode TEXT,      -- 'text_only', 'vision', 'auto'
                model_used TEXT          -- 使用的模型名稱
            )
        """)
        
        # 2. 向量切片表 (核心)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vec_chunks (
                chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,  -- 'chapter', 'step', 'field', 'section'
                source_title TEXT,           -- 章節/步驟/欄位標題
                text_content TEXT NOT NULL,  -- 實際被向量化的內容
                embedding BLOB,              -- 向量 (使用 vec0)
                keywords TEXT,               -- 關鍵字 (JSON 格式 or 逗號分隔)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)
        
        # 3. 確保 keywords 欄位存在 (Migration)
        _check_and_migrate_keywords(cursor)
        
        # 建立索引加速查詢
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vec_chunks_doc ON vec_chunks(doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vec_chunks_type ON vec_chunks(source_type)")
        
        conn.commit()
        logger.info("✅ 資料表結構建立完成")
        
    except Exception as e:
        logger.error(f"❌ 建立資料表失敗: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def _check_and_migrate_keywords(cursor):
    """檢查並新增 keywords 欄位"""
    try:
        cursor.execute("PRAGMA table_info(vec_chunks)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'keywords' not in columns:
            logger.info("⚠️ 偵測到舊版 schema, 正在新增 keywords 欄位...")
            cursor.execute("ALTER TABLE vec_chunks ADD COLUMN keywords TEXT")
    except Exception as e:
        logger.warning(f"Migration 檢查失敗: {e}")


def drop_all_tables():
    """
    刪除所有資料表 (慎用!)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DROP TABLE IF EXISTS vec_chunks")
        cursor.execute("DROP TABLE IF EXISTS documents")
        conn.commit()
        logger.warning("⚠️ 所有資料表已刪除")
    except Exception as e:
        logger.error(f"❌ 刪除資料表失敗: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # 測試建立資料表
    create_all_tables()
    print("✅ 資料表結構測試完成")
