"""
查詢分詞工具模組

提供查詢字串分詞功能,用於改善關鍵字搜尋的召回率
"""

import re
from typing import List, Set


def tokenize_query(query: str) -> List[str]:
    """
    將查詢字串分詞,提取有意義的關鍵字
    
    規則:
    1. 移除檔案副檔名 (.pptx, .pdf 等)
    2. 以空格、標點符號分割
    3. 分離中英文混合詞彙 (例如: "蝴蝶Mura" -> ["蝴蝶", "Mura"])
    4. 過濾過短的詞 (< 2 字元)
    5. 過濾停用詞
    
    Args:
        query: 原始查詢字串
        
    Returns:
        關鍵字列表
        
    Examples:
        >>> tokenize_query("N706 蝴蝶Mura.pptx  內容詳細解析")
        ['N706', '蝴蝶', 'Mura']
        
        >>> tokenize_query("如何解決 ITO issue 問題")
        ['如何', '解決', 'ITO', 'issue', '問題']
    """
    # 移除副檔名
    query = re.sub(r'\.(pptx|pdf|xlsx|docx|txt|md)', '', query, flags=re.IGNORECASE)
    
    # 先以空格、逗號、句號等分割
    tokens = re.split(r'[\s,。、;:]+', query)
    
    # 進一步分離中英文混合的詞彙
    refined_tokens = []
    for token in tokens:
        if not token:
            continue
        
        # 使用正則表達式分離連續的中文、英文、數字
        # 匹配模式: 連續的中文字符 | 連續的英文字母和數字
        parts = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', token)
        
        if parts:
            refined_tokens.extend(parts)
        else:
            # 如果沒有匹配到,保留原token
            refined_tokens.append(token)
    
    # 停用詞表 (可根據實際情況擴充)
    stopwords = {
        '的', '了', '和', '與', '或', '在', '是', '有', '為', '以', '及',
        '內容', '詳細', '解析', '說明', '介紹', '資料', '文件', '檔案'
    }
    
    # 過濾
    keywords = []
    for token in refined_tokens:
        token = token.strip()
        if len(token) >= 2 and token not in stopwords:
            keywords.append(token)
    
    return keywords



def extract_document_identifiers(query: str) -> List[str]:
    """
    從查詢中提取文件編號/識別碼
    
    常見格式:
    - N706, A123 (字母+數字)
    - SOP-001 (字母-數字)
    - DOC_2024_01 (DOC_年份_月份)
    
    Args:
        query: 查詢字串
        
    Returns:
        文件編號列表
    """
    identifiers = []
    
    # 檢測常見的文件編號格式
    patterns = [
        r'[A-Z]\d{3,}',           # N706, A123
        r'[A-Z]{2,}-\d{3,}',      # SOP-001
        r'DOC[_-]\d{4}[_-]\d{2}', # DOC_2024_01
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        identifiers.extend(matches)
    
    return identifiers


def expand_query_with_synonyms(keywords: List[str], synonym_map: dict = None) -> List[str]:
    """
    使用同義詞擴展查詢關鍵字
    
    Args:
        keywords: 原始關鍵字列表
        synonym_map: 同義詞映射字典
        
    Returns:
        擴展後的關鍵字列表 (包含原始關鍵字)
    """
    if synonym_map is None:
        # 預設同義詞映射
        synonym_map = {
            'Mura': ['斑點', '不均勻'],
            '問題': ['issue', 'problem'],
            '異常': ['error', '錯誤', 'fault'],
            '故障': ['failure', 'malfunction'],
            '如何': ['怎麼', '怎樣'],
            '步驟': ['流程', 'procedure', 'process'],
        }
    
    expanded = keywords.copy()
    for kw in keywords:
        if kw in synonym_map:
            expanded.extend(synonym_map[kw])
    
    return expanded


def contains_document_identifier(query: str) -> bool:
    """
    檢查查詢是否包含文件編號/名稱
    
    Args:
        query: 查詢字串
        
    Returns:
        是否包含文件編號
    """
    return len(extract_document_identifiers(query)) > 0
