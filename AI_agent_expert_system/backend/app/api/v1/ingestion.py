"""
Ingestion API - 檔案上傳與入庫路由
"""

import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from backend.app.schemas.common import ResponseBase
from backend.app.schemas.document import ProcessingStatus
from backend.app.utils.file_handler import save_uploaded_file, get_file_status

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_dirs():
    """取得檔案目錄配置"""
    import backend.config as cfg
    return cfg.RAW_FILES_DIR, cfg.ARCHIVED_FILES_DIR, cfg.FAILED_FILES_DIR


@router.post("/upload", response_model=ResponseBase)
async def upload_file(
    file: UploadFile = File(...),
    doc_type: str = Form(default="Knowledge"),
    analysis_mode: str = Form(default="auto"),
):
    """
    上傳檔案到 raw_files 目錄
    檔案將由 File Watcher 自動處理
    """
    try:
        raw_dir, _, _ = _get_dirs()

        # 驗證檔案類型
        allowed_extensions = {".pptx", ".md", ".txt", ".pdf", ".png", ".jpg", ".jpeg"}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的檔案類型: {ext}。支援: {', '.join(allowed_extensions)}",
            )

        # 讀取檔案內容
        content = await file.read()

        # 儲存到 raw_files
        saved_path = save_uploaded_file(content, file.filename, raw_dir)

        logger.info(f"✅ 檔案已上傳: {file.filename} -> {saved_path}")

        return ResponseBase(
            success=True,
            message=f"檔案 {file.filename} 已上傳到監控目錄，將自動處理",
            data={"filename": file.filename, "path": saved_path, "size": len(content)},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 上傳失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_multiple", response_model=ResponseBase)
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    doc_type: str = Form(default="Knowledge"),
):
    """批次上傳多個檔案"""
    try:
        raw_dir, _, _ = _get_dirs()
        results = []

        for file in files:
            content = await file.read()
            saved_path = save_uploaded_file(content, file.filename, raw_dir)
            results.append({"filename": file.filename, "size": len(content)})

        return ResponseBase(
            success=True,
            message=f"已上傳 {len(results)} 個檔案到監控目錄",
            data={"files": results},
        )

    except Exception as e:
        logger.error(f"❌ 批次上傳失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_and_process", response_model=ResponseBase)
async def upload_and_process(
    file: UploadFile = File(...),
    doc_type: str = Form(default="Knowledge"),
    analysis_mode: str = Form(default="auto"),
    api_key: str = Form(default=None),
    base_url: str = Form(default=None),
):
    """
    上傳檔案並立即處理（使用使用者的 API Key）
    不經過 File Watcher，直接執行入庫

    流程:
    1. 儲存檔案到 raw_files
    2. 直接呼叫 ingestion_v3 處理
    3. 成功後移動到 archived_files
    """
    try:
        raw_dir, archive_dir, _ = _get_dirs()

        # 驗證檔案類型
        allowed_extensions = {".pptx", ".md", ".txt", ".pdf", ".png", ".jpg", ".jpeg"}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的檔案類型: {ext}。支援: {', '.join(allowed_extensions)}",
            )

        # 讀取並儲存檔案
        content = await file.read()
        saved_path = save_uploaded_file(content, file.filename, raw_dir)
        logger.info(f"📤 檔案已上傳: {file.filename}，開始直接處理...")

        # 直接處理（不經 Watcher，使用使用者的 API Key）
        from core.ingestion_v3 import process_document_v3

        is_image = ext in {".png", ".jpg", ".jpeg"}
        result = process_document_v3(
            file_path=saved_path,
            doc_type=doc_type,
            analysis_mode=analysis_mode,
            api_key=api_key,
            base_url=base_url,
            enable_gemini_vision=is_image,
        )

        # 處理成功則移動到 archived
        if result.get("success"):
            try:
                archived_path = os.path.join(archive_dir, file.filename)
                if os.path.exists(saved_path):
                    os.makedirs(archive_dir, exist_ok=True)
                    shutil.move(saved_path, archived_path)
            except Exception as move_err:
                logger.warning(f"⚠️ 移動到 archived 失敗: {move_err}")

        return ResponseBase(
            success=result.get("success", False),
            message=result.get("message", ""),
            data={
                "filename": file.filename,
                "doc_id": result.get("doc_id"),
                "chunks": result.get("chunks", 0),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 上傳處理失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{filename}", response_model=ProcessingStatus)
async def get_processing_status(filename: str):
    """查詢檔案處理狀態"""
    try:
        raw_dir, archive_dir, failed_dir = _get_dirs()
        status = get_file_status(filename, raw_dir, archive_dir, failed_dir)

        return ProcessingStatus(
            filename=filename,
            status=status["status"],
            message=status.get("error", ""),
        )

    except Exception as e:
        logger.error(f"❌ 查詢狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
