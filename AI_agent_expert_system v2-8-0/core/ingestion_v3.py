"""
v2.7.0 Document Ingestion Module
整合新的 parsers 和 database 模組
輔助邏輯已拆分至 core/ingestion/ 子套件:
  - file_reader.py   (讀檔 / 章節切分)
  - keyword_matcher.py (關鍵字比對 + 儲存)
  - image_ingestion.py (Gemini Vision 圖片處理)
"""

import os
import logging
from typing import Optional, Callable, Dict, List
from pathlib import Path

from core import database
from core.parsers import TroubleshootingParser, TrainingParser, KnowledgeParser, ProcedureParser
from core import ai_core
from core.ingestion.file_reader import read_file_content, extract_chapters
from core.ingestion.keyword_matcher import save_keywords_to_db
from core.ingestion.image_ingestion import process_image_with_gemini

logger = logging.getLogger(__name__)


def process_document_v3(
    file_path: str,
    doc_type: str,
    analysis_mode: str = "auto",
    text_model: str = None,
    vision_model: str = None,
    progress_callback: Optional[Callable] = None,
    auto_extract_metadata: bool = True,  # 是否自動提取元數據
    category: str = None,  # 手動指定分類
    department: str = None,  # 部門
    factory: str = None,  # 工廠
    priority: int = 0,  # 優先級
    api_key: str = None,  # 使用者 API Key（每人消耗自己的 API）
    base_url: str = None,  # API Base URL
    enable_gemini_vision: bool = False,  # 啟用 Gemini 圖片辨識
    parent_doc_id: int = None,  # 父文件 ID（圖片生成 MD 關聯原圖）
) -> Dict:
    """
    v3.0 文件處理流程 (使用新的 parsers 和 database 模組)
    增強版: 支援自動元數據提取
    
    Args:
        file_path: 文件路徑
        doc_type: 文件類型 ('Knowledge', 'Troubleshooting', 'Training', 'Procedure')
        analysis_mode: 分析模式 ('text_only', 'vision', 'auto')
        text_model: 文字模型 (可選)
        vision_model: 視覺模型 (可選)
        progress_callback: 進度回調函數
        auto_extract_metadata: 是否使用 AI 自動提取元數據
        category: 手動指定分類
        department: 部門
        factory: 工廠
        priority: 優先級
    
    Returns:
        Dict: {'success': bool, 'doc_id': int, 'chunks': int, 'message': str}
    """
    import time
    from core.metadata_extractor import calculate_file_hash, extract_document_metadata
    
    try:
        filename = os.path.basename(file_path)
        logger.info(f"開始處理文件: {filename} (類型: {doc_type})")
        
        start_time = time.time()
        
        # 設定使用者 API 配置（若提供自訂 base_url）
        # 注意：API Key 不再設定到全域 config，而是直接傳遞給各個函數
        if base_url:
            try:
                import backend.config as root_config
                root_config.set_api_config(base_url=base_url)
                logger.info("✅ 已套用使用者自訂 API Base URL")
            except Exception as e:
                logger.warning(f"⚠️ 設定使用者 API 配置失敗: {e}")
        
        # 檢查是否為圖片檔案
        ext = os.path.splitext(file_path)[1].lower()
        is_image = ext in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        
        if is_image:
            if enable_gemini_vision:
                return process_image_with_gemini(
                    file_path=file_path,
                    doc_type=doc_type,
                    progress_callback=progress_callback,
                    parent_doc_id=parent_doc_id,
                )
            else:
                return {
                    'success': False,
                    'message': f'圖片檔案需啟用 enable_gemini_vision 參數: {filename}'
                }
        
        if progress_callback:
            progress_callback(f"正在解析: {filename}")
        
        # 步驟 1: 讀取文件內容
        raw_content = read_file_content(file_path)
        if not raw_content:
            return {
                'success': False,
                'message': f'無法讀取文件內容: {filename}'
            }
        
        # 步驟 2: 提取基本檔案資訊
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size
        file_hash = calculate_file_hash(file_path)
        
        # 步驟 3: 使用 AI 提取元數據 (如果啟用)
        metadata = {}
        if auto_extract_metadata:
            if progress_callback:
                progress_callback(f"正在提取元數據: {filename}")
            
            try:
                ai_metadata = extract_document_metadata(
                    content=raw_content,
                    doc_type=doc_type,
                    model=text_model or "gpt-4o-mini",
                    api_key=api_key,
                    base_url=base_url
                )
                metadata.update(ai_metadata)
                logger.info(f"✓ 元數據提取完成: {filename}")
            except Exception as e:
                logger.warning(f"元數據提取失敗: {e}")
        
        # 步驟 4: 建立文件記錄 (使用增強版函數)
        processing_time = time.time() - start_time
        model_used = text_model or vision_model or "auto"
        
        doc_id = database.create_document_enhanced(
            filename=filename,
            doc_type=doc_type,
            analysis_mode=analysis_mode,
            model_used=model_used,
            category=category or metadata.get('category'),
            tags=metadata.get('tags'),
            file_size=file_size,
            file_hash=file_hash,
            processing_time=processing_time,
            department=department,
            factory=factory,
            priority=priority,
            summary=metadata.get('summary'),
            key_points=metadata.get('key_points'),
            language=metadata.get('language', 'zh-TW'),
            # Troubleshooting 專用欄位
            product_model=metadata.get('product_model'),
            defect_code=metadata.get('defect_code'),
            station=metadata.get('station'),
            yield_loss=metadata.get('yield_loss')
        )
        
        logger.info(f"文件記錄已建立, ID: {doc_id}")
        
        # 設定 parent_doc_id（若有關聯的父文件）
        if parent_doc_id:
            try:
                database.update_document(
                    doc_id, parent_doc_id=parent_doc_id, source_type='gemini_vision'
                )
                logger.info(f"✅ 已設定 parent_doc_id={parent_doc_id} (doc_id={doc_id})")
            except Exception as e:
                logger.warning(f"⚠️ 設定 parent_doc_id 失敗: {e}")
        
        # 步驟 4a: 儲存原始內容到 document_raw_data 表
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            content_type = 'markdown' if file_ext == '.md' else 'text'
            database.save_raw_data(
                doc_id=doc_id,
                raw_content=raw_content,
                content_type=content_type,
                file_extension=file_ext
            )
            logger.info(f"✓ Raw data 已儲存 (doc_id: {doc_id})")
        except Exception as e:
            logger.warning(f"⚠️ 儲存 Raw data 失敗: {e}")
        
        # 步驟 4b: 儲存關鍵字到 document_keywords 表
        try:
            save_keywords_to_db(doc_id, raw_content, doc_type, metadata)
        except Exception as e:
            logger.warning(f"⚠️ 儲存關鍵字失敗: {e}")
        
        # 步驟 4c: 儲存專屬 metadata (Troubleshooting / Procedure)
        try:
            if doc_type == 'Troubleshooting':
                database.save_troubleshooting_metadata(
                    doc_id=doc_id,
                    product_model=metadata.get('product_model'),
                    defect_code=metadata.get('defect_code'),
                    station=metadata.get('station'),
                    yield_loss=metadata.get('yield_loss')
                )
            elif doc_type in ('Procedure', 'procedure'):
                database.save_procedure_metadata(doc_id=doc_id)
        except Exception as e:
            logger.warning(f"⚠️ 儲存專屬 metadata 失敗: {e}")
        
        # 步驟 4d: 建立版本記錄
        try:
            database.create_version(
                doc_id=doc_id,
                change_type='create',
                change_description=f'初始上傳: {filename}'
            )
        except Exception as e:
            logger.warning(f"⚠️ 建立版本記錄失敗: {e}")
        
        # 步驟 3: 根據文件類型選擇解析器
        if progress_callback:
            progress_callback(f"正在分析: {filename}")
        
        # 創建 AI Core 包裝器 (用於解析器)
        class AICoreWrapper:
            """簡單的 AI Core 包裝器,提供 analyze_slide 介面並記錄 Token"""
            def __init__(self, filename):
                self.filename = filename

            def analyze_slide(self, prompt, api_mode="text_only"):
                """呼叫 AI 分析"""
                result, usage = ai_core.analyze_slide(
                    text=prompt,
                    image_paths=None,
                    api_mode=api_mode,
                    text_model=text_model,
                    vision_model=vision_model,
                    api_key=api_key,
                    base_url=base_url
                )
                
                # 記錄 Token
                database.log_token_usage(
                    file_name=self.filename,
                    operation='ingestion_parse',
                    usage=usage
                )
                return result
        
        ai_wrapper = AICoreWrapper(filename)
        
        # 選擇並執行解析器
        chunks = []
        if doc_type == 'Troubleshooting':
            parser = TroubleshootingParser(ai_wrapper)
            chunks = parser.parse(raw_content)
            
        elif doc_type == 'Training':
            parser = TrainingParser(ai_wrapper)
            chunks = parser.parse(raw_content)
            
        elif doc_type == 'Procedure' or doc_type == 'procedure':
            parser = ProcedureParser(ai_wrapper)
            chunks = parser.parse(raw_content)
            
        elif doc_type == 'Knowledge':
            # Knowledge 需要先拆分為章節
            chapters = extract_chapters(raw_content)
            parser = KnowledgeParser(ai_wrapper)
            chunks = parser.parse(chapters)
        
        logger.info(f"解析完成,產生 {len(chunks)} 個切片")
        
        # 步驟 4: 向量化並儲存切片
        if progress_callback:
            progress_callback(f"正在向量化: {filename}")
        
        chunk_count = 0
        for chunk in chunks:
            try:
                # 提取關鍵字 (自動)
                keywords_list = ai_core.extract_keywords(
                    chunk['content'],
                    api_key=api_key,
                    base_url=base_url
                )
                
                # 關鍵字歸類
                from core.keyword_manager import get_keyword_manager
                import json
                
                km = get_keyword_manager()
                categorized_keywords = []
                
                for kw in keywords_list:
                    # 檢查映射表
                    found = False
                    for category, mapping_list in km.get_all_data().items():
                        if kw in mapping_list:
                            categorized_keywords.append(f"{category}:{kw}")
                            found = True
                            break
                    
                    if not found:
                        categorized_keywords.append(f"通用:{kw}")
                
                # 轉為字串儲存
                keywords_str = ",".join(categorized_keywords)
                
                # 取得 embedding
                embedding, usage = ai_core.get_embedding(
                    chunk['content'],
                    api_key=api_key,
                    base_url=base_url
                )
                
                # 記錄 Token
                database.log_token_usage(
                    file_name=filename,
                    operation='ingestion_embedding',
                    usage=usage
                )
                
                # 儲存切片與向量 (含關鍵字)
                chunk_id = database.save_chunk_embedding(
                    doc_id=doc_id,
                    source_type=chunk['type'],
                    title=chunk['title'],
                    content=chunk['content'],
                    embedding=embedding,
                    keywords=keywords_str
                )
                chunk_count += 1
                
                # 儲存 chunk_metadata (若有結構化 metadata)
                if chunk.get('metadata'):
                    try:
                        database.save_chunk_metadata(chunk_id, chunk['metadata'])
                    except Exception as e:
                        logger.warning(f"儲存 chunk metadata 失敗: {e}")
                
            except Exception as e:
                logger.warning(f"切片向量化失敗: {chunk['title']}, 錯誤: {e}")
        
        logger.info(f"✅ 文件處理完成: {filename}, {chunk_count} 個切片已儲存")
        
        if progress_callback:
            progress_callback(f"完成: {filename}")
        
        return {
            'success': True,
            'doc_id': doc_id,
            'chunks': chunk_count,
            'message': f'成功處理 {filename}'
        }
        
    except Exception as e:
        logger.error(f"❌ 文件處理失敗: {filename}, 錯誤: {e}")
        return {
            'success': False,
            'message': f'處理失敗: {str(e)}'
        }


