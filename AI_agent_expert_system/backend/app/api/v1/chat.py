"""
Chat API - 問答路由
"""

import logging
from fastapi import APIRouter, HTTPException

from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.dependencies import get_database, get_ai_core, get_search, get_config

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=ChatResponse)
async def query(request: ChatRequest):
    """
    執行問答查詢

    流程:
    1. 搜尋知識庫
    2. 組合上下文
    3. 呼叫 AI 模型生成回答
    """
    try:
        database = get_database()
        ai_core = get_ai_core()
        search = get_search()
        config = get_config()

        # 準備 API 設定
        api_key = request.api_key or config.API_KEY
        base_url = request.base_url or config.BASE_URL

        # 檢查是否為列表查詢
        list_keywords = ["有哪些", "列出", "目錄", "清單", "全部", "所有文件", "知識庫"]
        is_list_query = any(kw in request.query for kw in list_keywords)

        if is_list_query:
            overview = database.get_knowledge_overview()
            response_parts = [f"📚 **知識庫概覽**\n\n目前共有 **{overview['total']}** 個文件\n"]
            if overview.get("by_type"):
                response_parts.append("\n**文件類型統計:**")
                for ftype, count in overview["by_type"].items():
                    response_parts.append(f"- {ftype}: {count} 個")
            if overview.get("all_keywords"):
                response_parts.append(f"\n\n**熱門關鍵字:** {', '.join(overview['all_keywords'][:20])}")

            return ChatResponse(
                response="\n".join(response_parts),
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 100},
            )

        # 執行搜尋
        doc_type_filter = request.selected_types[0] if request.selected_types else None
        search_result = search.universal_search(
            query=request.query,
            top_k=request.search_limit,
            doc_type=doc_type_filter,
            auto_strategy=True,
            api_key=api_key,
            base_url=base_url,
            query_type=request.query_type,
            filters=request.filters,
        )

        search_results = search_result.get("results", [])
        search_meta = search_result.get("meta", {})

        if not search_results:
            return ChatResponse(
                response="抱歉，我找不到與您問題直接相關的資料。請嘗試使用更簡單的關鍵字。",
                search_meta=search_meta,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 50},
            )

        # 檢查是否為直接檢索 (跳過 LLM)
        if search_meta.get("skip_llm", False):
            doc = search_results[0]
            content = doc.get("raw_content", doc.get("content", ""))
            return ChatResponse(
                response=content,
                search_results=search_results,
                search_meta=search_meta,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                is_direct_retrieval=True,
                doc_type=doc.get("file_type"),
            )

        # 組合上下文
        context_parts = []
        for i, doc in enumerate(search_results, 1):
            max_len = 8000 if len(search_results) <= 2 else 3000
            content = doc.get("raw_content", doc.get("preview", ""))[:max_len]
            context_parts.append(f"[文件{i}] {doc['file_name']}\n{content}\n")
        context = "\n".join(context_parts)

        # 根據查詢類型組建 Prompt
        prompts_by_type = {
            "troubleshooting": (
                "你是工廠維修專家。",
                "請根據參考資料中的異常現象與解決方案，整理出完整的維修建議。",
            ),
            "procedure": (
                "你是資深工程師。",
                "請根據參考資料，清晰條列出操作步驟。",
            ),
            "knowledge": (
                "你是技術資料管理員。",
                "請根據參考資料，精準回答規格參數或錯誤代碼定義。",
            ),
            "training": (
                "你是資深企業講師。",
                "請根據參考資料，深入淺出地解釋技術原理或演算法概念。",
            ),
        }

        system_role, instruction = prompts_by_type.get(
            request.query_type,
            ("", "請根據上述參考資料，簡潔明確地回答使用者的問題。"),
        )

        full_prompt = f"""{system_role}
以下是相關的參考資料:

{context}

---

使用者問題: {request.query} ({request.query_type} mode)

{instruction}
"""

        # 呼叫 AI
        messages = [{"role": "user", "content": full_prompt}]
        response_text, usage = ai_core.call_chat_model(
            messages=messages,
            model=request.chat_model,
            api_key=api_key,
            base_url=base_url,
        )

        # 記錄 Token
        database.log_token_usage(file_name=None, operation="qa", usage=usage)

        return ChatResponse(
            response=response_text,
            search_results=search_results,
            search_meta={
                "intent": search_result.get("intent", ""),
                "strategy": search_result.get("strategy", ""),
                **search_meta,
            },
            usage=usage,
        )

    except Exception as e:
        logger.error(f"❌ 查詢失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history():
    """取得聊天歷史 (由前端 session 管理，此端點供未來擴展)"""
    return {"message": "聊天歷史由前端 session_state 管理"}
