# -*- coding: utf-8 -*-
"""
資料庫 Schema 升級腳本

將現有資料庫從基礎版本升級到增強版本,新增更多元數據欄位
"""

import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
# migrations -> database -> core -> 專案根目錄
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str) -> str:
    """計算檔案 hash 值"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return ""


def upgrade_documents_table(cursor: sqlite3.Cursor):
    """
    升級 documents 表,新增增強欄位
    
    新增欄位:
    - category: 二級分類
    - tags: 標籤 (JSON)
    - file_size: 檔案大小
    - file_hash: 檔案 hash
    - version: 版本號
    - last_modified: 最後修改時間
    - processing_time: 處理時間
    - author: 作者
    - department: 部門
    - factory: 工廠
    - language: 語言
    - priority: 優先級
    - summary: 摘要
    - key_points: 重點 (JSON)
    - status: 狀態
    - access_count: 訪問次數
    - last_accessed: 最後訪問時間
    """
    logger.info("開始升級 documents 表...")
    
    # 檢查現有欄位
    cursor.execute("PRAGMA table_info(documents)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # 定義需要新增的欄位
    new_columns = {
        'category': 'TEXT',
        'tags': 'TEXT',  # JSON 陣列
        'file_size': 'INTEGER',
        'file_hash': 'TEXT',
        'version': 'INTEGER DEFAULT 1',
        'last_modified': 'TIMESTAMP',
        'processing_time': 'REAL',
        'author': 'TEXT',
        'department': 'TEXT',
        'factory': 'TEXT',
        'language': 'TEXT DEFAULT "zh-TW"',
        'priority': 'INTEGER DEFAULT 0',
        'summary': 'TEXT',
        'key_points': 'TEXT',  # JSON 陣列
        'status': 'TEXT DEFAULT "active"',
        'access_count': 'INTEGER DEFAULT 0',
        'last_accessed': 'TIMESTAMP'
    }
    
    # 新增缺少的欄位
    added_count = 0
    for column_name, column_type in new_columns.items():
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE documents ADD COLUMN {column_name} {column_type}")
                logger.info(f"  ✓ 新增欄位: {column_name}")
                added_count += 1
            except Exception as e:
                logger.warning(f"  ✗ 新增欄位 {column_name} 失敗: {e}")
    
    logger.info(f"documents 表升級完成,新增了 {added_count} 個欄位")


def upgrade_vec_chunks_table(cursor: sqlite3.Cursor):
    """
    升級 vec_chunks 表,新增增強欄位
    
    新增欄位:
    - chunk_index: 在文件中的順序
    - context_before: 前文摘要
    - context_after: 後文摘要
    - content_quality: 內容品質分數
    - relevance_score: 相關性分數
    - access_count: 訪問次數
    - positive_feedback: 正面回饋次數
    """
    logger.info("開始升級 vec_chunks 表...")
    
    # 檢查現有欄位
    cursor.execute("PRAGMA table_info(vec_chunks)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # 定義需要新增的欄位
    new_columns = {
        'chunk_index': 'INTEGER',
        'context_before': 'TEXT',
        'context_after': 'TEXT',
        'content_quality': 'REAL',
        'relevance_score': 'REAL',
        'access_count': 'INTEGER DEFAULT 0',
        'positive_feedback': 'INTEGER DEFAULT 0'
    }
    
    # 新增缺少的欄位
    added_count = 0
    for column_name, column_type in new_columns.items():
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE vec_chunks ADD COLUMN {column_name} {column_type}")
                logger.info(f"  ✓ 新增欄位: {column_name}")
                added_count += 1
            except Exception as e:
                logger.warning(f"  ✗ 新增欄位 {column_name} 失敗: {e}")
    
    logger.info(f"vec_chunks 表升級完成,新增了 {added_count} 個欄位")


def create_new_tables(cursor: sqlite3.Cursor):
    """
    創建新的關聯表
    
    - document_relations: 文件之間的關聯
    - search_history: 搜尋歷史
    """
    logger.info("開始創建新的關聯表...")
    
    # 1. 文件關聯表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_doc_id INTEGER NOT NULL,
            target_doc_id INTEGER NOT NULL,
            relation_type TEXT NOT NULL,  -- 'references', 'updates', 'related', 'supersedes'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_doc_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (target_doc_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)
    logger.info("  ✓ 創建 document_relations 表")
    
    # 2. 搜尋歷史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            query_embedding BLOB,
            result_chunks TEXT,  -- JSON: 返回的 chunk_ids
            user_clicked_chunk_id INTEGER,
            feedback TEXT,  -- 'helpful', 'not_helpful', 'irrelevant'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("  ✓ 創建 search_history 表")


def create_indexes(cursor: sqlite3.Cursor):
    """創建索引以優化查詢效能"""
    logger.info("開始創建索引...")
    
    indexes = [
        # documents 表索引
        ("idx_documents_category", "documents", "category"),
        ("idx_documents_status", "documents", "status"),
        ("idx_documents_hash", "documents", "file_hash"),
        ("idx_documents_priority", "documents", "priority DESC"),
        ("idx_documents_access", "documents", "access_count DESC"),
        
        # vec_chunks 表索引
        ("idx_vec_chunks_quality", "vec_chunks", "content_quality DESC"),
        ("idx_vec_chunks_access", "vec_chunks", "access_count DESC"),
        
        # document_relations 表索引
        ("idx_relations_source", "document_relations", "source_doc_id"),
        ("idx_relations_target", "document_relations", "target_doc_id"),
        
        # search_history 表索引
        ("idx_search_history_query", "search_history", "query"),
    ]
    
    created_count = 0
    for index_name, table_name, column in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column})")
            logger.info(f"  ✓ 創建索引: {index_name}")
            created_count += 1
        except Exception as e:
            logger.warning(f"  ✗ 創建索引 {index_name} 失敗: {e}")
    
    logger.info(f"索引創建完成,共創建 {created_count} 個索引")


def upgrade_database(db_path: str = None):
    """
    執行資料庫升級
    
    Args:
        db_path: 資料庫路徑,如果為 None 則使用預設路徑
    """
    if db_path is None:
        # 使用統一的 v2 資料庫路徑
        db_path = str(project_root / "backend" / "data" / "documents" / "knowledge_v2.db")
    
    logger.info("=" * 60)
    logger.info("開始資料庫 Schema 升級")
    logger.info(f"資料庫路徑: {db_path}")
    logger.info("=" * 60)
    
    # 備份資料庫
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"✓ 資料庫已備份至: {backup_path}")
    except Exception as e:
        logger.warning(f"✗ 備份失敗: {e}")
    
    # 執行升級
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 升級 documents 表
        upgrade_documents_table(cursor)
        
        # 2. 升級 vec_chunks 表
        upgrade_vec_chunks_table(cursor)
        
        # 3. 創建新表
        create_new_tables(cursor)
        
        # 4. 創建索引
        create_indexes(cursor)
        
        # 提交變更
        conn.commit()
        
        logger.info("=" * 60)
        logger.info("✓ 資料庫升級完成!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ 資料庫升級失敗: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def check_schema_version(db_path: str = None) -> dict:
    """
    檢查資料庫 Schema 版本
    
    Returns:
        包含各表欄位資訊的字典
    """
    if db_path is None:
        # 使用統一的 v2 資料庫路徑
        db_path = str(project_root / "backend" / "data" / "documents" / "knowledge_v2.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    schema_info = {}
    
    # 檢查各表
    for table in ['documents', 'vec_chunks', 'document_relations', 'search_history']:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone():
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            schema_info[table] = columns
        else:
            schema_info[table] = None
    
    conn.close()
    return schema_info


if __name__ == "__main__":
    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 檢查當前 Schema
    print("\n檢查當前 Schema:")
    schema = check_schema_version()
    for table, columns in schema.items():
        if columns:
            print(f"\n{table} 表欄位 ({len(columns)} 個):")
            for col in columns:
                print(f"  - {col}")
        else:
            print(f"\n{table} 表不存在")
    
    # 詢問是否執行升級
    print("\n" + "=" * 60)
    response = input("是否執行資料庫升級? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        upgrade_database()
    else:
        print("取消升級")
