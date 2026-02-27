"""
AI Expert System - AI Core Module
與 AI API (OpenAI/Compatible) 的整合
支援自訂 API 端點（直接 HTTP 請求模式）
"""

import base64
import logging
import httpx
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import backend.config as config

logger = logging.getLogger(__name__)

# 定義可重試的例外類型（僅限暫時性錯誤，避免重試 400/401 等客戶端錯誤）
_RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    OSError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadTimeout,
)

# 嘗試加入 openai 特定例外
try:
    import openai
    _RETRYABLE_EXCEPTIONS += (
        openai.RateLimitError,
        openai.APITimeoutError,
        openai.APIConnectionError,
        openai.InternalServerError,
    )
except ImportError:
    pass


def encode_image_to_base64(image_path: str) -> str:
    """將圖片編碼為 base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def call_chat_model(messages: List[Dict], model: str = None, temperature: float = 0.3, max_tokens: int = None,
                   api_key: str = None, base_url: str = None) -> str:
    """
    呼叫 Chat Completions API（標準 OpenAI 格式）
    
    Args:
        messages: 對話訊息列表
        model: 模型名稱（可選）
        temperature: 溫度參數
        max_tokens: 最大 token 數（可選）
        api_key: API Key（可選，未提供則使用 config）
        base_url: Base URL（可選，未提供則使用 config）
    
    Returns:
        str: AI 回應內容
    """
    # 使用傳入的 URL 或 config 預設值
    url = base_url if base_url else config.BASE_URL
    
    # 若 URL 不包含 /chat/completions，自動補上
    if not url.endswith('/chat/completions'):
        if url.endswith('/'):
            url = url + 'chat/completions'
        else:
            url = url + '/chat/completions'
    
    headers = {
        "Content-Type": "application/json",
    }
    
    # BYOK 模式：必須使用用戶提供的 API Key
    if not api_key:
        logger.error("❌ 未提供 API Key，系統採用 BYOK 模式")
        raise ValueError("系統採用 BYOK 模式，請提供您的 API Key")
    
    headers["Authorization"] = f"Bearer {api_key.strip()}"
    
    payload = {
        "messages": messages,
        "temperature": temperature,
    }
    
    # 若有指定 model，加入 payload
    if model:
        payload["model"] = model
    
    # 若有指定 max_tokens，加入 payload
    if max_tokens:
        payload["max_tokens"] = max_tokens
    
    logger.debug(f"📡 API 請求: {url}")
    
    try:
        with httpx.Client(timeout=60.0) as client:
            logger.info(f"📤 發送請求到: {url}")
            logger.debug(f"📤 請求 Headers: {headers}")
            logger.debug(f"📤 請求 Payload: {payload}")
            
            response = client.post(url, json=payload, headers=headers)
            
            # 先記錄回應，再檢查狀態
            logger.info(f"📥 回應狀態: {response.status_code}")
            logger.debug(f"📥 回應內容: {response.text[:500] if response.text else '(空)'}")
            
            response.raise_for_status()
            
            data = response.json()
            
            # 提取 Token 使用資訊
            usage = data.get('usage', {})
            token_info = {
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            }
            
            # 嘗試從標準 OpenAI 格式解析
            content = None
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
            # 若格式不同，嘗試其他常見格式
            elif "content" in data:
                content = data["content"]
            elif "response" in data:
                content = data["response"]
            elif "message" in data:
                content = data["message"]
            else:
                # 若都找不到，返回原始 JSON
                logger.warning(f"⚠️ 無法解析 API 回應格式: {data}")
                content = str(data)
            
            return content, token_info
            
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ API HTTP 錯誤: {e.response.status_code}")
        logger.error(f"❌ 錯誤回應內容: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"❌ API 呼叫失敗: {e}")
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
    reraise=True,
)
def analyze_slide(
    text: str,
    image_paths: List[str] = None,
    user_focus: str = "",
    api_mode: str = "auto",
    api_key: str = None,
    base_url: str = None,
    text_model: str = None,
    vision_model: str = None
) -> tuple:
    """
    分析單張投影片，返回結構化的知識摘要
    
    Args:
        text: 投影片文字內容
        image_paths: 圖片路徑列表 (可選)
        user_focus: 使用者關注點
        api_mode: "text_only", "vision", "auto"
        api_key: API Key(可選)
        base_url: Base URL(可選)
        text_model: 文字模型名稱 (可選,預設使用 config.MODEL_TEXT)
        vision_model: 視覺模型名稱 (可選,預設使用 config.MODEL_VISION)
    
    Returns:
        tuple: (AI 分析後的結構化內容, Token 使用資訊)
    """
    # 處理 image_paths 為 None 的情況
    if image_paths is None:
        image_paths = []
    
    # 智慧判斷使用哪種 API
    use_vision = (api_mode == "vision") or (api_mode == "auto" and len(image_paths) > 0)
    
    if use_vision and len(image_paths) > 0:
        return _analyze_with_vision(
            text, image_paths, user_focus, 
            api_key=api_key, base_url=base_url, model=vision_model
        )
    else:
        return _analyze_text_only(
            text, user_focus, 
            api_key=api_key, base_url=base_url, model=text_model
        )


def _analyze_text_only(text: str, user_focus: str = "", api_key: str = None, base_url: str = None, model: str = None) -> str:
    """使用純文字 API 分析"""
    if not text.strip():
        return "", {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    
    system_prompt = """請分析以下投影片內容，提取重點資訊。
