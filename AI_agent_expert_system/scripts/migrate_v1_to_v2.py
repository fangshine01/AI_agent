"""
v1 to v2 資料遷移腳本 (Phase 4)

功能:
1. 將舊版 data/knowledge.db 中的 documents、vec_chunks 遷移到 v2 資料庫
2. 將舊版 data/tokenrecord.db 遷移到 v2 Token 資料庫
3. 自動檢測 schema 差異並安全遷移
4. 遷移前自動備份目標 DB

使用方式:
    python scripts/migrate_v1_to_v2.py --check       # 僅檢查，不遷移
    python scripts/migrate_v1_to_v2.py --migrate      # 執行遷移
    python scripts/migrate_v1_to_v2.py --migrate --force  # 強制遷移（覆蓋已存在的資料）
"""

import argparse
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# 確保可以匯入專案模組
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ========== 路徑設定 ==========

# 舊版 (v1) 資料庫路徑
V1_KNOWLEDGE_DB = PROJECT_ROOT / "data" / "knowledge.db"
V1_TOKEN_DB = PROJECT_ROOT / "data" / "tokenrecord.db"

# 新版 (v2) 資料庫路徑（與 backend/config.py 一致）
V2_KNOWLEDGE_DB = PROJECT_ROOT / "backend" / "data" / "documents" / "knowledge_v2.db"
V2_TOKEN_DB = PROJECT_ROOT / "backend" / "data" / "documents" / "tokenrecord_v2.db"

# 備份目錄
BACKUP_DIR = PROJECT_ROOT / "backend" / "data" / "backups" / "migration"

# ========== 日誌設定 ==========

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("migrate_v1_to_v2")


# ========== 輔助函式 ==========


def get_table_info(db_path: Path) -> dict:
    """取得資料庫中所有表格的資訊"""
    if not db_path.exists():
        return {}

    info = {}
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 取得所有表格名稱
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [(row[1], row[2]) for row in cursor.fetchall()]

            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]

            info[table] = {
                "columns": columns,
                "row_count": row_count,
            }

        conn.close()
    except Exception as e:
        logger.error(f"讀取 {db_path} 失敗: {e}")

    return info


def backup_database(db_path: Path) -> Path:
    """備份資料庫檔案"""
    if not db_path.exists():
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{db_path.stem}_{timestamp}{db_path.suffix}"
    backup_path = BACKUP_DIR / backup_name

    shutil.copy2(str(db_path), str(backup_path))
    logger.info(f"  ✅ 已備份: {db_path.name} → {backup_path}")
    return backup_path


def migrate_table(src_conn: sqlite3.Connection, dst_conn: sqlite3.Connection,
                  table: str, force: bool = False) -> dict:
    """
    遷移單一表格的資料

    Args:
        src_conn: 來源 DB 連線
        dst_conn: 目標 DB 連線
        table: 表格名稱
        force: True 時先刪除目標表已有資料

    Returns:
        dict: {migrated: int, skipped: int, errors: []}
    """
    result = {"migrated": 0, "skipped": 0, "errors": []}

    try:
        src_cursor = src_conn.cursor()
        dst_cursor = dst_conn.cursor()

        # 確認來源表存在
        src_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if not src_cursor.fetchone():
            result["errors"].append(f"來源表 {table} 不存在")
            return result

        # 確認目標表存在
        dst_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if not dst_cursor.fetchone():
            result["errors"].append(f"目標表 {table} 不存在（請先初始化 v2 資料庫）")
            return result

        # 取得來源表欄位
        src_cursor.execute(f"PRAGMA table_info({table})")
        src_columns = [row[1] for row in src_cursor.fetchall()]

        # 取得目標表欄位
        dst_cursor.execute(f"PRAGMA table_info({table})")
        dst_columns = [row[1] for row in dst_cursor.fetchall()]

        # 找出共同欄位（排除 auto-increment id）
        common_columns = [c for c in src_columns if c in dst_columns and c != "id"]

        if not common_columns:
            result["errors"].append(f"表 {table} 無共同欄位可遷移")
            return result

        # 強制模式：清空目標表
        if force:
            dst_cursor.execute(f"DELETE FROM {table}")
            logger.info(f"  ⚠️ 已清空目標表 {table}")

        # 檢查目標表是否有資料
        dst_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        existing_count = dst_cursor.fetchone()[0]
        if existing_count > 0 and not force:
            logger.warning(
                f"  ⏩ 跳過 {table}: 目標表已有 {existing_count} 筆資料（使用 --force 強制覆蓋）"
            )
            result["skipped"] = existing_count
            return result

        # 讀取來源資料
        columns_str = ", ".join(common_columns)
        placeholders = ", ".join(["?"] * len(common_columns))
        src_cursor.execute(f"SELECT {columns_str} FROM {table}")
        rows = src_cursor.fetchall()

        # 寫入目標表
        if rows:
            dst_cursor.executemany(
                f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})", rows
            )
            dst_conn.commit()
            result["migrated"] = len(rows)
            logger.info(f"  ✅ 已遷移 {table}: {len(rows)} 筆")
        else:
            logger.info(f"  ℹ️ {table}: 來源表無資料")

    except Exception as e:
        result["errors"].append(f"遷移 {table} 失敗: {e}")
        logger.error(f"  ❌ 遷移 {table} 失敗: {e}")

    return result


