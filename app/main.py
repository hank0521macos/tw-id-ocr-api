import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import StandardResponse
from app.database import init_db
from app.routes.ocr import router as ocr_router
from app.routes.stores import router as stores_router
from app.google_drive_service import GoogleDriveService

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


drive_service = GoogleDriveService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("初始化資料庫...")
    init_db()
    logger.info("恢復卡住的 task...")
    from app.ocr_processor import recover_stale_tasks
    recover_stale_tasks()
    yield


app = FastAPI(
    title="Taiwan ID Card OCR API",
    description="Upload Taiwan ID card image to extract ID number and name",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr_router)
app.include_router(stores_router)


@app.get("/health", response_model=StandardResponse, tags=["Health"])
async def health_check():
    return StandardResponse(
        data={"status": "ok", "service": "tw-id-ocr", "version": "1.0.0"},
        success=True,
        message="Service is running.",
    )


@app.get("/api/drive/list", response_model=StandardResponse, tags=["Google Drive"])
async def list_drive_folders():
    """列出 Google Drive 資料夾結構（測試連線用）"""
    try:
        if not drive_service.service:
            drive_service.authenticate()

        from app.config import GOOGLE_DRIVE_FOLDER_ID
        tree = []
        biz_folders = drive_service.list_folders(GOOGLE_DRIVE_FOLDER_ID)
        for biz in biz_folders:
            sub_folders = drive_service.list_folders(biz["id"])
            tree.append({
                "name": biz["name"],
                "id": biz["id"],
                "sub_folders": [{"name": s["name"], "id": s["id"]} for s in sub_folders],
            })

        return StandardResponse(
            data=tree,
            success=True,
            message=f"Found {len(biz_folders)} business folders.",
        )
    except Exception as e:
        logger.error(f"列出目錄失敗: {e}", exc_info=True)
        return StandardResponse(data=None, success=False, message=f"List failed: {str(e)}")


@app.post("/api/drive/download", response_model=StandardResponse, tags=["Google Drive"])
async def manual_download():
    """手動觸發下載 Google Drive 圖片（掃描 → 寫入 ocr_tasks → 下載）"""
    try:
        from app.drive_downloader import download_new_images
        count = download_new_images(drive_service)
        return StandardResponse(
            data={"downloaded": count},
            success=True,
            message=f"Downloaded {count} new images.",
        )
    except Exception as e:
        logger.error(f"手動下載失敗: {e}", exc_info=True)
        return StandardResponse(data=None, success=False, message=f"Download failed: {str(e)}")


@app.post("/api/ocr/process/front", response_model=StandardResponse, tags=["OCR"])
async def manual_ocr_front():
    """手動觸發正面 OCR 處理（撈 status=downloaded, side=front → OCR → 存 DB）"""
    try:
        from app.ocr_processor import process_downloaded_images
        count = process_downloaded_images(side="front")
        return StandardResponse(
            data={"processed": count},
            success=True,
            message=f"Processed {count} front images.",
        )
    except Exception as e:
        logger.error(f"手動正面 OCR 失敗: {e}", exc_info=True)
        return StandardResponse(data=None, success=False, message=f"OCR front failed: {str(e)}")


@app.post("/api/ocr/process/back", response_model=StandardResponse, tags=["OCR"])
async def manual_ocr_back():
    """手動觸發反面 OCR 處理（撈 status=downloaded, side=back → OCR → 存 DB）"""
    try:
        from app.ocr_processor import process_downloaded_images
        count = process_downloaded_images(side="back")
        return StandardResponse(
            data={"processed": count},
            success=True,
            message=f"Processed {count} back images.",
        )
    except Exception as e:
        logger.error(f"手動反面 OCR 失敗: {e}", exc_info=True)
        return StandardResponse(data=None, success=False, message=f"OCR back failed: {str(e)}")
