"""
Search API - 搜尋路由
"""

import logging
from fastapi import APIRouter, HTTPException

from backend.app.schemas.document import SearchRequest, SearchResult
from backend.app.dependencies import get_search, get_config

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/semantic", response_model=SearchResult)
async def semantic_search(request: SearchRequest):
    """
    語意搜尋（使用通用查詢引擎 v4.0）

    自動分析查詢意圖，選擇最佳搜尋策略（向量搜尋 / 混合搜尋 / 關鍵字搜尋）。
    支援 Embedding 快取與結果快取以提升效能。

    Args:
        request: SearchRequest JSON body:
            - query (str): 查詢文字
            - top_k (int): 回傳前 k 筆結果，預設 5
            - doc_type (str): 可選，限定文件類型
            - filters (dict): 可選，結構化過濾條件
            - api_key (str): 可選，覆蓋預設 API Key
            - base_url (str): 可選，覆蓋預設 Base URL

    Returns:
        SearchResult:
            - intent (str): 偵測到的查詢意圖
            - strategy (str): 使用的搜尋策略
            - results (list): 搜尋結果陣列
            - meta (dict): 搜尋元資訊

    Raises:
        HTTPException 500: 搜尋引擎錯誤
    """
    try:
        search = get_search()
        config = get_config()

        # BYOK 模式：必須使用用戶提供的 API Key
        api_key = request.api_key
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="系統採用 BYOK 模式，請提供您的 API Key"
            )
        
        base_url = request.base_url or config.BASE_URL

        result = search.universal_search(
            query=request.query,
            top_k=request.top_k,
            doc_type=request.doc_type,
            auto_strategy=True,
            api_key=api_key,
            base_url=base_url,
            query_type="general",
            filters=request.filters,
        )

        return SearchResult(
            success=True,
            intent=result.get("intent", ""),
            strategy=result.get("strategy", ""),
            results=result.get("results", []),
            meta=result.get("meta", {}),
        )

    except Exception as e:
        logger.error(f"❌ 語意搜尋失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keyword", response_model=SearchResult)
async def keyword_search(request: SearchRequest):
    """
    關鍵字搜尋（Legacy v2.0 搜尋引擎）

    使用傳統關鍵字匹配搜尋，支援模糊搜尋。
    適用於精確文件名稱、型號查找等場景。

    Args:
        request: SearchRequest JSON body:
            - query (str): 查詢文字
            - top_k (int): 回傳前 k 筆結果，預設 5
            - doc_type (str): 可選，限定文件類型
            - enable_fuzzy (bool): 是否啟用模糊匹配，預設 True

    Returns:
        SearchResult:
            - intent: 固定為 "keyword_search"
            - strategy: 固定為 "legacy_search"
            - results (list): 匹配的文件列表
            - meta.result_count (int): 結果數量

    Raises:
        HTTPException 500: 搜尋引擎錯誤
    """
    try:
        search = get_search()

        results = search.search_documents_v2(
            query=request.query,
            file_types=[request.doc_type] if request.doc_type else None,
            fuzzy=request.enable_fuzzy,
            top_k=request.top_k,
        )

        return SearchResult(
            success=True,
            intent="keyword_search",
            strategy="legacy_search",
            results=results,
            meta={"result_count": len(results)},
        )

    except Exception as e:
        logger.error(f"❌ 關鍵字搜尋失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
