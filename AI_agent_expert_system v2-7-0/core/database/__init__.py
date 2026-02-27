"""
Database 模組
整合資料庫相關操作的統一介面 (v5.0)
"""

# v3.0 核心模組
from .connection import get_connection, init_database
from .document_ops import (
    create_document,
    get_document,
    get_all_documents,
    update_document,
    delete_document,
    get_document_stats,
    # v4.0 增強版函數
    create_document_enhanced,
    get_document_by_hash,
    increment_access_count,
    log_search_history,
    get_chunks_by_doc_id as get_chunks_by_doc_id_ops
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

# v5.0 新增模組
from .keyword_ops import (
    save_document_keywords,
    get_document_keywords,
    search_by_keywords,
    delete_document_keywords,
    get_keywords_by_category
)
from .metadata_ops import (
    # Troubleshooting metadata
    save_troubleshooting_metadata,
    get_troubleshooting_metadata,
    search_troubleshooting,
    # Procedure metadata
    save_procedure_metadata,
    get_procedure_metadata,
    # Document versions
    create_version,
    get_document_versions,
    # Search analytics
    log_search_analytics,
    update_search_feedback,
    get_search_stats,
    # Chunk metadata
    save_chunk_metadata,
    get_chunk_metadata
)
from .raw_data_ops import (
    save_raw_data,
    get_raw_data,
    get_raw_data_info,
    delete_raw_data,
    get_all_raw_data,
    has_raw_data
)
from .retrieval_ops import (
    find_document_by_metadata
)


# 為了相容性保留 get_knowledge_overview 的空實作
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
    
    # v4.0 增強版函數
    'create_document_enhanced',
    'get_document_by_hash',
    'increment_access_count',
    'log_search_history',
    
    # Token 相關
    'init_token_db',
    'log_token_usage',
    'get_token_stats',
    
    # v5.0 關鍵字操作
    'save_document_keywords',
    'get_document_keywords',
    'search_by_keywords',
    'delete_document_keywords',
    'get_keywords_by_category',
    
    # v5.0 Metadata 操作
    'save_troubleshooting_metadata',
    'get_troubleshooting_metadata',
    'search_troubleshooting',
    'save_procedure_metadata',
    'get_procedure_metadata',
    'create_version',
    'get_document_versions',
    'log_search_analytics',
    'update_search_feedback',
    'get_search_stats',
    'save_chunk_metadata',
    'get_chunk_metadata',
    
    # v5.0 Raw data 操作
    'save_raw_data',
    'get_raw_data',
    'get_raw_data_info',
    'delete_raw_data',
    'get_all_raw_data',
    'has_raw_data',
    
    # v5.0 Retrieval 操作
    'find_document_by_metadata',
    
    # 相容性
    'get_knowledge_overview',
]
