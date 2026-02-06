"""
Search Module - Keyword Matcher
關鍵字匹配與提取功能
"""

import sqlite3
import logging
import re
from typing import List
from rapidfuzz import fuzz, process
from config import DB_PATH

logger = logging.getLogger(__name__)


def fuzzy_search_keywords(query: str, threshold: int = 80) -> List[str]:
    """
    模糊比對關鍵字
    
    Args:
        query: 使用者輸入的搜尋詞
        threshold: 相似度門檻（0-100）
    
    Returns:
        List[str]: 相似的關鍵字列表
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 從所有子表收集關鍵字
        all_keywords = set()
        
        for table in ['doc_knowledge', 'doc_training', 'doc_procedure', 'doc_troubleshooting']:
            cursor.execute(f"SELECT DISTINCT keywords FROM {table}")
            for row in cursor.fetchall():
                if row[0]:
                    # 分割關鍵字（假設用逗號或頓號分隔）
                    keywords = row[0].replace('、', ',').split(',')
                    all_keywords.update([k.strip() for k in keywords if k.strip()])
        
        conn.close()
        
        # 使用 rapidfuzz 進行模糊比對
        matches = process.extract(
            query,
            list(all_keywords),
            scorer=fuzz.ratio,
            limit=5
        )
        
        # 過濾低於門檻的結果
        similar_keywords = [match[0] for match in matches if match[1] >= threshold]
        
        if similar_keywords:
            logger.info(f"模糊搜尋: '{query}' -> {similar_keywords}")
        
        return similar_keywords
        
    except Exception as e:
        logger.error(f"模糊搜尋失敗: {e}")
        return []


def extract_potential_terms(query: str) -> List[str]:
    """
    從自然語言查詢中提取潛在的搜尋詞
    1. 提取包含副檔名的檔案名 (xxx.pptx)
    2. 提取英數組合 (N706, 8D)
    3. 提取中文詞彙 (簡單的空格分隔)
    """
    terms = set()
    
    # 1. 提取可能的檔案名 (含副檔名)
    filename_pattern = r'[\w\u4e00-\u9fa5]+\.(pptx|ppt|pdf|md|txt)'
    filenames = re.findall(filename_pattern, query, re.IGNORECASE)
    
    parts = query.replace('，', ' ').replace('。', ' ').split()
    for part in parts:
        # 去除標點
        clean_part = re.sub(r'[^\w\.\u4e00-\u9fa5]', '', part)
        if not clean_part:
            continue
            
        # 如果像是檔案名
        if any(clean_part.lower().endswith(ext) for ext in ['.pptx', '.ppt', '.pdf', '.md', '.txt']):
            terms.add(clean_part)
        # 如果是英數混合 (如 N706, 8D)
        elif re.search(r'[a-zA-Z0-9]+', clean_part):
            terms.add(clean_part)
            
    # 如果都沒抓到,嘗試直接回傳分割後的詞 (排除常見停用詞)
    stop_words = {'給我', '的', '歸納', '總結', '列表', '有哪些', '中', '與', '和', '了', '吧', '嗎'}
    if not terms:
        for part in parts:
            if part not in stop_words and len(part) > 1:
                terms.add(part)
                
    return list(terms)


def get_all_keywords() -> List[str]:
    """
    取得所有關鍵字（用於自動完成或標籤雲）
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        all_keywords = set()
        for table in ['doc_knowledge', 'doc_training', 'doc_procedure', 'doc_troubleshooting']:
            cursor.execute(f"SELECT DISTINCT keywords FROM {table}")
            for row in cursor.fetchall():
                if row[0]:
                    keywords = row[0].replace('、', ',').split(',')
                    all_keywords.update([k.strip() for k in keywords if k.strip()])
        
        conn.close()
        return sorted(list(all_keywords))
        
    except Exception as e:
        logger.error(f"取得關鍵字失敗: {e}")
        return []
