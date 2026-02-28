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

        # BYOK 模式：必須使用用戶提供的 API Key
        api_key = request.api_key
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="系統採用 BYOK 模式，請提供您的 API Key"
            )
        
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
            # 情境 B：資料庫沒有找到相關資料，改呼叫 LLM 以自身知識作答
            system_prompt_b = (
                "因為知識庫中沒有相關資料，請直接根據你的內建知識回答 User 的問題。"
                "請確保答案正確且細節豐富，並適當區分段落，讓閱讀體驗順暢。"
                "回答結束時給予延伸補充或行動建議。"
            )
            messages_b = [
                {"role": "system", "content": system_prompt_b},
                {"role": "user",   "content": request.query},
            ]
            response_text_b, usage_b = ai_core.call_chat_model(
                messages=messages_b,
                model=request.chat_model,
                api_key=api_key,
                base_url=base_url,
            )
            # 記錄 Token（非致命，失敗不中斷問答）
            try:
                database.log_token_usage(file_name=None, operation="qa", usage=usage_b)
            except Exception as te:
                logger.warning(f"[Token] 記錄 token 失敗（非致命）: {te}")
            return ChatResponse(
                response=response_text_b,
                search_meta=search_meta,
                usage=usage_b,
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

        # 根據查詢類型組建 Prompt（情境 A：資料庫有找到相關資料）
        prompts_by_type = {
            "troubleshooting": (
                "你是工廠維修專家。請根據 User 提供的參考資料中的異常現象與解決方案，整理出完整的維修建議。在回答最後，主動提供延伸補充與行動建議。",
            ),
            "procedure": (
                "你是資深工程師。請根據 User 提供的參考資料，清晰條列出操作步驟。在回答最後，主動提供延伸補充與行動建議。",
            ),
            "knowledge": (
                "你是技術資料管理員。請根據 User 提供的參考資料，精準回答規格參數或錯誤代碼定義。在回答最後，主動提供延伸補充與行動建議。",
            ),
            "training": (
                "你是資深企業講師。請根據 User 提供的參考資料，深入淺出地解釋技術原理或演算法概念。在回答最後，主動提供延伸補充與行動建議。",
            ),
        }

        # system_prompt：角色定位 + 任務指令（覆蓋 Proxy 的預設人設）
        system_prompt = prompts_by_type.get(
            request.query_type,
            ("請根據 User 提供的參考資料，簡潔明確地回答問題。在回答最後，主動提供延伸補充與行動建議。",),
        )[0]

        # user_prompt：參考資料 + 使用者問題
        user_prompt = f"""【參考資料】
{context}

【使用者問題】
{request.query}"""

        # 呼叫 AI（標準兩段式 messages，確保 system prompt 不被 Proxy 蓋掉）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
        response_text, usage = ai_core.call_chat_model(
            messages=messages,
            model=request.chat_model,
            api_key=api_key,
            base_url=base_url,
        )

        # 記錄 Token（非致命，失敗不中斷問答）
        try:
            database.log_token_usage(file_name=None, operation="qa", usage=usage)
        except Exception as te:
            logger.warning(f"[Token] 記錄 token 失敗（非致命）: {te}")

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
    """
    取得聊天歷史（佔位端點）

    目前聊天歷史由前端 session_state 管理，
    完整歷史功能請使用 /api/v1/history/sessions 端點。

    Returns:
        dict: {"message": str} 提示訊息
    """
    return {"message": "聊天歷史由前端 session_state 管理"}
