"""
初始化全新資料庫 (v2.0)
使用方式: python scripts/init_db.py
"""
import sqlite3
import os
import sys

# 加入專案根目錄到 Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def init_knowledge_db(db_path: str):
    """初始化知識庫資料庫"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # documents 表 (包含新欄位)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            doc_type TEXT,
            file_path TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            parent_doc_id INTEGER DEFAULT NULL,
            source_type TEXT DEFAULT 'manual',
            raw_file_path TEXT DEFAULT NULL,
            -- v2.0 新增欄位
            filename TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            analysis_mode TEXT,
            model_used TEXT,
            file_hash TEXT,
            file_size INTEGER,
            category TEXT,
            tags TEXT,
            processing_time REAL,
            author TEXT,
            department TEXT,
            factory TEXT,
            language TEXT DEFAULT 'zh-TW',
            priority INTEGER DEFAULT 0,
            summary TEXT,
            key_points TEXT,
            status TEXT DEFAULT 'active',
            product_model TEXT,
            defect_code TEXT,
            station TEXT,
            yield_loss TEXT
        )
    """)

    # chunks 表 (向量儲存)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER,
            text_content TEXT,
            source_title TEXT,
            embedding BLOB,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)

    # vec_chunks 表 (相容現有系統)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vec_chunks (
            chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            source_title TEXT,
            text_content TEXT NOT NULL,
            embedding BLOB,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)

    # document_keywords 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER,
            category TEXT NOT NULL,
            keyword TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
            UNIQUE(doc_id, category, keyword)
        )
    """)

    # document_raw_data 表
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

    # troubleshooting_metadata 表
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

    # procedure_metadata 表
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

    # document_versions 表
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

    # search_analytics 表
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

    # chunk_metadata 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunk_metadata (
            chunk_id INTEGER PRIMARY KEY,
            metadata JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chunk_id) REFERENCES vec_chunks(chunk_id) ON DELETE CASCADE
        )
    """)

    # 建立索引
    indexes = [
        ("idx_documents_type", "documents", "doc_type"),
        ("idx_documents_hash", "documents", "file_hash"),
        ("idx_vec_chunks_doc", "vec_chunks", "doc_id"),
        ("idx_vec_chunks_type", "vec_chunks", "source_type"),
        ("idx_raw_data_doc_id", "document_raw_data", "doc_id"),
        ("idx_keywords_doc_id", "document_keywords", "doc_id"),
        ("idx_keywords_category", "document_keywords", "category"),
        ("idx_keywords_keyword", "document_keywords", "keyword"),
        ("idx_ts_product", "troubleshooting_metadata", "product_model"),
        ("idx_ts_defect", "troubleshooting_metadata", "defect_code"),
        ("idx_ts_station", "troubleshooting_metadata", "station"),
        ("idx_ts_composite", "troubleshooting_metadata", "product_model, defect_code"),
    ]

    for idx_name, table, columns in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
        except Exception as e:
            print(f"  ⚠️ 索引 {idx_name} 建立失敗: {e}")

    conn.commit()
    conn.close()
    print(f"✅ 知識庫資料庫初始化完成: {db_path}")


def init_token_db(db_path: str):
    """初始化 Token 記錄資料庫"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_name TEXT,
            operation TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ Token 資料庫初始化完成: {db_path}")


if __name__ == "__main__":
    # 確定路徑
    backend_data_dir = os.path.join(PROJECT_ROOT, "backend", "data", "documents")
    os.makedirs(backend_data_dir, exist_ok=True)

    knowledge_db = os.path.join(backend_data_dir, "knowledge_v2.db")
    token_db = os.path.join(backend_data_dir, "tokenrecord_v2.db")

    print("=" * 50)
    print("AI Expert System - 資料庫初始化")
    print("=" * 50)

    init_knowledge_db(knowledge_db)
    init_token_db(token_db)

    print("\n✅ 所有資料庫初始化完成!")
    print(f"  知識庫: {knowledge_db}")
    print(f"  Token:  {token_db}")