# ========== 主要功能 ==========


def check_migration():
    """檢查遷移狀態，顯示 v1 與 v2 資料庫差異"""
    print("=" * 60)
    print("  v1 → v2 資料庫遷移檢查")
    print("=" * 60)

    # 檢查 v1 資料庫
    print(f"\n📂 v1 Knowledge DB: {V1_KNOWLEDGE_DB}")
    if V1_KNOWLEDGE_DB.exists():
        v1_info = get_table_info(V1_KNOWLEDGE_DB)
        size_mb = V1_KNOWLEDGE_DB.stat().st_size / (1024 * 1024)
        print(f"   大小: {size_mb:.2f} MB | 表格數: {len(v1_info)}")
        for table, info in v1_info.items():
            print(f"   - {table}: {info['row_count']} 筆, {len(info['columns'])} 欄位")
    else:
        print("   ❌ 不存在（無需遷移）")

    print(f"\n📂 v1 Token DB: {V1_TOKEN_DB}")
    if V1_TOKEN_DB.exists():
        v1_token = get_table_info(V1_TOKEN_DB)
        size_mb = V1_TOKEN_DB.stat().st_size / (1024 * 1024)
        print(f"   大小: {size_mb:.2f} MB | 表格數: {len(v1_token)}")
        for table, info in v1_token.items():
            print(f"   - {table}: {info['row_count']} 筆")
    else:
        print("   ❌ 不存在（無需遷移）")

    # 檢查 v2 資料庫
    print(f"\n📂 v2 Knowledge DB: {V2_KNOWLEDGE_DB}")
    if V2_KNOWLEDGE_DB.exists():
        v2_info = get_table_info(V2_KNOWLEDGE_DB)
        size_mb = V2_KNOWLEDGE_DB.stat().st_size / (1024 * 1024)
        print(f"   大小: {size_mb:.2f} MB | 表格數: {len(v2_info)}")
        for table, info in v2_info.items():
            print(f"   - {table}: {info['row_count']} 筆, {len(info['columns'])} 欄位")
    else:
        print("   ⚠️ 不存在（將在首次啟動時自動建立）")

    print(f"\n📂 v2 Token DB: {V2_TOKEN_DB}")
    if V2_TOKEN_DB.exists():
        v2_token = get_table_info(V2_TOKEN_DB)
        size_mb = V2_TOKEN_DB.stat().st_size / (1024 * 1024)
        print(f"   大小: {size_mb:.2f} MB | 表格數: {len(v2_token)}")
    else:
        print("   ⚠️ 不存在（將在首次啟動時自動建立）")

    # 建議
    print("\n" + "=" * 60)
    need_migration = V1_KNOWLEDGE_DB.exists() or V1_TOKEN_DB.exists()
    if need_migration:
        print("💡 建議: 執行 `python scripts/migrate_v1_to_v2.py --migrate` 進行遷移")
    else:
        print("✅ 無 v1 資料庫需要遷移")
    print("=" * 60)


