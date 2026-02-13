"""
自動清理腳本 - 適用於 Windows Task Scheduler 排程
功能:
1. 清理過期 Session（超過 24h 未活動）
2. 清理過期暫存上傳檔案（超過 30 天）
3. 清理過大的日誌檔案（選用）

建議排程: 每天凌晨 2:00 執行
Task Scheduler 指令:
  python scripts/cleanup.py --all
"""

import argparse
import os
import sys
import time
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta

# 確保可以匯入 backend 模組
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ========== 設定 ==========

# Session 過期時間（秒）- 預設 24 小時
SESSION_TTL = int(os.getenv("SESSION_TTL", "86400"))

# 上傳檔案保留天數
UPLOAD_RETAIN_DAYS = int(os.getenv("UPLOAD_RETAIN_DAYS", "30"))

# 資料庫路徑（與 backend/config.py 一致：backend/data/documents/）
DB_DIR = PROJECT_ROOT / "backend" / "data" / "documents"
KNOWLEDGE_DB = DB_DIR / "knowledge_v2.db"
TOKEN_DB = DB_DIR / "tokenrecord_v2.db"

# 上傳目錄
UPLOAD_DIRS = [
    PROJECT_ROOT / "backend" / "data" / "uploads",
    PROJECT_ROOT / "backend" / "data" / "temp",
]

# 日誌目錄
LOG_DIR = PROJECT_ROOT / "logs"

# ========== 日誌設定 ==========

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            LOG_DIR / "cleanup.log" if LOG_DIR.exists() else "cleanup.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("cleanup")


# ========== 清理函式 ==========


def cleanup_expired_sessions() -> dict:
    """清理過期的 Session 記錄（不刪除 chat_history）"""
    result = {"deleted": 0, "errors": []}

    if not KNOWLEDGE_DB.exists():
        logger.warning(f"資料庫不存在: {KNOWLEDGE_DB}")
        result["errors"].append("資料庫不存在")
        return result

    try:
        conn = sqlite3.connect(str(KNOWLEDGE_DB))
        cursor = conn.cursor()

        # 計算過期時間點
        cutoff = datetime.utcnow() - timedelta(seconds=SESSION_TTL)
        cutoff_str = cutoff.isoformat()

        # 查詢即將刪除的 session 數量
        cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE last_activity_at < ?",
            (cutoff_str,),
        )
        count = cursor.fetchone()[0]

        if count > 0:
            # 刪除過期 session
            cursor.execute(
                "DELETE FROM sessions WHERE last_activity_at < ?",
                (cutoff_str,),
            )
            conn.commit()
            result["deleted"] = count
            logger.info(f"已清理 {count} 個過期 Session（截止: {cutoff_str}）")
        else:
            logger.info("沒有過期的 Session 需要清理")

        conn.close()

    except Exception as e:
        logger.error(f"清理 Session 失敗: {e}")
        result["errors"].append(str(e))

    return result


def cleanup_old_uploads() -> dict:
    """清理超過保留期限的暫存上傳檔案"""
    result = {"deleted_files": 0, "freed_bytes": 0, "errors": []}

    cutoff = datetime.now() - timedelta(days=UPLOAD_RETAIN_DAYS)

    for upload_dir in UPLOAD_DIRS:
        if not upload_dir.exists():
            logger.info(f"目錄不存在，跳過: {upload_dir}")
            continue

        try:
            for file_path in upload_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                # 檢查檔案修改時間
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff:
                    file_size = file_path.stat().st_size
                    try:
                        file_path.unlink()
                        result["deleted_files"] += 1
                        result["freed_bytes"] += file_size
                        logger.info(f"已刪除: {file_path} ({file_size:,} bytes)")
                    except PermissionError:
                        logger.warning(f"無法刪除（檔案被鎖定）: {file_path}")
                        result["errors"].append(f"無法刪除: {file_path}")

        except Exception as e:
            logger.error(f"清理目錄 {upload_dir} 失敗: {e}")
            result["errors"].append(str(e))

    freed_mb = result["freed_bytes"] / (1024 * 1024)
    logger.info(
        f"上傳清理完成: 刪除 {result['deleted_files']} 個檔案, "
        f"釋放 {freed_mb:.2f} MB"
    )
    return result


