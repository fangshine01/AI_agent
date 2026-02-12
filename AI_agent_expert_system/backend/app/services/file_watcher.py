"""
檔案監控服務 - 使用 Watchdog 監聽 raw_files 目錄
自動偵測新檔案並觸發處理流程
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class DocumentFileHandler(FileSystemEventHandler):
    """檔案事件處理器"""

    SUPPORTED_EXTENSIONS = {".pptx", ".md", ".txt", ".pdf", ".png", ".jpg", ".jpeg"}
    TEMP_EXTENSIONS = {".tmp", ".crdownload", ".part", ".swp"}

    def __init__(
        self,
        raw_dir: str,
        archive_dir: str,
        failed_dir: str,
        generated_md_dir: str,
        debounce: int = 2,
    ):
        self.raw_dir = Path(raw_dir)
        self.archive_dir = Path(archive_dir)
        self.failed_dir = Path(failed_dir)
        self.generated_md_dir = Path(generated_md_dir)
        self.debounce = debounce
        self.processing_files: Set[str] = set()
        self._lock = threading.Lock()

    def on_created(self, event):
        """檔案建立事件"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # 過濾臨時檔案
        if file_path.name.startswith(".") or file_path.suffix.lower() in self.TEMP_EXTENSIONS:
            return

        # 過濾不支援的檔案類型
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"略過不支援的檔案類型: {file_path.name}")
            return

        # 避免重複觸發
        with self._lock:
            if str(file_path) in self.processing_files:
                return
            self.processing_files.add(str(file_path))

        # 使用背景執行緒處理
        thread = threading.Thread(
            target=self._debounce_and_process,
            args=(file_path,),
            daemon=True,
        )
        thread.start()

    def _debounce_and_process(self, file_path: Path):
        """Debounce 等待後處理檔案"""
        try:
            logger.info(f"🔍 偵測到新檔案: {file_path.name}")

            # Debounce: 等待檔案寫入完成
            time.sleep(self.debounce)

            # 確認檔案仍存在
            if not file_path.exists():
                logger.warning(f"檔案已消失: {file_path.name}")
                return

            self._process_file(file_path)
        finally:
            with self._lock:
                self.processing_files.discard(str(file_path))

    def _process_file(self, file_path: Path):
        """處理單一檔案"""
        try:
            # 判斷是否為圖片
            is_image = file_path.suffix.lower() in {".png", ".jpg", ".jpeg"}

            if is_image:
                self._process_image(file_path)
            else:
                self._process_document(file_path)

        except Exception as e:
            logger.error(f"❌ 處理失敗: {file_path.name} - {e}")
            self._move_to_failed(file_path, str(e))

    def _process_document(self, file_path: Path):
        """處理文件檔案"""
        try:
            # 推測文件類型
            doc_type = self._infer_doc_type(file_path)

            logger.info(f"⚙️ 開始處理文件: {file_path.name} (類型: {doc_type})")

            # 匯入 ingestion 模組 (延遲匯入避免循環引用)
            from core.ingestion_v3 import process_document_v3

            result = process_document_v3(
                file_path=str(file_path),
                doc_type=doc_type,
                analysis_mode="auto",
            )

            if result.get("success"):
                # 成功: 移動到 archived
                self._move_to_archived(file_path)
                logger.info(f"✅ 處理成功 (doc_id={result.get('doc_id')}): {file_path.name}")
            else:
                raise Exception(result.get("message", "Unknown error"))

        except Exception as e:
            logger.error(f"❌ 文件處理失敗: {file_path.name} - {e}")
            self._move_to_failed(file_path, str(e))

    def _process_image(self, file_path: Path):
        """處理圖片檔案 (Gemini 辨識 + 自動入庫)"""
        try:
            logger.info(f"🖼️ 開始處理圖片: {file_path.name}")

            from backend.app.core.image_processor import get_image_processor

            processor = get_image_processor()
            markdown_content = processor.process_image(str(file_path), prompt_type="auto")

            if markdown_content:
                # 儲存生成的 Markdown
                md_filename = file_path.stem + "_generated.md"
                md_path = self.generated_md_dir / md_filename
                md_path.write_text(markdown_content, encoding="utf-8")

                logger.info(f"✅ 圖片轉 Markdown 成功: {md_filename}")

                # 將生成的 Markdown 入庫（整合 Ingestion）
                try:
                    from core.ingestion_v3 import process_document_v3

                    doc_type = self._infer_doc_type(file_path)
                    result = process_document_v3(
                        file_path=str(md_path),
                        doc_type=doc_type,
                        analysis_mode="auto",
                        enable_gemini_vision=False,  # MD 不需要再用 Gemini
                    )

                    if result.get("success"):
                        logger.info(
                            f"✅ Gemini 生成文件已入庫 "
                            f"(doc_id={result.get('doc_id')}, chunks={result.get('chunks')})"
                        )
                    else:
                        logger.warning(f"⚠️ Gemini 生成文件入庫失敗: {result.get('message')}")
                except Exception as e:
                    logger.warning(f"⚠️ Gemini 生成文件入庫失敗: {e}")

                # 追蹤 Gemini Token 用量（估算）
                try:
                    from backend.app.dependencies import get_database
                    db = get_database()
                    estimated_tokens = len(markdown_content) // 4
                    db.log_token_usage(
                        file_name=file_path.name,
                        operation='gemini_vision',
                        usage={
                            'prompt_tokens': estimated_tokens,
                            'completion_tokens': estimated_tokens,
                            'total_tokens': estimated_tokens * 2,
                        }
                    )
                except Exception:
                    pass  # Token 追蹤失敗不影響主流程

                # 移動原圖到 archived
                self._move_to_archived(file_path)
            else:
                raise Exception("Gemini 回傳空內容")

        except ImportError:
            logger.warning(f"⚠️ Gemini 模組未安裝，跳過圖片處理: {file_path.name}")
            self._move_to_failed(file_path, "Gemini module not available")
        except Exception as e:
            logger.error(f"❌ 圖片處理失敗: {file_path.name} - {e}")
            self._move_to_failed(file_path, str(e))

    def _move_to_archived(self, file_path: Path):
        """移動到已處理目錄"""
        try:
            dest = self.archive_dir / file_path.name
            # 處理同名檔案
            if dest.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                counter = 1
                while dest.exists():
                    dest = self.archive_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            file_path.rename(dest)
        except Exception as e:
            logger.error(f"移動到 archived 失敗: {e}")

    def _move_to_failed(self, file_path: Path, error: str):
        """移動到失敗目錄並記錄錯誤"""
        try:
            if file_path.exists():
                dest = self.failed_dir / file_path.name
                file_path.rename(dest)

            # 記錄錯誤
            error_log_path = self.failed_dir / f"{file_path.name}.error.txt"
            with open(error_log_path, "w", encoding="utf-8") as f:
                f.write(f"Filename: {file_path.name}\n")
                f.write(f"Error: {error}\n")
                f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception as e:
            logger.error(f"移動到 failed 失敗: {e}")

    def _infer_doc_type(self, file_path: Path) -> str:
        """推測文件類型"""
        name_lower = file_path.name.lower()

        if any(kw in name_lower for kw in ["troubleshoot", "qa", "8d", "defect", "異常"]):
            return "Troubleshooting"
        elif any(kw in name_lower for kw in ["training", "訓練", "教材", "原理"]):
            return "Training"
        elif any(kw in name_lower for kw in ["procedure", "sop", "手順", "流程"]):
            return "Procedure"
        else:
            return "Knowledge"


def start_file_watcher(watcher_config: dict) -> Optional[Observer]:
    """
    啟動檔案監控服務

    Args:
        watcher_config: {
            'raw_dir': str,
            'archive_dir': str,
            'failed_dir': str,
            'generated_md_dir': str,
            'debounce': int
        }

    Returns:
        Observer instance (可用於停止監控)
    """
    raw_dir = watcher_config["raw_dir"]

    # 確保所有目錄存在
    for key in ["raw_dir", "archive_dir", "failed_dir", "generated_md_dir"]:
        dir_path = watcher_config.get(key)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

    # 建立事件處理器和觀察者
    event_handler = DocumentFileHandler(
        raw_dir=raw_dir,
        archive_dir=watcher_config["archive_dir"],
        failed_dir=watcher_config["failed_dir"],
        generated_md_dir=watcher_config.get("generated_md_dir", ""),
        debounce=watcher_config.get("debounce", 2),
    )

    observer = Observer()
    observer.schedule(event_handler, raw_dir, recursive=False)
    observer.start()

    logger.info(f"👁️ 檔案監控服務已啟動: {raw_dir}")
    return observer