【要求】
1. 提取關鍵資訊並結構化輸出
2. 保留重要數據、人名、專有名詞
3. 若有清單或步驟，請整理成條列式

請輸出結構化的知識摘要："""

    user_content = f"【投影片文字】\n{text}\n\n"
    if user_focus:
        user_content += f"【使用者關注點】{user_focus}"

    try:
        used_model = model if model else config.DEFAULT_TEXT_MODEL
        logger.debug(f"🔤 使用文字 API: {used_model}")
        result, usage = call_chat_model(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=used_model,
            temperature=0.3,
            api_key=api_key,
            base_url=base_url
        )
        
        logger.debug(f"✅ 文字分析完成，長度: {len(result)}, Tokens: {usage['total_tokens']}")
        return result, usage
        
    except Exception as e:
        logger.error(f"❌ 文字 API 呼叫失敗: {e}")
        return text, {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}  # 降級：返回原始文字


def _analyze_with_vision(text: str, image_paths: List[str], user_focus: str = "", api_key: str = None, base_url: str = None, model: str = None) -> str:
    """使用 Vision API 分析"""
    system_prompt = """請分析這張投影片，整合文字與圖片內容。
【要求】
1. 若有流程圖，請嘗試轉為 Mermaid Markdown 格式
2. 若有圖表，請提取關鍵數據
3. 整合所有資訊，輸出結構化的知識摘要

請輸出結構化內容："""

    user_text = f"【投影片文字】\n{text if text else '(無文字)'}\n\n"
    if user_focus:
        user_text += f"【使用者關注點】{user_focus}"

    content_parts = [
        {
            "type": "text",
            "text": user_text
        }
    ]
    
    # 加入圖片
    for img_path in image_paths[:5]:  # 限制最多 5 張圖片
        try:
            img_base64 = encode_image_to_base64(img_path)
            img_ext = img_path.split('.')[-1].lower()
            
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{img_ext};base64,{img_base64}"
                }
            })
        except Exception as e:
            logger.warning(f"圖片編碼失敗 {img_path}: {e}")
    
    try:
        used_model = model if model else config.DEFAULT_VISION_MODEL
        logger.debug(f"🖼️ 使用 Vision API: {used_model}, {len(image_paths)} 圖片")
        result, usage = call_chat_model(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_parts}
            ],
            model=used_model,
            temperature=0.3,
            max_tokens=1500,
            api_key=api_key,
            base_url=base_url
        )
        
        logger.debug(f"✅ Vision 分析完成,長度: {len(result)}, Tokens: {usage['total_tokens']}")
        return result, usage
        
    except Exception as e:
        logger.error(f"❌ Vision API 呼叫失敗: {e}")
        # 降級:使用純文字模式
        return _analyze_text_only(text, user_focus, api_key=api_key, base_url=base_url, model=None)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
    reraise=True,
)
def get_embedding(text: str, api_key: str = None, base_url: str = None) -> tuple:
    """
    取得文字的 Embedding 向量
    
    Args:
        text: 輸入文字
        api_key: API Key (優先使用)
        base_url: Base URL (優先使用)
        
    Returns:
        tuple: (embedding_vector, usage_dict)
    """
    try:
        if not text:
            return [], {'total_tokens': 0}
            
        text = text.replace("\n", " ")
        if len(text) > 8000:
            text = text[:8000]
            
        # BYOK 模式：必須使用用戶提供的 API Key
        if not api_key:
            logger.error("❌ 未提供 API Key，無法呼叫 Embedding API")
            raise ValueError("系統採用 BYOK 模式，請提供您的 API Key")
            
        used_base_url = base_url if base_url else config.BASE_URL
        
        client = httpx.Client(timeout=30.0)
        
        response = client.post(
            f"{used_base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            },
            json={
                "input": text,
                "model": config.EMBEDDING_MODEL
            }
        )
        response.raise_for_status()
        
        data = response.json()
        embedding = data['data'][0]['embedding']
        usage = data.get('usage', {'total_tokens': 0})
        
        return embedding, usage
        
    except Exception as e:
        logger.error(f"❌ Embedding API 呼叫失敗: {e}")
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
    reraise=True,
)
def chat_response(
    question: str,
    context_slides: List[Dict],
    conversation_history: List[Dict] = None,
    api_key: str = None,
    base_url: str = None
) -> Dict:
    """
    基於檢索到的內容回答使用者問題
    
    Args:
        question: 使用者問題
        context_slides: 檢索到的投影片列表 [{file_path, file_name, page_num, content}, ...]
        conversation_history: 對話歷史
        api_key: API Key(可選)
        base_url: Base URL(可選)
    
    Returns:
        {
            'answer': str,
            'sources': [
                {'file': 'xxx.pptx', 'page': 5},
                ...
            ]
        }
    """
    if conversation_history is None:
        conversation_history = []
    
    if context_slides:
        # 情境 A：資料庫有找到相關資料
        # 建構上下文
        context_text = "\n\n".join([
            f"【來源：{slide['file_name']} - 第 {slide['page_num']} 頁】\n{slide['content']}"
            for slide in context_slides
        ])
        
        system_prompt = """請根據 User 提供的參考資料進行統整與總結。你的任務是化繁為簡，並在回答最後主動提供額外的延伸補充與行動建議。若參考資料不足以回答問題，請明確告知。"""
        
        user_prompt = f"""【上下文資料】
{context_text}

