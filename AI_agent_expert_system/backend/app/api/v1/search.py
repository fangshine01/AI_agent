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
    語意搜尋 (使用通用查詢引擎)
    """
    try:
        search = get_search()
        config = get_config()

        api_key = request.api_key or config.API_KEY
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
    關鍵字搜尋
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
