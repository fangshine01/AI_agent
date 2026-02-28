"""
資料庫自動初始化模組 (v2.7.0)
每次啟動時檢查 .db 是否存在，若不存在則自動建立
確保程式在不同主機首次使用時能自動建好資料庫

架構: 將 DDL 依領域拆分為純資料定義 (dict)，
      init / upgrade 函式只負責執行，不重複定義 DDL。
"""

import os
import sqlite3
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


# =====================================================================
# DDL 定義區 — 所有 CREATE TABLE / INDEX 的唯一來源 (Single Source of Truth)
# =====================================================================

# ---- 核心文件 ----
_DOCUMENTS_DDL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, content TEXT, doc_type TEXT, file_path TEXT, metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    parent_doc_id INTEGER DEFAULT NULL,
    source_type TEXT DEFAULT 'manual', raw_file_path TEXT DEFAULT NULL,
    filename TEXT, upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_mode TEXT, model_used TEXT, file_hash TEXT, file_size INTEGER,
    category TEXT, tags TEXT, processing_time REAL,
    author TEXT, department TEXT, factory TEXT,
    language TEXT DEFAULT 'zh-TW', priority INTEGER DEFAULT 0,
    summary TEXT, key_points TEXT, status TEXT DEFAULT 'active',
    product_model TEXT, defect_code TEXT, station TEXT, yield_loss TEXT
)
"""

_VEC_CHUNKS_DDL = """
CREATE TABLE IF NOT EXISTS vec_chunks (
    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL, source_type TEXT NOT NULL,
    source_title TEXT, text_content TEXT NOT NULL,
    embedding BLOB, keywords TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
)
"""

_KEYWORDS_DDL = """
CREATE TABLE IF NOT EXISTS document_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER, category TEXT NOT NULL, keyword TEXT NOT NULL,
    weight REAL DEFAULT 1.0, confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, category, keyword)
)
"""

_RAW_DATA_DDL = """
CREATE TABLE IF NOT EXISTS document_raw_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER UNIQUE NOT NULL, raw_content TEXT NOT NULL,
    content_type TEXT DEFAULT 'text', encoding TEXT DEFAULT 'utf-8',
    compressed BOOLEAN DEFAULT 0, file_extension TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
)
"""

# ---- 文件類型專用元資料 ----
_TROUBLESHOOTING_DDL = """
CREATE TABLE IF NOT EXISTS troubleshooting_metadata (
    doc_id INTEGER PRIMARY KEY,
    product_model TEXT, defect_code TEXT, station TEXT, yield_loss TEXT,
    severity TEXT, occurrence_date DATE, resolution_date DATE,
    responsible_dept TEXT, status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
)
"""

_PROCEDURE_DDL = """
CREATE TABLE IF NOT EXISTS procedure_metadata (
    doc_id INTEGER PRIMARY KEY,
    procedure_type TEXT, applicable_station TEXT, applicable_product TEXT,
    revision TEXT, approval_status TEXT, approved_by TEXT,
    approved_date DATE, effective_date DATE, expiry_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
)
"""

# ---- 分析 / 版本 ----
_SEARCH_ANALYTICS_DDL = """
CREATE TABLE IF NOT EXISTS search_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL, intent TEXT, strategy TEXT,
    result_count INTEGER, search_time_ms REAL,
    top_chunk_id INTEGER, user_clicked_chunk_id INTEGER,
    user_rating INTEGER, feedback TEXT,
    session_id TEXT, user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_VERSIONS_DDL = """
CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL, version INTEGER NOT NULL,
    change_type TEXT NOT NULL, changed_by TEXT, change_description TEXT,
    snapshot JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, version)
)
"""

_CHUNK_METADATA_DDL = """
CREATE TABLE IF NOT EXISTS chunk_metadata (
    chunk_id INTEGER PRIMARY KEY,
    metadata JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES vec_chunks(chunk_id) ON DELETE CASCADE
)
"""

# ---- Token 用量 (知識庫備份 + Token DB 主表共用) ----
_TOKEN_USAGE_DDL = """
CREATE TABLE IF NOT EXISTS token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_name TEXT, operation TEXT,
    prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER
)
"""

# ---- Chat / Session (v2.2.0+) ----
_CHAT_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL, session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL, model_used TEXT,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_SESSIONS_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL, user_id TEXT NOT NULL,
    title TEXT DEFAULT '新對話', model_used TEXT,
    message_count INTEGER DEFAULT 0, total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# ---- 索引定義 (name, table, columns) ----
