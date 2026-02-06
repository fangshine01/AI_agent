"""
AI Expert System - Data Ingestion Module
控制 PPT 檔案的批次處理與 AI 分析流程
"""

import os
import glob
import logging
from typing import Dict, Callable, Optional

from core import database, ppt_parser, ai_core

logger = logging.getLogger(__name__)


def process_directory(
    ppt_dir: str,
    user_focus: str = "",
    api_mode: str = "auto",
    ppt_mode: str = "text_and_images",
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    處理指定目錄下的所有 PPT 檔案
    
    Args:
        ppt_dir: PPT 檔案目錄
        user_focus: 使用者關注點
        api_mode: "text_only", "vision", "auto"
        ppt_mode: "text_only", "text_and_images"
        progress_callback: 進度回調函數 (current, total, message)
    
    Returns:
        {
            'total_files': int,
            'processed': int,
            'skipped': int,
            'errors': [...]
        }
    """
    logger.info("=" * 60)
    logger.info(f"開始處理目錄: {ppt_dir}")
    logger.info(f"PPT 模式: {ppt_mode}, API 模式: {api_mode}")
    logger.info("=" * 60)
    
    # 初始化資料庫
    database.init_database()
    
    # 尋找所有 PPT 與 MD 檔案
    ppt_files = glob.glob(os.path.join(ppt_dir, "**/*.pptx"), recursive=True)
    ppt_files += glob.glob(os.path.join(ppt_dir, "**/*.ppt"), recursive=True)
    md_files = glob.glob(os.path.join(ppt_dir, "**/*.md"), recursive=True)
    
    all_files = ppt_files + md_files
    
    total_files = len(all_files)
    processed = 0
    skipped = 0
    errors = []
    
    logger.info(f"找到 {len(ppt_files)} 個 PPT 檔案, {len(md_files)} 個 MD 檔案")
    
    if total_files == 0:
        return {
            'total_files': 0,
            'processed': 0,
            'skipped': 0,
            'errors': []
        }
    
    for idx, file_path in enumerate(all_files):
        file_name = os.path.basename(file_path)
        current = idx + 1
        
        # 更新進度
        if progress_callback:
            try:
                progress_callback(current, total_files, f"正在處理: {file_name} ({current}/{total_files})")
            except:
                pass
       
        logger.info(f"\n[{current}/{total_files}] 處理: {file_name}")
        
        try:
            # 檢查檔案是否已處理且未變更
            file_hash = database.get_file_hash(file_path)
            
            if database.check_file_processed(file_path, file_hash):
                logger.info(f"⏭️  檔案未變更，跳過: {file_name}")
                skipped += 1
                database.log_processing(file_path, "skipped")
                continue
            
            # 若檔案已修改，先刪除舊記錄
            database.delete_slides_by_file(file_path)
            
            # 判斷檔案類型並解析
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.md':
                # 解析 Markdown
                from core import md_parser  # 延遲導入避免循環引用
                slides_data = md_parser.parse_md(file_path)
            else:
                # 解析 PPT
                extract_images = (ppt_mode == "text_and_images")
                slides_data = ppt_parser.parse_ppt(file_path, extract_images=extract_images)
            
            # 逐頁處理
            for slide_data in slides_data:
                page_num = slide_data['page_num']
                text = slide_data['text']
                images = slide_data['images']
                
                # 使用 AI 分析
                try:
                    analyzed_content, usage = ai_core.analyze_slide(
                        text=text,
                        image_paths=images,
                        user_focus=user_focus,
                        api_mode=api_mode
                    )
                    
                    # 記錄 Token 使用量
                    database.log_token_usage(
                        file_name=file_name,
                        operation='analysis',
                        usage=usage
                    )
                    
                except Exception as e:
                    logger.warning(f"AI 分析失敗 (頁 {page_num}): {e}，使用原始文字")
                    analyzed_content = text
                
                # 存入資料庫
                database.insert_slide(
                    file_path=file_path,
                    file_name=file_name,
                    file_hash=file_hash,
                    page_num=page_num,
                    content=analyzed_content,
                    raw_text=text,
                    has_image=(len(images) > 0)
                )
                
                logger.debug(f"  ✅ 頁 {page_num} 已存入資料庫")
            
            processed += 1
            database.log_processing(file_path, "success")
            logger.info(f"✅ 完成: {file_name} ({len(slides_data)} 頁/段落)")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 處理失敗: {file_name}, 錯誤: {error_msg}")
            errors.append({'file': file_name, 'error': error_msg})
            database.log_processing(file_path, "error", error_msg)
    
    logger.info("\n" + "=" * 60)
    logger.info("處理完成！")
    logger.info(f"總檔案數: {total_files}")
    logger.info(f"已處理: {processed}")
    logger.info(f"已跳過: {skipped}")
    logger.info(f"錯誤: {len(errors)}")
    logger.info("=" * 60)
    
    return {
        'total_files': total_files,
        'processed': processed,
        'skipped': skipped,
        'errors': errors
    }


# ========== v2.0 新增：支援 documents 架構的批次處理 ==========

def process_documents_v2(
    doc_dir: str,
    file_type: str,
    file_extensions: list = None,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    v2.0 文件處理（整份文件處理，非逐頁）
    
    Args:
        doc_dir: 文件目錄
        file_type: 文件類型 ('knowledge', 'training', 'procedure', 'troubleshooting')
        file_extensions: 要處理的副檔名列表（預設 ['.pptx', '.md', '.txt']）
        progress_callback: 進度回調 (current, total, message)
    
    Returns:
        {
            'total_files': int,
            'processed': int,
            'errors': [...]
        }
    """
    from core import parsers, database
    import time
    
    logger.info("=" * 60)
    logger.info(f"開始處理文件目錄 (v2.0): {doc_dir}")
    logger.info(f"文件類型: {file_type}")
    logger.info("=" * 60)
    
    # 初始化新架構資料庫
    database.init_documents_schema()
    
    # 預設副檔名
    if file_extensions is None:
        file_extensions = ['.pptx', '.md', '.txt']
    
    # 收集檔案
    all_files = []
    for ext in file_extensions:
        pattern = os.path.join(doc_dir, f"**/*{ext}")
        all_files.extend(glob.glob(pattern, recursive=True))
    
    stats = {
        'total_files': len(all_files),
        'processed': 0,
        'errors': []
    }
    
    logger.info(f"找到 {len(all_files)} 個檔案")
    
    # 取得對應的 Parser
    parser = parsers.ParserFactory.get_parser(file_type)
    
    for idx, file_path in enumerate(all_files, 1):
        try:
            if progress_callback:
                progress_callback(idx, len(all_files), f"處理: {os.path.basename(file_path)}")
            
            logger.info(f"[{idx}/{len(all_files)}] 處理: {file_path}")
            
            # 讀取檔案內容
            content = _read_file_content(file_path)
            
            if not content:
                logger.warning(f"檔案內容為空，跳過: {file_path}")
                continue
            
            # 使用 Parser 解析(傳遞 API 憑證,若有提供的話)
            logger.info(f"使用 {parser.parser_type} Parser 解析...")
            # 從 config 取得當前的 API 設定(後台已設定的)
            import config as cfg
            api_key = cfg.API_KEY if cfg.API_KEY else None
            base_url = cfg.BASE_URL if cfg.BASE_URL else None
            
            type_data, usage = parser.parse(content, api_key=api_key, base_url=base_url)
            
            # 除錯:印出 type_data 的內容
            logger.debug(f"Parser 回傳的 type_data: {type_data}")
            logger.debug(f"type_data 的欄位類型: {[(k, type(v).__name__) for k, v in type_data.items()]}")
            
            # 從 type_data 中提取並移除 author (避免傳入不支援的欄位)
            author = type_data.pop('author', '')  # 提取並刪除 author 欄位
            
            # 準備主表資料
            file_info = {
                'file_name': os.path.basename(file_path),
                'file_path': file_path,
                'file_hash': database.get_file_hash(file_path),
                'file_type': file_type,
                'raw_content': content,
                'author': author  # 使用提取的作者資訊
            }
            
            # 寫入資料庫
            doc_id = database.insert_document(file_info, type_data)
            
            if doc_id:
                stats['processed'] += 1
                logger.info(f"成功寫入資料庫: doc_id={doc_id}")
                
                # 記錄 Token 使用
                if usage:
                    database.log_token_usage(
                        file_name=os.path.basename(file_path),
                        operation='analysis',
                        usage=usage
                    )
            else:
                stats['errors'].append({
                    'file': file_path,
                    'error': '資料庫寫入失敗'
                })
        
        except Exception as e:
            logger.error(f"處理檔案失敗: {file_path}, 錯誤: {e}")
            stats['errors'].append({
                'file': file_path,
                'error': str(e)
            })
    
    logger.info("=" * 60)
    logger.info(f"處理完成: {stats['processed']}/{stats['total_files']}")
    logger.info(f"錯誤數: {len(stats['errors'])}")
    logger.info("=" * 60)
    
    return stats


def _read_file_content(file_path: str) -> str:
    """
    讀取檔案內容（支援 .txt, .md, .pptx）
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.txt', '.md']:
        # 純文字檔案
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='big5') as f:
                return f.read()
    
    elif ext == '.pptx':
        # PPT 檔案：提取所有頁面的文字
        try:
            slides_data = ppt_parser.parse_ppt(file_path, extract_images=False)
            all_text = "\n\n".join([
                f"--- 第 {slide['page_num']} 頁 ---\n{slide['text']}"
                for slide in slides_data
            ])
            return all_text
        except Exception as e:
            logger.error(f"PPT 解析失敗: {file_path}, {e}")
            return ""
    
    elif ext == '.pdf':
        # PDF 檔案:提取所有頁面的文字
        try:
            import PyPDF2
            all_text = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    if text.strip():
                        all_text.append(f"--- 第 {page_num} 頁 ---\n{text}")
            
            result = "\n\n".join(all_text)
            logger.info(f"PDF 解析完成: {len(pdf_reader.pages)} 頁, {len(result)} 字元")
            return result
        except ImportError:
            logger.error("缺少 PyPDF2 套件,請執行: pip install PyPDF2")
            return ""
        except Exception as e:
            logger.error(f"PDF 解析失敗: {file_path}, {e}")
            return ""
    
    else:
        logger.warning(f"不支援的檔案格式: {ext}")
        return ""


# 測試用
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_dir = sys.argv[1]
        result = process_directory(test_dir, api_mode="text_only", ppt_mode="text_only")
        print(f"\n處理結果: {result}")
    else:
        print("使用方式: python ingestion.py <ppt_directory>")
