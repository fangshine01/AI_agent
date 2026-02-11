
"""
意圖路由器 (Intent Router)
負責分析使用者查詢意圖，並決定最佳的檢索策略
主要用於 Troubleshooting 的智慧路由 (Smart Routing)
"""

import logging
from typing import Optional, Dict, Tuple
from core.database import find_document_by_metadata, get_connection

logger = logging.getLogger(__name__)

class IntentRouter:
    _instance = None
    _products = set()
    _defects = set()
    _last_refresh = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IntentRouter, cls).__new__(cls)
            cls._instance._refresh_cache()
        return cls._instance

    def _refresh_cache(self):
        """從資料庫載入所有已知的 Product 和 Defect 以供快速匹配"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # 載入 Products
            cursor.execute("SELECT DISTINCT product_model FROM troubleshooting_metadata WHERE product_model IS NOT NULL")
            self._products = {row[0].strip().upper() for row in cursor.fetchall() if row[0]}
            
            # 載入 Defects
            cursor.execute("SELECT DISTINCT defect_code FROM troubleshooting_metadata WHERE defect_code IS NOT NULL")
            self._defects = {row[0].strip().upper() for row in cursor.fetchall() if row[0]}
            
            conn.close()
            logger.info(f"✅ IntentRouter cache refreshed: {len(self._products)} products, {len(self._defects)} defects")
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh IntentRouter cache: {e}")

    def check_troubleshooting_exact_match(self, query: str) -> Optional[Dict]:
        """
        檢查查詢是否為 Troubleshooting 精確查找
        
        Returns:
            Optional[Dict]: 若命中則回傳文件資料 (同 find_document_by_metadata)，否則 None
        """
        query_upper = query.upper()
        
        # 1. 識別 Product
        matched_product = None
        for prod in self._products:
            if prod in query_upper:
                matched_product = prod
                break
        
        # 2. 識別 Defect
        matched_defect = None
        for defect in self._defects:
            if defect in query_upper:
                matched_defect = defect
                break
                
        # 3. 只有當兩者都命中時，才進行資料庫精確查找
        if matched_product and matched_defect:
            logger.info(f"🔍 Detected exact match intent: Product={matched_product}, Defect={matched_defect}")
            return find_document_by_metadata(matched_product, matched_defect)
            
        return None

# Global instance
router = IntentRouter()

def check_troubleshooting_intent(query: str) -> Optional[Dict]:
    """Helper function to use the singleton router"""
    return router.check_troubleshooting_exact_match(query)