_KNOWLEDGE_INDEXES: List[Tuple[str, str, str]] = [
    # documents
    ("idx_documents_type", "documents", "doc_type"),
    ("idx_documents_hash", "documents", "file_hash"),
    ("idx_documents_parent", "documents", "parent_doc_id"),
    ("idx_documents_status", "documents", "status"),
    # vec_chunks
    ("idx_vec_chunks_doc", "vec_chunks", "doc_id"),
    ("idx_vec_chunks_type", "vec_chunks", "source_type"),
    # raw_data / keywords
    ("idx_raw_data_doc_id", "document_raw_data", "doc_id"),
    ("idx_keywords_doc_id", "document_keywords", "doc_id"),
    ("idx_keywords_category", "document_keywords", "category"),
    ("idx_keywords_keyword", "document_keywords", "keyword"),
    # troubleshooting
    ("idx_ts_product", "troubleshooting_metadata", "product_model"),
    ("idx_ts_defect", "troubleshooting_metadata", "defect_code"),
    ("idx_ts_station", "troubleshooting_metadata", "station"),
    # token_usage (backup)
    ("idx_token_timestamp", "token_usage", "timestamp"),
    ("idx_token_operation", "token_usage", "operation"),
    # analytics
    ("idx_search_query", "search_analytics", "query"),
    # chat_history
    ("idx_chat_history_user", "chat_history", "user_id"),
    ("idx_chat_history_session", "chat_history", "session_id"),
    ("idx_chat_history_created", "chat_history", "created_at"),
    ("idx_chat_history_user_session", "chat_history", "user_id, session_id"),
    # sessions
    ("idx_sessions_user", "sessions", "user_id"),
    ("idx_sessions_updated", "sessions", "updated_at"),
]

_TOKEN_INDEXES: List[Tuple[str, str, str]] = [
    ("idx_token_timestamp", "token_usage", "timestamp"),
    ("idx_token_operation", "token_usage", "operation"),
    ("idx_token_file", "token_usage", "file_name"),
]


# =====================================================================
# 執行層 — 只負責連線管理與呼叫上方定義
# =====================================================================

def _enable_wal_mode(conn: sqlite3.Connection, db_label: str):
    """啟用 WAL 模式以支援高併發讀寫"""
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA cache_size=-64000;")
        logger.info(f"✅ [{db_label}] WAL 模式已啟用")
    except Exception as e:
        logger.error(f"❌ [{db_label}] WAL 模式啟用失敗: {e}")


def _execute_ddl(
    cursor: sqlite3.Cursor,
    ddl_list: List[str],
    indexes: List[Tuple[str, str, str]],
):
    """依序執行 DDL 與 CREATE INDEX"""
    for ddl in ddl_list:
        cursor.execute(ddl)
    for idx_name, table, columns in indexes:
        try:
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})"
            )
        except Exception:
            pass  # 索引已存在或表不匹配時忽略


# ---- 公開 API ----

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
            _upgrade_existing_db(path, label)


def _upgrade_existing_db(db_path: str, label: str):
    """升級既有資料庫：啟用 WAL + 確保缺失的表/索引已建立"""
    try:
        conn = sqlite3.connect(db_path)
        _enable_wal_mode(conn, label)
        # 只補建 chat / session 相關表（最常見的升級路徑）
        _execute_ddl(
            conn.cursor(),
            [_CHAT_HISTORY_DDL, _SESSIONS_DDL],
            [i for i in _KNOWLEDGE_INDEXES if "chat_history" in i[1] or "sessions" in i[1]],
        )
        conn.commit()
        conn.close()
        logger.info(f"✅ [{label}] Schema 升級檢查完成")
    except Exception as e:
        logger.warning(f"⚠️ [{label}] 升級檢查失敗: {e}")


def _init_knowledge_db(db_path: str):
    """初始化知識庫資料庫（建立所有必要的資料表與索引）"""
    conn = sqlite3.connect(db_path)
    _execute_ddl(
        conn.cursor(),
        [
            # 核心文件
            _DOCUMENTS_DDL, _VEC_CHUNKS_DDL, _KEYWORDS_DDL, _RAW_DATA_DDL,
            # 文件類型專用
            _TROUBLESHOOTING_DDL, _PROCEDURE_DDL,
            # 分析 / 版本
            _TOKEN_USAGE_DDL, _SEARCH_ANALYTICS_DDL, _VERSIONS_DDL, _CHUNK_METADATA_DDL,
            # Chat / Session
            _CHAT_HISTORY_DDL, _SESSIONS_DDL,
        ],
        _KNOWLEDGE_INDEXES,
    )
    conn.commit()
    _enable_wal_mode(conn, "知識庫")
    conn.close()


def _init_token_db(db_path: str):
    """初始化 Token 記錄資料庫"""
    conn = sqlite3.connect(db_path)
    _execute_ddl(conn.cursor(), [_TOKEN_USAGE_DDL], _TOKEN_INDEXES)
    conn.commit()
    _enable_wal_mode(conn, "Token 記錄")
    conn.close()
