"""
Token 統計服務
將 Admin Router 中的 _build_enhanced_token_stats 原始 SQL 邏輯
抽離為獨立 Service，保持 Router 端點乾淨。
"""

import sqlite3
import logging
from datetime import datetime, timedelta

import backend.config as cfg

logger = logging.getLogger(__name__)


def build_enhanced_token_stats(raw_stats: dict, days: int) -> dict:
    """
    將 core/database/token_ops 原始格式轉為 Admin UI 期望的增強格式

    原始格式: {total_tokens, total_prompt_tokens, by_operation: {}, recent_usage: []}
    增強格式: {summary, daily, by_model, by_operation, by_user, by_hour, top_files}
    """
    total_tokens = raw_stats.get("total_tokens", 0)
    total_prompt = raw_stats.get("total_prompt_tokens", 0)
    total_completion = raw_stats.get("total_completion_tokens", 0)

    # summary 摘要
    estimated_cost = (total_prompt * 0.15 + total_completion * 0.60) / 1_000_000

    recent = raw_stats.get("recent_usage", [])
    total_requests = len(recent) if recent else 0

    today_tokens = 0
    daily_data: list[dict] = []
    by_model_data: list[dict] = []
    by_user_data: list[dict] = []
    by_hour_data: list[dict] = []
    top_files_data: list[dict] = []

    try:
        conn = sqlite3.connect(cfg.TOKEN_DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if days:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            time_cond = "WHERE timestamp >= ?"
            params: tuple = (start_date,)
        else:
            time_cond = ""
            params = ()

        today_tokens = _query_today_tokens(cursor)
        total_requests = _query_total_requests(cursor, time_cond, params)
        daily_data = _query_daily(cursor, time_cond, params)
        by_model_data = _query_by_model(cursor, time_cond, params)
        by_user_data = _query_by_user(cursor, time_cond, params)
        by_hour_data = _query_by_hour(cursor, time_cond, params)
        top_files_data = _query_top_files(cursor, time_cond, params)

        conn.close()
    except Exception as e:
        logger.warning(f"[TokenStats] Token DB 增強查詢失敗（退化使用基本資料）: {e}")

    by_operation_data = _normalize_by_operation(raw_stats)

    if not by_model_data and by_operation_data:
        by_model_data = [{"model": item["operation"], "tokens": item["tokens"]} for item in by_operation_data]

    return {
        "summary": {
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "estimated_cost": round(estimated_cost, 4),
            "today_tokens": today_tokens,
        },
        "daily": daily_data,
        "by_model": by_model_data,
        "by_operation": by_operation_data,
        "by_user": by_user_data,
        "by_hour": by_hour_data,
        "top_files": top_files_data,
    }


# ---------- private helpers ----------

def _query_today_tokens(cursor: sqlite3.Cursor) -> int:
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT COALESCE(SUM(total_tokens), 0) FROM token_usage WHERE DATE(timestamp) = ?",
        (today_str,),
    )
    return cursor.fetchone()[0] or 0


def _query_total_requests(cursor: sqlite3.Cursor, time_cond: str, params: tuple) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM token_usage {time_cond}", params)
    return cursor.fetchone()[0] or 0


def _query_daily(cursor: sqlite3.Cursor, time_cond: str, params: tuple) -> list[dict]:
    cursor.execute(f"""
        SELECT DATE(timestamp) as date, SUM(total_tokens) as tokens
        FROM token_usage {time_cond}
        GROUP BY DATE(timestamp) ORDER BY date
    """, params)
    return [{"date": row["date"], "tokens": row["tokens"]} for row in cursor.fetchall()]


def _query_by_model(cursor: sqlite3.Cursor, time_cond: str, params: tuple) -> list[dict]:
    try:
        cursor.execute(f"""
            SELECT model as model_name, SUM(total_tokens) as tokens
            FROM token_usage {time_cond}
            GROUP BY model ORDER BY tokens DESC
        """, params)
        return [{"model": row["model_name"] or "unknown", "tokens": row["tokens"]} for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []


def _query_by_user(cursor: sqlite3.Cursor, time_cond: str, params: tuple) -> list[dict]:
    try:
        cursor.execute(f"""
            SELECT user_id, SUM(total_tokens) as tokens, COUNT(*) as requests
            FROM token_usage {time_cond}
            GROUP BY user_id ORDER BY tokens DESC
        """, params)
        return [
            {"user_id": row["user_id"] or "anonymous", "tokens": row["tokens"], "requests": row["requests"]}
            for row in cursor.fetchall()
        ]
    except sqlite3.OperationalError:
        return []


def _query_by_hour(cursor: sqlite3.Cursor, time_cond: str, params: tuple) -> list[dict]:
    cursor.execute(f"""
        SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, SUM(total_tokens) as tokens
        FROM token_usage {time_cond}
        GROUP BY hour ORDER BY hour
    """, params)
    return [{"hour": row["hour"], "tokens": row["tokens"]} for row in cursor.fetchall()]


def _query_top_files(cursor: sqlite3.Cursor, time_cond: str, params: tuple) -> list[dict]:
    cursor.execute(f"""
        SELECT file_name, SUM(total_tokens) as tokens
        FROM token_usage {time_cond}
        GROUP BY file_name ORDER BY tokens DESC LIMIT 10
    """, params)
    return [
        {"file_name": row["file_name"] or "N/A", "tokens": row["tokens"]}
        for row in cursor.fetchall()
    ]


def _normalize_by_operation(raw_stats: dict) -> list[dict]:
    raw_ops = raw_stats.get("by_operation", {})
    if isinstance(raw_ops, dict):
        return [{"operation": k, "tokens": v} for k, v in raw_ops.items()]
    elif isinstance(raw_ops, list):
        return raw_ops
    return []
