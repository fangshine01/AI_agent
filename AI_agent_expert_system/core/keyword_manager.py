"""
Keyword Manager Module
負責管理關鍵字對應表 (JSON)
"""

import json
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class KeywordManager:
    def __init__(self, data_path: str = "data/keyword_mappings"):
        """
        初始化 KeywordManager
        
        Args:
            data_path: JSON檔案目錄路徑 (預設: data/keyword_mappings)
        """
        # 確保路徑是絕對路徑或是相對於專案根目錄
        if not os.path.isabs(data_path):
             base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
             data_path = os.path.join(base_dir, data_path)
             
        self.data_path = data_path
        self._data: Dict[str, List[str]] = {}
        self._load_data()

    def _load_data(self):
        """從目錄載入所有 JSON 檔案"""
        if not os.path.exists(self.data_path):
            logger.warning(f"關鍵字目錄不存在: {self.data_path}, 建立新目錄")
            os.makedirs(self.data_path, exist_ok=True)
            self._data = {}
            return

        self._data = {}
        try:
            for filename in os.listdir(self.data_path):
                if filename.endswith(".json"):
                    category = os.path.splitext(filename)[0]
                    file_path = os.path.join(self.data_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        keywords = json.load(f)
                        if isinstance(keywords, list):
                            self._data[category] = keywords
            
            logger.info(f"已載入關鍵字設定: {len(self._data)} 個類別")
        except Exception as e:
            logger.error(f"載入關鍵字檔案失敗: {e}")
            self._data = {}

    def _save_category(self, category: str):
        """儲存特定類別到檔案"""
        try:
            os.makedirs(self.data_path, exist_ok=True)
            file_path = os.path.join(self.data_path, f"{category}.json")
            
            # 如果該類別已被刪除 (不在 self._data 中)，則刪除檔案
            if category not in self._data:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已刪除類別檔案: {file_path}")
                return

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data[category], f, indent=4, ensure_ascii=False)
            logger.info(f"類別 {category} 已儲存")
            
        except Exception as e:
            logger.error(f"儲存類別 {category} 失敗: {e}")

    def get_all_categories(self) -> List[str]:
        """取得所有類別名稱"""
        return list(self._data.keys())

    def get_keywords(self, category: str) -> List[str]:
        """
        取得特定類別的關鍵字列表
        
        Args:
            category: 類別名稱 (如 "產品")
        """
        return self._data.get(category, [])

    def add_category(self, category: str) -> bool:
        """
        新增類別
        
        Returns:
            bool: 是否成功 (若已存在則回傳 False)
        """
        if category in self._data:
            return False
        
        self._data[category] = []
        self._save_category(category)
        return True

    def remove_category(self, category: str) -> bool:
        """刪除類別"""
        if category in self._data:
            del self._data[category]
            self._save_category(category) # 這會觸發檔案刪除
            return True
        return False

    def add_keyword(self, category: str, keyword: str) -> bool:
        """
        新增關鍵字到特定類別
        
        Returns:
             bool: 是否成功
        """
        if category not in self._data:
            self._data[category] = []
            
        if keyword not in self._data[category]:
            self._data[category].append(keyword)
            self._save_category(category)
            return True
        return False

    def remove_keyword(self, category: str, keyword: str) -> bool:
        """從類別刪除關鍵字"""
        if category in self._data and keyword in self._data[category]:
            self._data[category].remove(keyword)
            self._save_category(category)
            return True
        return False

    def get_all_data(self) -> Dict[str, List[str]]:
        """取得完整資料"""
        return self._data.copy()

# 測試用單例
_manager = None

def get_keyword_manager() -> KeywordManager:
    global _manager
    if _manager is None:
        _manager = KeywordManager()
    return _manager
