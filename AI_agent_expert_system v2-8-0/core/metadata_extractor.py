# -*- coding: utf-8 -*-
"""
元數據提取模組

使用 AI 從文件內容中自動提取元數據
"""

import json
import logging
import hashlib
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str) -> str:
    """
    計算檔案 hash 值
    
    Args:
        file_path: 檔案路徑
    
    Returns:
        str: MD5 hash 值
    """
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.warning(f"計算檔案 hash 失敗: {e}")
        return ""


def extract_document_metadata(
    content: str,
    doc_type: str,
    model: str = "gpt-4o-mini",
    max_content_length: int = 3000
) -> Dict:
    """
    使用 AI 從文件內容中提取元數據
    
    Args:
        content: 文件內容
        doc_type: 文件類型
        model: 使用的 AI 模型
        max_content_length: 最大內容長度 (避免 token 過多)
    
    Returns:
        包含元數據的字典:
        {
            'summary': str,           # 摘要
            'key_points': list,       # 重點列表
            'category': str,          # 推薦分類
            'tags': list,             # 標籤
            'language': str,          # 語言
            # Troubleshooting 專用:
            'product_model': str,     # 產品型號
            'defect_code': str,       # 缺陷代碼
            'station': str,           # 檢出站點
            'yield_loss': str         # 產量損失
        }
    """
    try:
        from core import ai_core
        
        # 截取內容避免 token 過多
        content_preview = content[:max_content_length]
        
        # 針對 Troubleshooting 或 Procedure 類型使用特殊 prompt
        if doc_type in ['Troubleshooting', 'Procedure', 'procedure']:
            prompt = f"""請分析以下 {doc_type} 文件,提取關鍵資訊:

【文件內容】
{content_preview}

請以 JSON 格式回覆:
{{
    "summary": "一段式摘要(不超過150字)",
    "key_points": ["重點1", "重點2", "重點3"],
    "suggested_category": "建議的二級分類",
    "tags": ["標籤1", "標籤2"],
    "language": "zh-TW 或 en-US",
    "product_model": "產品型號 (如 N706, N707, 或適用機台)",
    "defect_code": "缺陷代碼 (如 Oven Pin, 蝴蝶Mura) 或 作業對象",
    "station": "檢出站點或適用站點 (如 PTST, A3LR, LCD2)",
    "yield_loss": "產量損失 (僅8D報告需要, SOP填null)"
}}

注意:
1. summary 要簡潔扼要,突出核心內容
2. key_points 列出 3-5 個最重要的要點
3. product_model, defect_code, station, yield_loss 請從文件中提取,若無法確定則填 null
4. Procedure (SOP) 文件請特別留意「適用範圍」或「Target」來提取 station 與 product_model
5. 只回覆 JSON,不要其他文字
"""
        else:
            # 一般文件使用原有 prompt
            prompt = f"""請分析以下{doc_type}文件,提取關鍵資訊:

【文件內容】
{content_preview}

請以 JSON 格式回覆:
{{
    "summary": "一段式摘要(不超過150字)",
    "key_points": ["重點1", "重點2", "重點3"],
    "suggested_category": "建議的二級分類",
    "tags": ["標籤1", "標籤2"],
    "language": "zh-TW 或 en-US"
}}

注意:
1. summary 要簡潔扼要,突出核心內容
2. key_points 列出 3-5 個最重要的要點
3. suggested_category 根據內容推薦分類 (例如: Hardware, Software, Process, Quality 等)
4. tags 提取 2-5 個關鍵標籤
5. 只回覆 JSON,不要其他文字
"""
        
        # 使用 analyze_slide (text_only 模式) 來替代不存在的 analyze_text
        # analyze_slide 回傳 (content, usage)
        response, _ = ai_core.analyze_slide(prompt, api_mode="text_only", text_model=model)
        
        # 清理回應 (移除 Markdown 標記)
        cleaned_response = response.strip()
        if cleaned_response.startswith("```"):
            # 移除開頭的 ```json 或 ```
            first_newline = cleaned_response.find("\n")
            if first_newline != -1:
                cleaned_response = cleaned_response[first_newline+1:]
            # 移除結尾的 ```
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
        
        cleaned_response = cleaned_response.strip()
        
        # 解析 JSON 回應
        try:
            metadata = json.loads(cleaned_response)
            
            result = {
                'summary': metadata.get('summary'),
                'key_points': json.dumps(metadata.get('key_points', []), ensure_ascii=False),
                'category': metadata.get('suggested_category'),
                'tags': json.dumps(metadata.get('tags', []), ensure_ascii=False),
                'language': metadata.get('language', 'zh-TW')
            }
            
            # 針對 Troubleshooting/Procedure 新增專用欄位
            if doc_type in ['Troubleshooting', 'Procedure', 'procedure']:
                result['product_model'] = metadata.get('product_model')
                result['defect_code'] = metadata.get('defect_code')
                result['station'] = metadata.get('station')
                result['yield_loss'] = metadata.get('yield_loss')
            
            return result
            
        except json.JSONDecodeError:
            logger.warning("AI 回應不是有效的 JSON,嘗試提取部分資訊")
            # 如果 JSON 解析失敗,返回基本資訊
            return {
                'summary': response[:150] if len(response) > 150 else response,
                'key_points': json.dumps([], ensure_ascii=False),
                'category': None,
                'tags': json.dumps([], ensure_ascii=False),
                'language': 'zh-TW'
            }
            
    except Exception as e:
        logger.warning(f"元數據提取失敗: {e}")
        return {
            'summary': None,
            'key_points': json.dumps([], ensure_ascii=False),
            'category': None,
            'tags': json.dumps([], ensure_ascii=False),
            'language': 'zh-TW'
        }