def execute_migration(force: bool = False):
    """執行完整遷移流程"""
    print("=" * 60)
    print("  v1 → v2 資料庫遷移")
    print("=" * 60)

    results = {"knowledge": {}, "token": {}}

    # --- 遷移 Knowledge DB ---
    print(f"\n📦 Knowledge DB 遷移")
    if not V1_KNOWLEDGE_DB.exists():
        print("   ⏩ v1 Knowledge DB 不存在，跳過")
    elif not V2_KNOWLEDGE_DB.exists():
        print("   ❌ v2 Knowledge DB 不存在，請先啟動一次系統以初始化資料庫")
    else:
        # 備份 v2
        backup_database(V2_KNOWLEDGE_DB)

        src_conn = sqlite3.connect(str(V1_KNOWLEDGE_DB))
        dst_conn = sqlite3.connect(str(V2_KNOWLEDGE_DB))

        # 啟用 WAL 模式（確保寫入安全）
        dst_conn.execute("PRAGMA journal_mode=WAL")

        # 遷移主要表格
        tables_to_migrate = [
            "documents",
            "vec_chunks",
            "doc_knowledge",
            "doc_training",
            "doc_procedure",
            "doc_troubleshooting",
        ]

        for table in tables_to_migrate:
            result = migrate_table(src_conn, dst_conn, table, force=force)
            results["knowledge"][table] = result

        src_conn.close()
        dst_conn.close()

    # --- 遷移 Token DB ---
    print(f"\n📦 Token DB 遷移")
    if not V1_TOKEN_DB.exists():
        print("   ⏩ v1 Token DB 不存在，跳過")
    elif not V2_TOKEN_DB.exists():
        print("   ❌ v2 Token DB 不存在，請先啟動一次系統以初始化資料庫")
    else:
        backup_database(V2_TOKEN_DB)

        src_conn = sqlite3.connect(str(V1_TOKEN_DB))
        dst_conn = sqlite3.connect(str(V2_TOKEN_DB))
        dst_conn.execute("PRAGMA journal_mode=WAL")

        result = migrate_table(src_conn, dst_conn, "token_usage", force=force)
        results["token"]["token_usage"] = result

        src_conn.close()
        dst_conn.close()

    # 遷移摘要
    print("\n" + "=" * 60)
    print("  遷移摘要")
    print("=" * 60)

    total_migrated = 0
    total_skipped = 0
    total_errors = 0

    for db_name, tables in results.items():
        for table_name, r in tables.items():
            total_migrated += r.get("migrated", 0)
            total_skipped += r.get("skipped", 0)
            total_errors += len(r.get("errors", []))

    print(f"  ✅ 已遷移: {total_migrated} 筆")
    print(f"  ⏩ 已跳過: {total_skipped} 筆")
    print(f"  ❌ 錯誤:   {total_errors} 個")

    if total_errors == 0:
        print("\n🎉 遷移完成！舊版 v1 資料庫可安全保留或刪除。")
    else:
        print("\n⚠️ 遷移過程中有錯誤，請檢查日誌。")

    return results


# ========== 主程式 ==========


def main():
    parser = argparse.ArgumentParser(
        description="AI Expert System v1 → v2 資料庫遷移工具"
    )
    parser.add_argument("--check", action="store_true", help="僅檢查遷移狀態，不執行遷移")
    parser.add_argument("--migrate", action="store_true", help="執行資料遷移")
    parser.add_argument(
        "--force",
        action="store_true",
        help="強制遷移（清空目標表後再寫入）",
    )

    args = parser.parse_args()

    if not any([args.check, args.migrate]):
        parser.print_help()
        return

    if args.check:
        check_migration()

    if args.migrate:
        if args.force:
            print("\n⚠️ 警告: --force 模式會清空目標 v2 資料庫中的現有資料！")
            confirm = input("確定要繼續嗎？(yes/no): ")
            if confirm.lower() not in ["yes", "y"]:
                print("取消遷移。")
                return

        execute_migration(force=args.force)


if __name__ == "__main__":
    main()
