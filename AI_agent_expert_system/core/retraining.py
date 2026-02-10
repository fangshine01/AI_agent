"""
重新訓練模組 (v5.0)
從 document_raw_data 表讀取原始內容,重新執行解析與向量化
"""

import os
import logging
from typing import Optional, Dict, List, Callable

from core import database
from core.parsers import TroubleshootingParser, TrainingParser, KnowledgeParser, ProcedureParser
from core import ai_core

logger = logging.getLogger(__name__)


def retrain_all_documents(
    doc_type: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
    text_model: str = None,
    vision_model: str = None
) -> Dict:
    """
    從 raw_content 重新訓練所有文件
    
    Args:
        doc_type: 限定文件類型 (None 表示全部重新訓練)
        progress_callback: 進度回調函數
        text_model: 文字模型
        vision_model: 視覺模型
    
    Returns:
        Dict: {'total': int, 'success': int, 'skipped': int, 'errors': [...]}
    """
    logger.info(f"開始重新訓練 (doc_type: {doc_type or 'ALL'})...")
    
    # 取得所有有 raw_data 的文件
    raw_docs = database.get_all_raw_data(doc_type=doc_type)
    
    if not raw_docs:
        logger.warning("沒有找到可重新訓練的文件 (無 raw_data)")
        return {'total': 0, 'success': 0, 'skipped': 0, 'errors': []}
    
    results = {
        'total': len(raw_docs),
        'success': 0,
        'skipped': 0,
        'errors': []
    }
    
    for i, doc in enumerate(raw_docs):
        doc_id = doc['doc_id']
        filename = doc['filename']
        raw_content = doc['raw_content']
        current_doc_type = doc['doc_type']
        
        if progress_callback:
            progress_callback(f"重新訓練 ({i+1}/{len(raw_docs)}): {filename}")
        
        logger.info(f"重新訓練: {filename} (doc_id: {doc_id}, type: {current_doc_type})")
        
        if not raw_content:
            logger.warning(f"文件 {filename} 無原始內容，跳過")
            results['skipped'] += 1
            continue
        
        try:
            result = retrain_single_document(
                doc_id=doc_id,
                raw_content=raw_content,
                doc_type=current_doc_type,
                filename=filename,
                text_model=text_model,
                vision_model=vision_model
            )
            
            if result['success']:
                results['success'] += 1
            else:
                results['errors'].append({
                    'doc_id': doc_id,
                    'filename': filename,
                    'error': result.get('message', 'Unknown error')
                })
                
        except Exception as e:
            logger.error(f"重新訓練失敗: {filename}, 錯誤: {e}")
            results['errors'].append({
                'doc_id': doc_id,
                'filename': filename,
                'error': str(e)
            })
    
    logger.info(f"✅ 重新訓練完成: {results['success']}/{results['total']} 成功, "
                f"{results['skipped']} 跳過, {len(results['errors'])} 失敗")
    
    return results


def retrain_single_document(
    doc_id: int,
    raw_content: str,
    doc_type: str,
    filename: str = "Unknown",
    text_model: str = None,
    vision_model: str = None
) -> Dict:
    """
    重新訓練單一文件
    
    Args:
        doc_id: 文件 ID
        raw_content: 原始文字內容
        doc_type: 文件類型
        filename: 檔案名稱
        text_model: 文字模型
        vision_model: 視覺模型
    
    Returns:
        Dict: {'success': bool, 'chunks': int, 'message': str}
    """
    try:
        # 1. 刪除舊的 chunks 和 embeddings
        deleted = database.delete_chunks_by_doc_id(doc_id)
        logger.info(f"已刪除 {deleted} 個舊切片 (doc_id: {doc_id})")
        
        # 2. 建立 AI Core 包裝器
        class AICoreWrapper:
            def __init__(self, fname):
                self.filename = fname
            
            def analyze_slide(self, prompt, api_mode="text_only"):
                result, usage = ai_core.analyze_slide(
                    text=prompt,
                    image_paths=None,
                    api_mode=api_mode,
                    text_model=text_model,
                    vision_model=vision_model
                )
                database.log_token_usage(
                    file_name=self.filename,
                    operation='retrain_parse',
                    usage=usage
                )
                return result
        
        ai_wrapper = AICoreWrapper(filename)
        
        # 3. 選擇並執行解析器
        chunks = []
        if doc_type == 'Troubleshooting':
            parser = TroubleshootingParser(ai_wrapper)
            chunks = parser.parse(raw_content)
        elif doc_type == 'Training':
            parser = TrainingParser(ai_wrapper)
            chunks = parser.parse(raw_content)
        elif doc_type in ('Procedure', 'procedure'):
            parser = ProcedureParser(ai_wrapper)
            chunks = parser.parse(raw_content)
        elif doc_type == 'Knowledge':
            from core.ingestion_v3 import _extract_chapters
            chapters = _extract_chapters(raw_content)
            parser = KnowledgeParser(ai_wrapper)
            chunks = parser.parse(chapters)
        
        logger.info(f"解析完成,產生 {len(chunks)} 個切片")
        
        # 4. 向量化並儲存切片
        chunk_count = 0
        for chunk in chunks:
            try:
                # 提取關鍵字
                keywords_list = ai_core.extract_keywords(chunk['content'])
                
                from core.keyword_manager import get_keyword_manager
                km = get_keyword_manager()
                categorized_keywords = []
                
                for kw in keywords_list:
                    found = False
                    for category, mapping_list in km.get_all_data().items():
                        if kw in mapping_list:
                            categorized_keywords.append(f"{category}:{kw}")
                            found = True
                            break
                    if not found:
                        categorized_keywords.append(f"通用:{kw}")
                
                keywords_str = ",".join(categorized_keywords)
                
                # 取得 embedding
                embedding, usage = ai_core.get_embedding(chunk['content'])
                
                database.log_token_usage(
                    file_name=filename,
                    operation='retrain_embedding',
                    usage=usage
                )
                
                # 儲存切片與向量
                chunk_id = database.save_chunk_embedding(
                    doc_id=doc_id,
                    source_type=chunk['type'],
                    title=chunk['title'],
                    content=chunk['content'],
                    embedding=embedding,
                    keywords=keywords_str
                )
                chunk_count += 1
                
                # 儲存 chunk_metadata
                if chunk.get('metadata'):
                    database.save_chunk_metadata(chunk_id, chunk['metadata'])
                
            except Exception as e:
                logger.warning(f"切片向量化失敗: {chunk.get('title', 'Unknown')}, 錯誤: {e}")
        
        # 5. 建立版本記錄
        database.create_version(
            doc_id=doc_id,
            change_type='reprocess',
            change_description=f'重新訓練: 產生 {chunk_count} 個切片'
        )
        
        logger.info(f"✅ 重新訓練完成: {filename}, {chunk_count} 個切片已儲存")
        
        return {
            'success': True,
            'chunks': chunk_count,
            'message': f'成功重新訓練 {filename}'
        }
        
    except Exception as e:
        logger.error(f"❌ 重新訓練失敗: {filename}, 錯誤: {e}")
        return {
            'success': False,
            'chunks': 0,
            'message': f'重新訓練失敗: {str(e)}'
        }


if __name__ == "__main__":
    print("重新訓練模組載入成功")
