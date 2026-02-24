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
        
        # 4. 確保 documents 新欄位存在 (Migration v3.0)
        _check_and_migrate_documents(cursor)
        
        # 建立索引加速查詢
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash)")
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
        logger.warning(f"Migration (keywords) 檢查失敗: {e}")


def _check_and_migrate_documents(cursor):
    """檢查並新增 documents 新欄位 (v3.0)"""
    try:
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = {
            'file_hash': 'TEXT',
            'file_size': 'INTEGER',
            'category': 'TEXT',
            'tags': 'TEXT',
            'processing_time': 'REAL',
            'author': 'TEXT',
            'department': 'TEXT',
            'factory': 'TEXT',
            'language': 'TEXT DEFAULT "zh-TW"',
            'priority': 'INTEGER DEFAULT 0',
            'summary': 'TEXT',
            'key_points': 'TEXT',
            'status': 'TEXT DEFAULT "active"',
            # Troubleshooting 專用欄位
            'product_model': 'TEXT',      # 產品型號 (如 N706, N707)
            'defect_code': 'TEXT',        # 缺陷代碼 (如 Oven Pin, 蝴蝶Mura)
            'station': 'TEXT',            # 檢出站點 (如 PTST, A3LR, LCD2)
            'yield_loss': 'TEXT'          # 產量損失 (如 8%, 7.2%)
        }
        
        for col, dtype in new_columns.items():
            if col not in columns:
                logger.info(f"⚠️ 偵測到舊版 schema, 正在新增 {col} 欄位...")
                try:
                    cursor.execute(f"ALTER TABLE documents ADD COLUMN {col} {dtype}")
                except Exception as e:
                    logger.warning(f"無法新增欄位 {col}: {e}")
                    
    except Exception as e:
        logger.warning(f"Migration (documents) 檢查失敗: {e}")


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
