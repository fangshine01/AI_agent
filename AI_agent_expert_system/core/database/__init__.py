"""
Database 模組
整合資料庫相關操作的統一介面
"""

# v3.0 新模組
from .connection import get_connection, init_database
from .document_ops import (
    create_document,
    get_document,
    get_all_documents,
    update_document,
    delete_document,
    get_document_stats
)
from .vector_ops import (
    save_chunk_embedding,
    search_by_vector,
    get_chunks_by_doc_id,
    delete_chunks_by_doc_id
)
from .token_ops import (
    init_token_db,
    log_token_usage,
    get_token_stats
)


# 為了相容性保留 get_knowledge_overview 的空實作
# 因為這功能在 v3 架構下已經改變，暫時回傳空值以免 UI 報錯
def get_knowledge_overview():
    return {
        'total': 0,
        'by_type': {},
        'recent_files': [],
        'all_keywords': []
    }


__all__ = [
    # v3.0 核心功能
    'get_connection',
    'init_database',
    'create_document',
    'get_document',
    'get_all_documents',
    'update_document',
    'delete_document',
    'get_document_stats',
    'save_chunk_embedding',
    'search_by_vector',
    'get_chunks_by_doc_id',
    'delete_chunks_by_doc_id',
    
    # Token 相關
    'init_token_db',
    'log_token_usage',
    'get_token_stats',
    
    # 相容性
    'get_knowledge_overview',
]