def process_directory_v3(
    doc_dir: str,
    doc_type: str,
    analysis_mode: str = "auto",
    text_model: str = None,
    vision_model: str = None,
    file_extensions: List[str] = None,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    v3.0 批次處理目錄下的文件
    
    Args:
        doc_dir: 文件目錄
        doc_type: 文件類型
        analysis_mode: 分析模式
        text_model: 文字模型
        vision_model: 視覺模型
        file_extensions: 允許的副檔名 (預設: ['.pptx', '.md', '.txt'])
        progress_callback: 進度回調
    
    Returns:
        Dict: {'processed': int, 'success': int, 'errors': [...]}
    """
    if file_extensions is None:
        file_extensions = ['.pptx', '.md', '.txt']
    
    logger.info(f"開始批次處理: {doc_dir}")
    
    # 找出所有檔案
    files = []
    for ext in file_extensions:
        files.extend(Path(doc_dir).glob(f'*{ext}'))
    
    if not files:
        logger.warning(f"目錄中沒有找到文件: {doc_dir}")
        return {'processed': 0, 'success': 0, 'errors': []}
    
    logger.info(f"找到 {len(files)} 個文件")
    
    results = {
        'processed': 0,
        'success': 0,
        'errors': []
    }
    
    for file_path in files:
        results['processed'] += 1
        
        result = process_document_v3(
            file_path=str(file_path),
            doc_type=doc_type,
            analysis_mode=analysis_mode,
            text_model=text_model,
            vision_model=vision_model,
            progress_callback=progress_callback
        )
        
        if result['success']:
            results['success'] += 1
        else:
            results['errors'].append({
                'file': file_path.name,
                'error': result['message']
            })
    
    logger.info(f"批次處理完成: {results['success']}/{results['processed']} 成功")
    return results


if __name__ == "__main__":
    print("v3.0 Ingestion 模組載入成功")

