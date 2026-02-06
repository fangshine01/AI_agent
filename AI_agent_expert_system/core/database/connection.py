"""
資料庫連線管理模組
負責資料庫連線與 sqlite-vec 擴充套件載入
"""

import sqlite3
import os
import logging
import config  # 匯入 config 模組

logger = logging.getLogger(__name__)

# 資料庫路徑 (改用 config 設定)
DB_PATH = config.DB_PATH


def get_connection() -> sqlite3.Connection:
    """
    取得資料庫連線並載入 vec0 擴充套件
    
    Returns:
        sqlite3.Connection: 已載入 sqlite-vec 的資料庫連線
    """
    try:
        # 自動檢查並初始化
        if not os.path.exists(DB_PATH):
            logger.warning(f"資料庫不存在，嘗試初始化: {DB_PATH}")
            # 確保目錄存在
            db_dir = os.path.dirname(DB_PATH)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # 使用初始連線建立表格 (避免遞迴呼叫 get_connection -> init_database -> get_connection)
            # 這裡我們直接呼叫 init_database，但要確保 init_database 內部能處理首次連線
            # 修改策略：先建立檔案，再呼叫 init_database
            
            # 也可以簡單地先 connect 一次確保檔案建立
            sqlite3.connect(DB_PATH).close()
            init_database()

        conn = sqlite3.connect(DB_PATH)
        
        # 載入 sqlite-vec 擴充套件
        conn.enable_load_extension(True)
        try:
            import sqlite_vec
            vec_path = sqlite_vec.loadable_path()
            conn.load_extension(vec_path)
            logger.debug("✅ sqlite-vec 擴充套件已載入")
        except ImportError:
            raise Exception("無法載入 sqlite-vec 擴充套件。請確認已安裝: pip install sqlite-vec")
        except Exception as e:
            raise Exception(f"載入 sqlite-vec 擴充套件失敗: {e}")
        finally:
            conn.enable_load_extension(False)
        
        return conn
        
    except Exception as e:
        logger.error(f"資料庫連線失敗: {e}")
        raise


def init_database():
    """
    初始化資料庫結構
    呼叫 schema 模組建立所有資料表
    """
    from . import schema
    schema.create_all_tables()
    logger.info("✅ 資料庫初始化完成")


if __name__ == "__main__":
    # 測試連線
    try:
        conn = get_connection()
        print("✅ 資料庫連線測試成功")
        conn.close()
    except Exception as e:
        print(f"❌ 資料庫連線測試失敗: {e}")
