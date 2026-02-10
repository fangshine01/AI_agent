"""
Token 操作模組
負責 Token 使用量的記錄與統計
"""

import sqlite3
import logging
from typing import Dict, List, Optional
import pathlib
from datetime import datetime, timedelta

# 延遲導入 config 以避免循環引用
# 在函數內部使用時才導入
TOKEN_DB_PATH = None

def _get_token_db_path():
    """延遲載入 TOKEN_DB_PATH 以避免循環引用"""
    global TOKEN_DB_PATH
    if TOKEN_DB_PATH is None:
        import config
        TOKEN_DB_PATH = config.TOKEN_DB_PATH
    return TOKEN_DB_PATH

logger = logging.getLogger(__name__)


def get_connection():
    """取得 Token 資料庫連線"""
    conn = sqlite3.connect(_get_token_db_path())
    return conn


def init_token_db():
    """
    初始化 Token 資料庫
    建立 token_usage 表
    """
    try:
        # 確保目錄存在
        pathlib.Path(_get_token_db_path()).parent.mkdir(parents=True, exist_ok=True)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_name TEXT,
                operation TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Token 資料庫初始化完成")
        
    except Exception as e:
        logger.error(f"❌ Token 資料庫初始化失敗: {e}")
        raise


def log_token_usage(file_name: str, operation: str, usage: Dict):
    """
    記錄 Token 使用量
    
    Args:
        file_name: 相關檔案名稱
        operation: 操作類型 (例如 'search_embedding', 'chat_response')
        usage: Token 使用量字典
    """
    try:
        if not usage or usage.get('total_tokens', 0) == 0:
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO token_usage (
                file_name, operation, prompt_tokens, completion_tokens, total_tokens
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            file_name,
            operation,
            usage.get('prompt_tokens', 0),
            usage.get('completion_tokens', 0),
            usage.get('total_tokens', 0)
        ))
        
        conn.commit()
        conn.close()
        logger.debug(f"📝 Token 已記錄: {operation} - {usage.get('total_tokens', 0)}")
        
    except Exception as e:
        logger.error(f"❌ 記錄 Token 失敗: {e}")


def get_token_stats(days: int = 30) -> Dict:
    """
    取得 Token 統計資訊
    
    Args:
        days: 統計最近幾天
    
    Returns:
        Dict: 包含總量、分類統計等
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. 總量統計
        if days:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            time_condition = "WHERE timestamp >= ?"
            params = (start_date,)
        else:
            time_condition = ""
            params = ()
        
        cursor.execute(f"""
            SELECT 
                SUM(total_tokens),
                SUM(prompt_tokens),
                SUM(completion_tokens)
            FROM token_usage
            {time_condition}
        """, params)
        
        row = cursor.fetchone()
        stats = {
            'total_tokens': row[0] or 0,
            'total_prompt_tokens': row[1] or 0,
            'total_completion_tokens': row[2] or 0,
            'period_days': days
        }
        
        # 2. 按操作統計
        cursor.execute(f"""
            SELECT operation, SUM(total_tokens)
            FROM token_usage
            {time_condition}
            GROUP BY operation
            ORDER BY SUM(total_tokens) DESC
        """, params)
        
        stats['by_operation'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 3. 最近使用記錄
        cursor.execute(f"""
            SELECT strftime('%s', timestamp), file_name, operation, total_tokens
            FROM token_usage
            {time_condition}
            ORDER BY timestamp DESC
            LIMIT 20
        """, params)
        
        stats['recent_usage'] = [
            {
                'timestamp': float(row[0]) if row[0] else 0,
                'file_name': row[1],
                'operation': row[2],
                'total_tokens': row[3]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return stats
        
    except sqlite3.OperationalError as e:
        # 資料庫可能不存在或資料表缺失 (即使 init_token_db 跑過也可能被手動刪除)
        logger.warning(f"Token 資料庫存取異常 (可能是全新的或者是資料庫遺失): {e}")
        # 嘗試重新初始化
        try:
            init_token_db()
        except:
            pass
            
        return {
            'total_tokens': 0,
            'total_prompt_tokens': 0,
            'total_completion_tokens': 0,
            'by_operation': {},
            'recent_usage': [],
            'period_days': days
        }
            
    except Exception as e:
        logger.error(f"❌ 取得 Token 統計失敗: {e}")
        return {
            'total_tokens': 0,
            'total_prompt_tokens': 0,
            'total_completion_tokens': 0,
            'by_operation': {},
            'recent_usage': [],
            'period_days': days,
            'error': str(e)
        }


# 初始化時確保資料表存在
init_token_db()
