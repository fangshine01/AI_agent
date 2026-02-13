"""
重試機制工具 (v2.2.0 Phase 2)

提供：
- LLM API 呼叫重試（RateLimitError / Timeout → 指數退避，最多 3 次）
- SQLite DB 寫入重試（OperationalError / Locked → 100ms 退避，最多 5 次）

使用方式：
    from backend.app.utils.retry import retry_llm_call, retry_db_write

    @retry_llm_call
    async def call_openai(...): ...

    @retry_db_write
    def insert_chat_history(...): ...
"""

import logging
import functools
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

logger = logging.getLogger(__name__)


# ========== LLM API 重試 ==========

# 常見 LLM API 例外類型（動態匹配，避免 import 失敗）
_LLM_RETRY_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    OSError,
)

try:
    import openai
    _LLM_RETRY_EXCEPTIONS += (
        openai.RateLimitError,
        openai.APITimeoutError,
        openai.APIConnectionError,
        openai.InternalServerError,
    )
except ImportError:
    pass

try:
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, DeadlineExceeded
    _LLM_RETRY_EXCEPTIONS += (ResourceExhausted, ServiceUnavailable, DeadlineExceeded)
except ImportError:
    pass


# 裝飾器：LLM API 呼叫重試
retry_llm_call = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),  # 2s → 4s → 8s...
    retry=retry_if_exception_type(_LLM_RETRY_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)


# ========== DB 寫入重試 ==========

import sqlite3

_DB_RETRY_EXCEPTIONS = (
    sqlite3.OperationalError,  # database is locked
)

# 裝飾器：DB 寫入重試
retry_db_write = retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(0.1),  # 固定 100ms
    retry=retry_if_exception_type(_DB_RETRY_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


# ========== 非裝飾器版本（供 inline 使用） ==========

def with_llm_retry(func):
    """
    同步 / 非同步 LLM 重試包裝器

    用法：
        result = with_llm_retry(lambda: client.chat.completions.create(...))
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return retry_llm_call(func)(*args, **kwargs)
    return wrapper


def with_db_retry(func):
    """
    同步 DB 重試包裝器

    用法：
        with_db_retry(lambda: cursor.execute("INSERT ..."))
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return retry_db_write(func)(*args, **kwargs)
    return wrapper