def cleanup_old_logs(max_age_days: int = 90) -> dict:
    """清理超過指定天數的日誌檔案"""
    result = {"deleted_files": 0, "freed_bytes": 0, "errors": []}

    if not LOG_DIR.exists():
        logger.info("日誌目錄不存在，跳過")
        return result

    cutoff = datetime.now() - timedelta(days=max_age_days)

    try:
        for log_file in LOG_DIR.glob("*.log*"):
            if not log_file.is_file():
                continue

            # 不刪除當前清理日誌
            if log_file.name == "cleanup.log":
                continue

            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                file_size = log_file.stat().st_size
                try:
                    log_file.unlink()
                    result["deleted_files"] += 1
                    result["freed_bytes"] += file_size
                    logger.info(f"已刪除日誌: {log_file.name} ({file_size:,} bytes)")
                except PermissionError:
                    logger.warning(f"無法刪除日誌: {log_file}")

    except Exception as e:
        logger.error(f"清理日誌失敗: {e}")
        result["errors"].append(str(e))

    return result


def vacuum_databases() -> dict:
    """對資料庫執行 VACUUM 以回收空間"""
    result = {"vacuumed": [], "errors": []}

    for db_path in [KNOWLEDGE_DB, TOKEN_DB]:
        if not db_path.exists():
            continue

        try:
            # 記錄 VACUUM 前的大小
            size_before = db_path.stat().st_size

            conn = sqlite3.connect(str(db_path))
            conn.execute("VACUUM")
            conn.close()

            size_after = db_path.stat().st_size
            saved = size_before - size_after
            saved_mb = saved / (1024 * 1024)

            result["vacuumed"].append({
                "db": db_path.name,
                "before_mb": round(size_before / (1024 * 1024), 2),
                "after_mb": round(size_after / (1024 * 1024), 2),
                "saved_mb": round(saved_mb, 2),
            })
            logger.info(
                f"VACUUM {db_path.name}: {round(size_before / (1024 * 1024), 2)} MB → "
                f"{round(size_after / (1024 * 1024), 2)} MB (節省 {round(saved_mb, 2)} MB)"
            )

        except Exception as e:
            logger.error(f"VACUUM {db_path.name} 失敗: {e}")
            result["errors"].append(str(e))

    return result


# ========== 主程式 ==========


def main():
    parser = argparse.ArgumentParser(description="AI Expert System 自動清理工具")
    parser.add_argument("--sessions", action="store_true", help="清理過期 Session")
    parser.add_argument("--uploads", action="store_true", help="清理過期上傳檔案")
    parser.add_argument("--logs", action="store_true", help="清理過期日誌檔案")
    parser.add_argument("--vacuum", action="store_true", help="資料庫 VACUUM 整理")
    parser.add_argument("--all", action="store_true", help="執行所有清理任務")
    parser.add_argument(
        "--log-max-days",
        type=int,
        default=90,
        help="日誌保留天數（預設 90 天）",
    )

    args = parser.parse_args()

    # 如果沒有指定任何參數，顯示 help
    if not any([args.sessions, args.uploads, args.logs, args.vacuum, args.all]):
        parser.print_help()
        return

    logger.info("=" * 60)
    logger.info(f"開始自動清理 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    start_time = time.time()
    results = {}

    if args.sessions or args.all:
        logger.info("[1/4] 清理過期 Session...")
        results["sessions"] = cleanup_expired_sessions()

    if args.uploads or args.all:
        logger.info("[2/4] 清理過期上傳檔案...")
        results["uploads"] = cleanup_old_uploads()

    if args.logs or args.all:
        logger.info("[3/4] 清理過期日誌...")
        results["logs"] = cleanup_old_logs(max_age_days=args.log_max_days)

    if args.vacuum or args.all:
        logger.info("[4/4] 資料庫 VACUUM...")
        results["vacuum"] = vacuum_databases()

    elapsed = time.time() - start_time
    logger.info(f"清理完成，耗時: {elapsed:.2f} 秒")

    # 摘要報告
    logger.info("=" * 60)
    logger.info("清理摘要:")
    if "sessions" in results:
        r = results["sessions"]
        logger.info(f"  Session: 刪除 {r['deleted']} 個")
    if "uploads" in results:
        r = results["uploads"]
        freed = r["freed_bytes"] / (1024 * 1024)
        logger.info(f"  上傳檔案: 刪除 {r['deleted_files']} 個, 釋放 {freed:.2f} MB")
    if "logs" in results:
        r = results["logs"]
        freed = r["freed_bytes"] / (1024 * 1024)
        logger.info(f"  日誌: 刪除 {r['deleted_files']} 個, 釋放 {freed:.2f} MB")
    if "vacuum" in results:
        r = results["vacuum"]
        logger.info(f"  VACUUM: 處理 {len(r['vacuumed'])} 個資料庫")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
