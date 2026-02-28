"""
Prometheus Metrics 監控中介層 (v2.3.0 Phase 5)

功能：
- HTTP 請求計數器 (依方法、路徑、狀態碼)
- 請求延遲直方圖
- 進行中請求量規
- 錯誤率追蹤
- /metrics 端點暴露 Prometheus 格式指標

注意：使用輕量級內建收集器，無需安裝 prometheus_client 套件
"""

import time
import logging
import threading
from collections import defaultdict
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse

logger = logging.getLogger(__name__)

# ========== 輕量級 Prometheus 兼容指標收集器 ==========

# 執行緒安全鎖
_lock = threading.Lock()

# 計數器: {(method, path, status_code): count}
_request_total: Dict[Tuple[str, str, str], int] = defaultdict(int)

# 延遲直方圖: {(method, path): [latency_values]}
_request_latency: Dict[Tuple[str, str], List[float]] = defaultdict(list)

# 進行中請求: {(method, path): count}
_requests_in_progress: Dict[Tuple[str, str], int] = defaultdict(int)

# 錯誤計數: {(method, path, error_type): count}
_error_total: Dict[Tuple[str, str, str], int] = defaultdict(int)

# 延遲直方圖桶邊界 (秒)
HISTOGRAM_BUCKETS = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")]


def _normalize_path(path: str) -> str:
    """
    正規化 URL 路徑，避免高基數指標
    將動態路徑段 (UUID, 數字 ID) 統一為佔位符
    """
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        # 替換 UUID 格式
        if len(part) == 36 and part.count("-") == 4:
            normalized.append("{id}")
        # 替換純數字 ID
        elif part.isdigit():
            normalized.append("{id}")
        # 替換 BYOK 身份 hash (16 字元 hex)
        elif len(part) == 16 and all(c in "0123456789abcdef" for c in part.lower()):
            normalized.append("{identity}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized)


def record_request(method: str, path: str, status_code: int, latency: float):
    """記錄單次 HTTP 請求指標"""
    normalized = _normalize_path(path)
    status_str = str(status_code)

    with _lock:
        _request_total[(method, normalized, status_str)] += 1
        _request_latency[(method, normalized)].append(latency)

        # 限制延遲陣列大小，保留最近 10000 筆
        if len(_request_latency[(method, normalized)]) > 10000:
            _request_latency[(method, normalized)] = _request_latency[(method, normalized)][-5000:]

        # 記錄 4xx/5xx 錯誤
        if status_code >= 400:
            error_type = "client_error" if status_code < 500 else "server_error"
            _error_total[(method, normalized, error_type)] += 1


def increment_in_progress(method: str, path: str):
    """增加進行中請求計數"""
    normalized = _normalize_path(path)
    with _lock:
        _requests_in_progress[(method, normalized)] += 1


def decrement_in_progress(method: str, path: str):
    """減少進行中請求計數"""
    normalized = _normalize_path(path)
    with _lock:
        _requests_in_progress[(method, normalized)] = max(
            0, _requests_in_progress[(method, normalized)] - 1
        )


def get_metrics_text() -> str:
    """
    生成 Prometheus 文字格式 (text/plain; version=0.0.4)
    相容 Prometheus scrape 端點
    """
    lines = []

    with _lock:
        # 1. 請求計數器
        lines.append("# HELP http_requests_total 累計 HTTP 請求總數")
        lines.append("# TYPE http_requests_total counter")
        for (method, path, status), count in sorted(_request_total.items()):
            lines.append(
                f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )

        # 2. 延遲直方圖
        lines.append("")
        lines.append("# HELP http_request_duration_seconds HTTP 請求延遲直方圖")
        lines.append("# TYPE http_request_duration_seconds histogram")
        for (method, path), latencies in sorted(_request_latency.items()):
            if not latencies:
                continue
            total_sum = sum(latencies)
            total_count = len(latencies)

            # 生成桶 (bucket)
            for bucket in HISTOGRAM_BUCKETS:
                bucket_count = sum(1 for lat in latencies if lat <= bucket)
                bucket_label = "+Inf" if bucket == float("inf") else f"{bucket}"
                lines.append(
                    f'http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="{bucket_label}"}} {bucket_count}'
                )
            lines.append(
                f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total_sum:.6f}'
            )
            lines.append(
                f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {total_count}'
            )

        # 3. 進行中請求
        lines.append("")
        lines.append("# HELP http_requests_in_progress 目前進行中的 HTTP 請求數")
        lines.append("# TYPE http_requests_in_progress gauge")
        for (method, path), count in sorted(_requests_in_progress.items()):
            if count > 0:
                lines.append(
                    f'http_requests_in_progress{{method="{method}",path="{path}"}} {count}'
                )

        # 4. 錯誤計數
        lines.append("")
        lines.append("# HELP http_errors_total 累計 HTTP 錯誤總數")
        lines.append("# TYPE http_errors_total counter")
        for (method, path, error_type), count in sorted(_error_total.items()):
            lines.append(
                f'http_errors_total{{method="{method}",path="{path}",type="{error_type}"}} {count}'
            )

    return "\n".join(lines) + "\n"


# ========== Starlette 中介層 ==========

class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Prometheus 指標收集中介層

    自動記錄所有 HTTP 請求的：
    - 請求計數 (依 method/path/status)
    - 延遲分佈 (直方圖)
    - 進行中請求數 (量規)
    - 錯誤率 (4xx/5xx)
    """

    # 排除 /metrics 本身，避免自我參照汙染指標
    EXCLUDE_PATHS = {"/metrics", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # 排除監控端點自身
        if path in self.EXCLUDE_PATHS:
            return await call_next(request)

        increment_in_progress(method, path)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            latency = time.perf_counter() - start_time
            record_request(method, path, response.status_code, latency)
            return response
        except Exception as exc:
            latency = time.perf_counter() - start_time
            record_request(method, path, 500, latency)
            raise
        finally:
            decrement_in_progress(method, path)


# ========== FastAPI 路由 ==========

def create_metrics_router():
    """建立 /metrics 路由，供 Prometheus 抓取"""
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/metrics")
    async def metrics():
        """
        Prometheus 指標端點

        Returns:
            Prometheus 文字格式的指標資料，包含：
            - http_requests_total: 累計請求總數 (counter)
            - http_request_duration_seconds: 延遲直方圖 (histogram)
            - http_requests_in_progress: 進行中請求數 (gauge)
            - http_errors_total: 錯誤總數 (counter)

        使用方式：
            在 Prometheus 設定檔中加入：
            ```yaml
            scrape_configs:
              - job_name: 'ai-expert-system'
                static_configs:
                  - targets: ['localhost:8000']
            ```
        """
        return PlainTextResponse(
            content=get_metrics_text(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    return router
