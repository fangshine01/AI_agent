"""
備份恢復測試腳本 (Phase 4)

功能:
1. 自動選取最近一份備份
2. 恢復到臨時目錄
3. 執行完整性檢查（表格、記錄數、WAL 模式）
4. 比較與正式 DB 的差異
5. 清理臨時檔案

使用方式:
    python scripts/test_backup_recovery.py                # 自動測試最近備份
    python scripts/test_backup_recovery.py --backup-dir D:\backups  # 指定備份目錄
"""

import argparse
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 確保可以匯入專案模組
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ========== 路徑設定 ==========

# 正式資料庫路徑
LIVE_KNOWLEDGE_DB = PROJECT_ROOT / "backend" / "data" / "documents" / "knowledge_v2.db"
LIVE_TOKEN_DB = PROJECT_ROOT / "backend" / "data" / "documents" / "tokenrecord_v2.db"

# 預設備份目錄
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backend" / "data" / "backups"

# ========== 日誌設定 ==========

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("test_backup_recovery")


# ========== 輔助函式 ==========


def find_latest_backup(backup_dir: Path, prefix: str) -> Path:
    """找到最近的備份檔案"""
    backups = sorted(
        backup_dir.glob(f"{prefix}_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return backups[0] if backups else None


def integrity_check(db_path: Path) -> dict:
    """
    對資料庫執行完整性檢查

    Returns:
        dict: {ok: bool, wal_mode: bool, tables: {name: row_count}, errors: []}
    """
    result = {"ok": True, "wal_mode": False, "tables": {}, "errors": [], "size_mb": 0}

    if not db_path.exists():
        result["ok"] = False
        result["errors"].append(f"資料庫不存在: {db_path}")
        return result

    result["size_mb"] = round(db_path.stat().st_size / (1024 * 1024), 2)

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # PRAGMA integrity_check
        cursor.execute("PRAGMA integrity_check")
        check_result = cursor.fetchone()[0]
        if check_result != "ok":
            result["ok"] = False
            result["errors"].append(f"PRAGMA integrity_check 失敗: {check_result}")

        # 檢查 WAL 模式
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        result["wal_mode"] = journal_mode.lower() == "wal"

        # 列出所有表格與記錄數
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                result["tables"][table] = count
            except Exception as e:
                result["tables"][table] = f"ERROR: {e}"
                result["errors"].append(f"讀取 {table} 失敗: {e}")

        conn.close()

    except Exception as e:
        result["ok"] = False
        result["errors"].append(f"開啟資料庫失敗: {e}")

    return result


def compare_databases(live_result: dict, backup_result: dict, db_name: str) -> list:
    """比較正式 DB 與備份 DB 的差異"""
    diffs = []

    # 表格差異
    live_tables = set(live_result.get("tables", {}).keys())
    backup_tables = set(backup_result.get("tables", {}).keys())

    missing_in_backup = live_tables - backup_tables
    extra_in_backup = backup_tables - live_tables

    if missing_in_backup:
        diffs.append(f"備份中缺少表格: {missing_in_backup}")
    if extra_in_backup:
        diffs.append(f"備份中多出表格: {extra_in_backup}")

    # 記錄數差異
    for table in live_tables & backup_tables:
        live_count = live_result["tables"].get(table, 0)
        backup_count = backup_result["tables"].get(table, 0)

        if isinstance(live_count, int) and isinstance(backup_count, int):
            diff = live_count - backup_count
            if diff != 0:
                diffs.append(
                    f"{table}: 正式={live_count}, 備份={backup_count} (差異: {diff})"
                )

    return diffs


def test_single_backup(backup_path: Path, live_db_path: Path, db_name: str) -> bool:
    """測試單一備份檔案的恢復"""
    print(f"\n{'='*50}")
    print(f"  測試恢復: {db_name}")
    print(f"  備份來源: {backup_path}")
    print(f"{'='*50}")

    all_passed = True

    # Step 1: 複製到臨時目錄
    tmp_dir = Path(tempfile.mkdtemp(prefix="ai_expert_recovery_"))
    tmp_db = tmp_dir / backup_path.name

    try:
        shutil.copy2(str(backup_path), str(tmp_db))
        print(f"\n  1️⃣ 複製備份到臨時目錄: ✅")
        print(f"     路徑: {tmp_db}")

        # Step 2: 完整性檢查
        backup_check = integrity_check(tmp_db)
        if backup_check["ok"]:
            print(f"  2️⃣ 完整性檢查: ✅ (PRAGMA integrity_check = ok)")
        else:
            print(f"  2️⃣ 完整性檢查: ❌")
            for err in backup_check["errors"]:
                print(f"     - {err}")
            all_passed = False

        # Step 3: 顯示表格統計
        print(f"  3️⃣ 表格統計:")
        print(f"     大小: {backup_check['size_mb']} MB")
        print(f"     WAL 模式: {'✅' if backup_check['wal_mode'] else '❌ (非 WAL)'}")
        for table, count in backup_check["tables"].items():
            print(f"     - {table}: {count} 筆")

        # Step 4: 與正式 DB 比較
        if live_db_path.exists():
            live_check = integrity_check(live_db_path)
            diffs = compare_databases(live_check, backup_check, db_name)

            if diffs:
                print(f"  4️⃣ 與正式 DB 差異:")
                for d in diffs:
                    print(f"     ⚠️ {d}")
            else:
                print(f"  4️⃣ 與正式 DB 差異: ✅ 完全一致")
        else:
            print(f"  4️⃣ 正式 DB 不存在，跳過比較")

        # Step 5: 測試查詢
        try:
            conn = sqlite3.connect(str(tmp_db))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
            conn.close()
            print(f"  5️⃣ 查詢測試: ✅ (SELECT 1 成功)")
        except Exception as e:
            print(f"  5️⃣ 查詢測試: ❌ ({e})")
            all_passed = False

    finally:
        # 清理臨時目錄
        shutil.rmtree(str(tmp_dir), ignore_errors=True)
        print(f"  6️⃣ 清理臨時檔案: ✅")

    return all_passed


# ========== 主程式 ==========


def main():
    parser = argparse.ArgumentParser(
        description="AI Expert System 備份恢復測試工具"
    )
    parser.add_argument(
        "--backup-dir",
        type=str,
        default=str(DEFAULT_BACKUP_DIR),
        help=f"備份目錄 (預設: {DEFAULT_BACKUP_DIR})",
    )

    args = parser.parse_args()
    backup_dir = Path(args.backup_dir)

    print("=" * 60)
    print("  AI Expert System - 備份恢復驗證")
    print(f"  時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  備份目錄: {backup_dir}")
    print("=" * 60)

    if not backup_dir.exists():
        print(f"\n❌ 備份目錄不存在: {backup_dir}")
        print("   請先執行備份: scripts\\backup_db.bat")
        return

    # 找到最近的備份
    results = {}

    # 測試 Knowledge DB 備份
    kb_backup = find_latest_backup(backup_dir, "knowledge_v2")
    if kb_backup:
        results["knowledge"] = test_single_backup(
            kb_backup, LIVE_KNOWLEDGE_DB, "Knowledge DB"
        )
    else:
        print("\n⚠️ 找不到 knowledge_v2 備份檔案")
        results["knowledge"] = None

    # 測試 Token DB 備份
    tk_backup = find_latest_backup(backup_dir, "tokenrecord_v2")
    if tk_backup:
        results["token"] = test_single_backup(
            tk_backup, LIVE_TOKEN_DB, "Token DB"
        )
    else:
        print("\n⚠️ 找不到 tokenrecord_v2 備份檔案")
        results["token"] = None

    # 最終結果
    print("\n" + "=" * 60)
    print("  最終結果")
    print("=" * 60)

    all_ok = True
    for db_name, passed in results.items():
        if passed is True:
            print(f"  ✅ {db_name}: 恢復測試通過")
        elif passed is False:
            print(f"  ❌ {db_name}: 恢復測試失敗")
            all_ok = False
        else:
            print(f"  ⚠️ {db_name}: 無備份可測試")
            all_ok = False

    if all_ok:
        print("\n🎉 所有備份恢復測試通過！")
    else:
        print("\n⚠️ 部份測試未通過或缺少備份，請檢查。")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