【使用者問題】
{question}

請根據上述上下文回答問題："""
        
        # 整理來源
        sources = [
            {'file': slide['file_name'], 'page': slide['page_num']}
            for slide in context_slides
        ]
    else:
        # 情境 B：資料庫沒有找到相關資料
        system_prompt = """因為知識庫中沒有相關資料，請直接根據你的內建知識與網路搜尋能力，回答 User 的問題。請確保答案正確且細節豐富，並適當區分段落，讓閱讀體驗順暢。回答結束時一樣給予延伸補充或行動建議。"""
        
        user_prompt = question
        sources = []

    try:
        messages = [{"role": "system", "content": system_prompt}]
        
        # 加入對話歷史（最多 5 輪）
        messages.extend(conversation_history[-10:])
        
        # 加入當前問題
        messages.append({"role": "user", "content": user_prompt})
        
        logger.debug(f"💬 問答 API 呼叫: {question[:50]}...")
        answer, usage = call_chat_model(
            messages=messages,
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.5,
            api_key=api_key,
            base_url=base_url
        )
        
        logger.debug(f"✅ 問答完成，來源數: {len(sources)}, Tokens: {usage['total_tokens']}")
        
        # 回傳 tuple 格式 (response_text, usage) 以符合 Parser 的期待
        return answer, usage
        
    except Exception as e:
        logger.error(f"❌ 問答 API 呼叫失敗: {e}")
        return f"抱歉，發生錯誤:{str(e)}", {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
    reraise=True,
)
def extract_keywords(text: str, api_key: str = None, base_url: str = None) -> List[str]:
    """
    從文字中提取關鍵字
    
    Args:
        text: 輸入文字
        api_key: API Key (可選)
        base_url: Base URL (可選)
    
    Returns:
        List[str]: 關鍵字列表
    """
    if not text or len(text) < 10:
        return []
        
    system_prompt = """請從技術文件中提取 3-5 個關鍵字。
【要求】
1. 專注於：產品型號(如 N706)、機台站點(如 Station A)、Defect Code(如 E001)、專有名詞
2. 只輸出關鍵字，用逗號分隔
3. 不要輸出任何解釋文字"""

    user_content = f"【文件內容】\n{text[:2000]}... (下略)\n\n關鍵字："

    try:
        result, _ = call_chat_model(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.3,
            max_tokens=100,
            api_key=api_key,
            base_url=base_url
        )
        
        # 清理結果
        if result:
            keywords = [k.strip() for k in result.replace("、", ",").split(",") if k.strip()]
            return keywords
        return []
        
    except Exception as e:
        logger.error(f"❌ 關鍵字提取失敗: {e}")
        return []


# 測試用
if __name__ == "__main__":
    print("測試 AI API 連接...")
    
    test_text = "這是一個測試投影片，包含機器學習的基本概念。"
    result = analyze_slide(test_text, [], api_mode="text_only")
    print(f"結果: {result[:200]}...")
