"""
v3.0 Document Ingestion Module
整合新的 parsers 和 database 模組
"""

import os
import logging
from typing import Optional, Callable, Dict, List
from pathlib import Path

# 匯入新模組
from core import database
from core.parsers import TroubleshootingParser, TrainingParser, KnowledgeParser
from core import ai_core, ppt_parser

logger = logging.getLogger(__name__)


def process_document_v3(
    file_path: str,
    doc_type: str,
    analysis_mode: str = "auto",
    text_model: str = None,
    vision_model: str = None,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    v3.0 文件處理流程 (使用新的 parsers 和 database 模組)
    
    Args:
        file_path: 文件路徑
        doc_type: 文件類型 ('Knowledge', 'Troubleshooting', 'Training')
        analysis_mode: 分析模式 ('text_only', 'vision', 'auto')
        text_model: 文字模型 (可選)
        vision_model: 視覺模型 (可選)
        progress_callback: 進度回調函數
    
    Returns:
        Dict: {'success': bool, 'doc_id': int, 'chunks': int, 'message': str}
    """
    try:
        filename = os.path.basename(file_path)
        logger.info(f"開始處理文件: {filename} (類型: {doc_type})")
        
        if progress_callback:
            progress_callback(f"正在解析: {filename}")
        
        # 步驟 1: 讀取文件內容
        raw_content = _read_file_content_v3(file_path)
        if not raw_content:
            return {
                'success': False,
                'message': f'無法讀取文件內容: {filename}'
            }
        
        # 步驟 2: 建立文件記錄
        model_used = text_model or vision_model or "auto"
        doc_id = database.create_document(
            filename=filename,
            doc_type=doc_type,
            analysis_mode=analysis_mode,
            model_used=model_used
        )
        
        logger.info(f"文件記錄已建立, ID: {doc_id}")
        
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
                    vision_model=vision_model
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
            
        elif doc_type == 'Knowledge':
            # Knowledge 需要先拆分為章節
            chapters = _extract_chapters(raw_content)
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
                keywords_list = ai_core.extract_keywords(chunk['content'])
                
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
                embedding, usage = ai_core.get_embedding(chunk['content'])
                
                # 記錄 Token
                database.log_token_usage(
                    file_name=filename,
                    operation='ingestion_embedding',
                    usage=usage
                )
                
                # 儲存切片與向量 (含關鍵字)
                database.save_chunk_embedding(
                    doc_id=doc_id,
                    source_type=chunk['type'],
                    title=chunk['title'],
                    content=chunk['content'],
                    embedding=embedding,
                    keywords=keywords_str
                )
                chunk_count += 1
                
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


def _read_file_content_v3(file_path: str) -> str:
    """
    讀取文件內容 (支援 .txt, .md, .pptx)
    
    Args:
        file_path: 文件路徑
    
    Returns:
        str: 文件內容
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.txt' or ext == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        elif ext == '.pptx':
            # 使用現有的 ppt_parser
            slides_data = ppt_parser.parse_ppt(file_path, extract_images=False)
            # 合併所有投影片內容
            content_parts = []
            for slide in slides_data:
                if slide.get('text'):
                    content_parts.append(f"--- 投影片 {slide.get('page_num', '?')} ---\n{slide['text']}")
            return "\n\n".join(content_parts)
        
        else:
            logger.warning(f"不支援的文件格式: {ext}")
            return ""
            
    except Exception as e:
        logger.error(f"讀取文件失敗: {e}")
        return ""


def _extract_chapters(content: str) -> Dict[str, str]:
    """
    從內容中提取章節 (簡單實現)
    
    Args:
        content: 完整內容
    
    Returns:
        Dict[str, str]: {"章節標題": "章節內容"}
    """
    # 簡單的章節切分邏輯
    # 假設以 "---" 或 "# " 開頭的行為章節標題
    
    chapters = {}
    current_chapter = "主要內容"
    current_content = []
    
    for line in content.split('\n'):
        # 檢查是否為章節標題
        if line.startswith('---') or line.startswith('# '):
            # 儲存前一章節
            if current_content:
                chapters[current_chapter] = '\n'.join(current_content)
            
            # 開始新章節
            current_chapter = line.replace('---', '').replace('#', '').strip()
            if not current_chapter:
                current_chapter = f"章節 {len(chapters) + 1}"
            current_content = []
        else:
            current_content.append(line)
    
    # 儲存最後一章
    if current_content:
        chapters[current_chapter] = '\n'.join(current_content)
    
    # 如果沒有找到章節,將整個內容作為單一章節
    if not chapters:
        chapters["完整內容"] = content
    
    return chapters


if __name__ == "__main__":
    # 測試用
    print("v3.0 Ingestion 模組載入成功")
