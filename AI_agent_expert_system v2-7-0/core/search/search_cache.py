"""
Search Optimization - 搜尋快取與效能優化 (v2.3.0 Phase 5)

功能：
- Embedding 向量快取 (LRU，避免重複呼叫 API)
- 搜尋結果快取 (TTL-based，減少重複查詢)
- 查詢預處理 (正規化、去重)
- 效能指標記錄

設計考量：
- 全記憶體快取，重啟後自動失效（無持久化需求）
- 執行緒安全
- 快取大小可配置，避免記憶體失控
"""

import time
import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class LRUCache:
    """
    執行緒安全的 LRU 快取

    Args:
        max_size: 最大快取項目數
        ttl_seconds: 快取過期時間（秒），0 = 永不過期
    """

    def __init__(self, max_size: int = 500, ttl_seconds: int = 0):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """取得快取值，命中時移至前端"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, timestamp = self._cache[key]

            # 檢查 TTL
            if self._ttl > 0 and (time.time() - timestamp) > self._ttl:
                del self._cache[key]
                self._misses += 1
                return None

            # 移至最近使用端
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def put(self, key: str, value: Any):
        """寫入快取值"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = (value, time.time())
            else:
                if len(self._cache) >= self._max_size:
                    # 移除最久未使用的項目
                    self._cache.popitem(last=False)
                self._cache[key] = (value, time.time())

    def invalidate(self, key: str):
        """刪除特定快取項目"""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        """清空快取"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> Dict:
        """取得快取統計"""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "N/A",
            }


# ========== 全域快取實例 ==========

# Embedding 快取：較大（向量計算成本高），不設 TTL
embedding_cache = LRUCache(max_size=1000, ttl_seconds=0)

# 搜尋結果快取：中等大小，5 分鐘 TTL（知識庫可能更新）
search_result_cache = LRUCache(max_size=200, ttl_seconds=300)


def _normalize_query(query: str) -> str:
    """
    正規化查詢字串（去除多餘空白、統一大小寫等）
    用於快取鍵生成
    """
    # 去除前後空白、壓縮連續空白
    normalized = " ".join(query.strip().split())
    # 轉為小寫（中文不受影響）
    normalized = normalized.lower()
    return normalized


def _make_cache_key(prefix: str, query: str, **kwargs) -> str:
    """
    生成快取鍵

    Args:
        prefix: 快取類型前綴 (如 "emb", "search")
        query: 查詢字串
        **kwargs: 其他影響結果的參數
    """
    normalized = _normalize_query(query)
    # 將額外參數排序後加入
    extra = "|".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
    raw_key = f"{prefix}:{normalized}:{extra}"
    return hashlib.md5(raw_key.encode("utf-8")).hexdigest()


def get_cached_embedding(query: str) -> Optional[List[float]]:
    """
    取得快取的 embedding 向量

    Args:
        query: 原始查詢文字

    Returns:
        快取的 embedding 向量，或 None
    """
    key = _make_cache_key("emb", query)
    result = embedding_cache.get(key)
    if result is not None:
        logger.debug(f"[快取命中] Embedding: '{query[:30]}...'")
    return result


def cache_embedding(query: str, embedding: List[float]):
    """
    快取 embedding 向量

    Args:
        query: 原始查詢文字
        embedding: 計算得到的向量
    """
    key = _make_cache_key("emb", query)
    embedding_cache.put(key, embedding)
    logger.debug(f"[快取寫入] Embedding: '{query[:30]}...' (dim={len(embedding)})")


def get_cached_search_results(
    query: str, top_k: int = 5, source_type: Optional[str] = None
) -> Optional[List[Dict]]:
    """
    取得快取的搜尋結果

    Args:
        query: 查詢文字
        top_k: 結果數量
        source_type: 來源類型過濾

    Returns:
        快取的搜尋結果列表，或 None
    """
    key = _make_cache_key("search", query, top_k=top_k, source_type=source_type)
    result = search_result_cache.get(key)
    if result is not None:
        logger.debug(f"[快取命中] 搜尋結果: '{query[:30]}...' ({len(result)} 筆)")
    return result


def cache_search_results(
    query: str,
    results: List[Dict],
    top_k: int = 5,
    source_type: Optional[str] = None,
):
    """
    快取搜尋結果

    Args:
        query: 查詢文字
        results: 搜尋結果列表
        top_k: 結果數量
        source_type: 來源類型過濾
    """
    key = _make_cache_key("search", query, top_k=top_k, source_type=source_type)
    search_result_cache.put(key, results)
    logger.debug(f"[快取寫入] 搜尋結果: '{query[:30]}...' ({len(results)} 筆)")


def invalidate_search_cache():
    """
    清空搜尋結果快取（當知識庫更新時呼叫）
    Embedding 快取保留（向量不變）
    """
    search_result_cache.clear()
    logger.info("🗑️ 搜尋結果快取已清空")


def get_all_cache_stats() -> Dict:
    """
    取得所有快取的統計資訊

    Returns:
        Dict 包含 embedding_cache 和 search_result_cache 的統計
    """
    return {
        "embedding_cache": embedding_cache.stats,
        "search_result_cache": search_result_cache.stats,
    }