def extract_metadata_from_file(
    file_path: str,
    doc_type: str,
    auto_extract: bool = True
) -> Dict:
    """
    從檔案中提取完整的元數據
    
    Args:
        file_path: 檔案路徑
        doc_type: 文件類型
        auto_extract: 是否使用 AI 自動提取元數據
    
    Returns:
        包含所有元數據的字典
    """
    metadata = {}
    
    # 1. 基本檔案資訊
    try:
        file_stats = os.stat(file_path)
        metadata['file_size'] = file_stats.st_size
        metadata['file_hash'] = calculate_file_hash(file_path)
    except Exception as e:
        logger.warning(f"取得檔案資訊失敗: {e}")
        metadata['file_size'] = None
        metadata['file_hash'] = None
    
    # 2. 使用 AI 提取元數據 (如果啟用)
    if auto_extract:
        try:
            # 讀取檔案內容 (這裡需要根據檔案類型使用不同的 parser)
            # 簡化版本:假設已經有解析好的內容
            # 實際使用時應該整合到 ingestion_v3.py 中
            ai_metadata = {
                'summary': None,
                'key_points': json.dumps([], ensure_ascii=False),
                'category': None,
                'tags': json.dumps([], ensure_ascii=False),
                'language': 'zh-TW'
            }
            metadata.update(ai_metadata)
        except Exception as e:
            logger.warning(f"AI 元數據提取失敗: {e}")
    
    return metadata


if __name__ == "__main__":
    # 測試元數據提取
    logging.basicConfig(level=logging.INFO)
    
    test_content = """
    N706 蝴蝶Mura 問題分析報告
    
    問題描述:
    在生產過程中發現蝴蝶狀的 Mura 缺陷,影響產品品質。
    
    根本原因:
    1. 溫度控制不均勻
    2. 材料批次差異
    3. 設備老化
    
    解決方案:
    - 優化溫度控制參數
    - 加強材料檢驗
    - 定期設備維護
    """
    
    print("測試元數據提取:")
    metadata = extract_document_metadata(test_content, "Troubleshooting")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
