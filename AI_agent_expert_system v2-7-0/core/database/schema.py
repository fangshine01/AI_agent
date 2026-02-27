"""
資料庫結構定義模組
定義所有資料表的 Schema (v5.0 - 完整架構)
"""

import logging
from .connection import get_connection

logger = logging.getLogger(__name__)


def create_all_tables():
    """
    建立所有資料表
    包含主文件表、向量切片表、以及 v5.0 新增的擴充表
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # ========== 核心資料表 ==========
        
        # 1. 主文件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                doc_type TEXT NOT NULL,  -- 'Knowledge', 'Troubleshooting', 'Training', 'Procedure'
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
                source_type TEXT NOT NULL,  -- 'chapter', 'step', 'field', 'section', 'troubleshooting_full'
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
        
        # ========== v5.0 新增資料表 ==========
        
        # 5. 原始文字內容表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER UNIQUE NOT NULL,
                raw_content TEXT NOT NULL,
                content_type TEXT DEFAULT 'text',
                encoding TEXT DEFAULT 'utf-8',
                compressed BOOLEAN DEFAULT 0,
                file_extension TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)
        
        # 6. 關鍵字關聯表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                keyword TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE(doc_id, category, keyword)
            )
        """)
        
        # 7. Troubleshooting 專屬 metadata 表 (正規化拆分)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS troubleshooting_metadata (
                doc_id INTEGER PRIMARY KEY,
                product_model TEXT,
                defect_code TEXT,
                station TEXT,
                yield_loss TEXT,
                severity TEXT,
                occurrence_date DATE,
                resolution_date DATE,
                responsible_dept TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)
        
        # 8. Procedure 專屬 metadata 表 (正規化拆分)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedure_metadata (
                doc_id INTEGER PRIMARY KEY,
                procedure_type TEXT,
                applicable_station TEXT,
                applicable_product TEXT,
                revision TEXT,
                approval_status TEXT,
                approved_by TEXT,
                approved_date DATE,
                effective_date DATE,
                expiry_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)
        
        # 9. 版本管理表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                change_type TEXT NOT NULL,
                changed_by TEXT,
                change_description TEXT,
                snapshot JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE(doc_id, version)
            )
        """)
        
        # 10. 搜尋分析表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                intent TEXT,
                strategy TEXT,
                result_count INTEGER,
                search_time_ms REAL,
                top_chunk_id INTEGER,
                user_clicked_chunk_id INTEGER,
                user_rating INTEGER,
                feedback TEXT,
                session_id TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 11. Chunk 結構化 metadata 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunk_metadata (
                chunk_id INTEGER PRIMARY KEY,
                metadata JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chunk_id) REFERENCES vec_chunks(chunk_id) ON DELETE CASCADE
            )
        """)
        
        # ========== 建立索引 ==========
        _create_all_indexes(cursor)
        
        conn.commit()
        logger.info("✅ 資料表結構建立完成 (v5.0)")
        
    except Exception as e:
        logger.error(f"❌ 建立資料表失敗: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def _create_all_indexes(cursor):
    """建立所有索引"""
    indexes = [
        # documents 表索引
        ("idx_documents_type", "documents", "doc_type"),
        ("idx_documents_hash", "documents", "file_hash"),
        
        # vec_chunks 表索引
        ("idx_vec_chunks_doc", "vec_chunks", "doc_id"),
        ("idx_vec_chunks_type", "vec_chunks", "source_type"),
        
        # document_raw_data 表索引
        ("idx_raw_data_doc_id", "document_raw_data", "doc_id"),
        
        # document_keywords 表索引
        ("idx_keywords_doc_id", "document_keywords", "doc_id"),
        ("idx_keywords_category", "document_keywords", "category"),
        ("idx_keywords_keyword", "document_keywords", "keyword"),
        ("idx_keywords_composite", "document_keywords", "category, keyword"),
        
        # troubleshooting_metadata 表索引
        ("idx_ts_product", "troubleshooting_metadata", "product_model"),
        ("idx_ts_defect", "troubleshooting_metadata", "defect_code"),
        ("idx_ts_station", "troubleshooting_metadata", "station"),
        ("idx_ts_composite", "troubleshooting_metadata", "product_model, defect_code"),
        
        # procedure_metadata 表索引
        ("idx_proc_type", "procedure_metadata", "procedure_type"),
        ("idx_proc_station", "procedure_metadata", "applicable_station"),
        ("idx_proc_status", "procedure_metadata", "approval_status"),
        
        # document_versions 表索引
        ("idx_versions_doc_id", "document_versions", "doc_id"),
        ("idx_versions_created", "document_versions", "created_at"),
        
        # search_analytics 表索引
        ("idx_analytics_query", "search_analytics", "query"),
        ("idx_analytics_intent", "search_analytics", "intent"),
        ("idx_analytics_created", "search_analytics", "created_at"),
        ("idx_analytics_session", "search_analytics", "session_id"),
    ]
    
    for idx_name, table, columns in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
        except Exception as e:
            logger.warning(f"建立索引 {idx_name} 失敗: {e}")


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


def migrate_existing_data(cursor):
    """
    遷移現有 documents 表中的 Troubleshooting 專屬欄位到新表
    """
    try:
        # 遷移 Troubleshooting metadata
        cursor.execute("""
            INSERT OR IGNORE INTO troubleshooting_metadata 
                (doc_id, product_model, defect_code, station, yield_loss)
            SELECT id, product_model, defect_code, station, yield_loss
            FROM documents
            WHERE doc_type = 'Troubleshooting' 
              AND (product_model IS NOT NULL OR defect_code IS NOT NULL)
        """)
        ts_count = cursor.rowcount
        logger.info(f"✅ 已遷移 {ts_count} 筆 Troubleshooting metadata")
        
    except Exception as e:
        logger.warning(f"遷移資料失敗 (可能表不存在或已遷移): {e}")


def drop_all_tables():
    """
    刪除所有資料表 (慎用!)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # v5.0 新增的表
        cursor.execute("DROP TABLE IF EXISTS chunk_metadata")
        cursor.execute("DROP TABLE IF EXISTS search_analytics")
        cursor.execute("DROP TABLE IF EXISTS document_versions")
        cursor.execute("DROP TABLE IF EXISTS procedure_metadata")
        cursor.execute("DROP TABLE IF EXISTS troubleshooting_metadata")
        cursor.execute("DROP TABLE IF EXISTS document_keywords")
        cursor.execute("DROP TABLE IF EXISTS document_raw_data")
        # 核心表
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
