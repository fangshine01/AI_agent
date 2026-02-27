"""
資料庫自動初始化模組
每次啟動時檢查 .db 是否存在，若不存在則自動建立
確保程式在不同主機首次使用時能自動建好資料庫

v2.2.0 變更:
- 啟用 WAL Mode (Write-Ahead Logging) 以支援高併發
- 新增 chat_history 對話歷史表
- 新增 sessions 使用者 Session 管理表
"""

import os
import sqlite3
import logging

logger = logging.getLogger(__name__)


def _enable_wal_mode(conn: sqlite3.Connection, db_label: str):
    """
    啟用 WAL 模式以支援高併發讀寫 (50~100 人同時在線)
    WAL 允許多個讀取同時進行，寫入不阻塞讀取
    """
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")  # 等待 5 秒避免 locked
        conn.execute("PRAGMA cache_size=-64000;")   # 64MB cache
        logger.info(f"✅ [{db_label}] WAL 模式已啟用")
    except Exception as e:
        logger.error(f"❌ [{db_label}] WAL 模式啟用失敗: {e}")


def ensure_databases(db_path: str, token_db_path: str):
    """
    檢查並自動建立資料庫（首次使用時）

    Args:
        db_path: 知識庫 DB 路徑
        token_db_path: Token 記錄 DB 路徑
    """
    for path, init_func, label in [
        (db_path, _init_knowledge_db, "知識庫"),
        (token_db_path, _init_token_db, "Token 記錄"),
    ]:
        db_dir = os.path.dirname(path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        if not os.path.exists(path):
            logger.info(f"📦 {label}資料庫不存在，正在建立: {path}")
            init_func(path)
            logger.info(f"✅ {label}資料庫已建立: {path}")
        else:
            logger.info(f"✅ {label}資料庫已存在: {path}")
            # 確保既有資料庫也啟用 WAL 模式並更新 Schema
            _upgrade_existing_db(path, label)


def _upgrade_existing_db(db_path: str, label: str):
    """
    升級既有資料庫：啟用 WAL 模式 + 新增缺失的表
    確保從舊版升級到 v2.2.0 時不遺失功能
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 啟用 WAL 模式
        _enable_wal_mode(conn, label)

        # 檢查並新增 chat_history 表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                model_used TEXT,
                tokens_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user ON chat_history(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_created ON chat_history(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user_session ON chat_history(user_id, session_id)")

        # 檢查並新增 sessions 表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT DEFAULT '新對話',
                model_used TEXT,
                message_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at)")

        conn.commit()
        conn.close()
        logger.info(f"✅ [{label}] Schema 升級檢查完成")
    except Exception as e:
        logger.warning(f"⚠️ [{label}] 升級檢查失敗: {e}")


def _init_knowledge_db(db_path: str):
    """初始化知識庫資料庫（建立所有必要的資料表與索引）"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ---- documents 主表 ----
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

    # ---- vec_chunks 向量存儲表 ----
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

    # ---- document_keywords 關鍵字表 ----
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

    # ---- document_raw_data 原始內容表 ----
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

    # ---- troubleshooting_metadata 異常專用表 ----
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

    # ---- procedure_metadata SOP 專用表 ----
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

    # ---- token_usage 表（備份用，主要在 token DB）----
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

    # ---- search_analytics 搜尋分析表 ----
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

    # ---- document_versions 版本記錄表 ----
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

    # ---- chunk_metadata 分塊元資料表 ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunk_metadata (
            chunk_id INTEGER PRIMARY KEY,
            metadata JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chunk_id) REFERENCES vec_chunks(chunk_id) ON DELETE CASCADE
        )
    """)

    # ---- 建立索引 ----
    indexes = [
        ("idx_documents_type", "documents", "doc_type"),
        ("idx_documents_hash", "documents", "file_hash"),
        ("idx_documents_parent", "documents", "parent_doc_id"),
        ("idx_documents_status", "documents", "status"),
        ("idx_vec_chunks_doc", "vec_chunks", "doc_id"),
        ("idx_vec_chunks_type", "vec_chunks", "source_type"),
        ("idx_raw_data_doc_id", "document_raw_data", "doc_id"),
        ("idx_keywords_doc_id", "document_keywords", "doc_id"),
        ("idx_keywords_category", "document_keywords", "category"),
        ("idx_keywords_keyword", "document_keywords", "keyword"),
        ("idx_ts_product", "troubleshooting_metadata", "product_model"),
        ("idx_ts_defect", "troubleshooting_metadata", "defect_code"),
        ("idx_ts_station", "troubleshooting_metadata", "station"),
        ("idx_token_timestamp", "token_usage", "timestamp"),
        ("idx_token_operation", "token_usage", "operation"),
        ("idx_search_query", "search_analytics", "query"),
    ]

    for idx_name, table, columns in indexes:
        try:
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})"
            )
        except Exception:
            pass  # 索引已存在或表不匹配時忽略

    # ---- chat_history 對話歷史表 (v2.2.0 新增) ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            model_used TEXT,
            tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # chat_history 索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user ON chat_history(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_created ON chat_history(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user_session ON chat_history(user_id, session_id)")

    # ---- sessions 使用者 Session 管理表 (v2.2.0 新增) ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            title TEXT DEFAULT '新對話',
            model_used TEXT,
            message_count INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # sessions 索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at)")

    conn.commit()

    # 啟用 WAL 模式 (必須在 commit 之後)
    _enable_wal_mode(conn, "知識庫")

    conn.close()


def _init_token_db(db_path: str):
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

    # 建立索引
    try:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_token_timestamp ON token_usage(timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_token_operation ON token_usage(operation)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_token_file ON token_usage(file_name)"
        )
    except Exception:
        pass

    conn.commit()

    # 啟用 WAL 模式 (必須在 commit 之後)
    _enable_wal_mode(conn, "Token 記錄")

    conn.close()
