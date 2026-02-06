"""
解析器基礎類別模組
定義解析器的基礎類別與共用方法
"""

from abc import ABC, abstractmethod
from typing import List, Dict
import json
import re
import logging

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """解析器基礎類別"""
    
    def __init__(self, ai_core):
        """
        初始化解析器
        
        Args:
            ai_core: AI 核心模組,用於呼叫 AI 分析功能
        """
        self.ai_core = ai_core
    
    @abstractmethod
    def parse(self, raw_data) -> List[Dict]:
        """
        解析原始資料為結構化切片
        
        Args:
            raw_data: 原始資料 (可能是字串或字典)
        
        Returns:
            List[Dict]: 結構化的切片列表
                每個切片包含: {'type': str, 'title': str, 'content': str}
        """
        pass
    
    def extract_json_from_response(self, response: str) -> Dict:
        """
        從 AI 回應中提取 JSON
        
        Args:
            response: AI 的文字回應
        
        Returns:
            Dict: 解析後的 JSON 字典
        
        Raises:
            ValueError: 無法解析 JSON 時拋出
        """
        try:
            # 1. 嘗試直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 2. 嘗試提取 ```json ... ``` 區塊
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 3. 嘗試提取 ``` ... ``` 區塊 (沒有 json 標籤)
            code_match = re.search(r'```\s*(.+?)\s*```', response, re.DOTALL)
            if code_match:
                try:
                    return json.loads(code_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 4. 嘗試尋找 JSON 物件 (以 { 開頭 } 結尾)
            json_obj_match = re.search(r'\{.+\}', response, re.DOTALL)
            if json_obj_match:
                try:
                    return json.loads(json_obj_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            logger.error(f"無法從回應中提取 JSON: {response[:200]}...")
            raise ValueError("無法從 AI 回應中提取有效的 JSON")
    
    def clean_text(self, text: str) -> str:
        """
        清理文字內容
        
        Args:
            text: 原始文字
        
        Returns:
            str: 清理後的文字
        """
        if not text:
            return ""
        
        # 移除多餘的空白
        text = re.sub(r'\s+', ' ', text)
        # 移除前後空白
        text = text.strip()
        
        return text
    
    def validate_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        驗證切片格式是否正確
        
        Args:
            chunks: 切片列表
        
        Returns:
            List[Dict]: 驗證後的切片列表
        """
        validated = []
        
        for chunk in chunks:
            # 檢查必要欄位
            if not isinstance(chunk, dict):
                logger.warning(f"切片不是字典格式,跳過: {chunk}")
                continue
            
            if 'type' not in chunk or 'title' not in chunk or 'content' not in chunk:
                logger.warning(f"切片缺少必要欄位,跳過: {chunk}")
                continue
            
            # 清理內容
            chunk['content'] = self.clean_text(str(chunk['content']))
            
            # 只保留非空內容
            if chunk['content']:
                validated.append(chunk)
        
        return validated


if __name__ == "__main__":
    print("BaseParser 基礎類別定義完成")
