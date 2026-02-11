import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import inspect

from app.config import SCAN_INTERVAL_MINUTES
from app.database import engine
from app.google_drive_service import GoogleDriveService

logger = logging.getLogger(__name__)

drive_service = GoogleDriveService()
scheduler = BackgroundScheduler()


def _tables_ready() -> bool:
    """檢查必要的 table 是否已建立"""
    try:
        existing = inspect(engine).get_table_names()
        required = {"ocr_tasks", "ocr_front_results", "ocr_back_results", "stores"}
        if not required.issubset(existing):
            missing = required - set(existing)
            logger.warning(f"Table 尚未建立，跳過排程: {missing}")
            return False
        return True
    except Exception as e:
        logger.warning(f"檢查 table 失敗，跳過排程: {e}")
        return False


def health_check_job():
    """每 10 秒的 health check log"""
    logger.info(f"[Health Check] 服務運作中 - {datetime.now().strftime('%H:%M:%S')}")


def download_job():
    """排程 1：從 Google Drive 下載最新的身分證圖片"""
    if not _tables_ready():
        return
    try:
        logger.info("=== 排程觸發：開始下載 Google Drive 圖片 ===")
        from app.drive_downloader import download_new_images
        count = download_new_images(drive_service)
        logger.info(f"=== 下載完成：{count} 張新圖片 ===")
    except Exception as e:
        logger.error(f"下載排程失敗: {e}", exc_info=True)


def ocr_job():
    """排程 2：處理已下載的圖片，OCR → 存 DB"""
    if not _tables_ready():
        return
    try:
        logger.info("=== 排程觸發：開始 OCR 處理 ===")
        from app.ocr_processor import process_downloaded_images
        count = process_downloaded_images()
        logger.info(f"=== OCR 完成：{count} 張圖片已處理 ===")

        # 清除已完成 task 的 image_data 節省 DB 空間
        if count > 0:
            _cleanup_completed_image_data()
    except Exception as e:
        logger.error(f"OCR 排程失敗: {e}", exc_info=True)


def _cleanup_completed_image_data():
    """將 status=completed 且 image_data 不為 null 的 task 清除圖片"""
    try:
        from app.database import SessionLocal
        from app.db_models import OcrTask
        db = SessionLocal()
        try:
            tasks = (
                db.query(OcrTask)
                .filter_by(status="completed")
                .filter(OcrTask.image_data.isnot(None))
                .all()
            )
            if tasks:
                for task in tasks:
                    task.image_data = None
                db.commit()
                logger.info(f"已清除 {len(tasks)} 筆已完成 task 的 image_data")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"清除 image_data 失敗: {e}", exc_info=True)


def start_scheduler():
    """啟動所有排程"""
    drive_service.authenticate()

    # Health check - 每 10 秒
    scheduler.add_job(
        health_check_job,
        "interval",
        seconds=10,
        id="health_check",
        replace_existing=True,
    )

    # 下載圖片 - 暫時關閉排程，先手動觸發
    # scheduler.add_job(
    #     download_job,
    #     "interval",
    #     minutes=SCAN_INTERVAL_MINUTES,
    #     id="drive_download",
    #     max_instances=1,
    #     replace_existing=True,
    #     next_run_time=datetime.now(),
    # )

    # OCR 處理 - 每 5 分鐘處理 20 筆
    scheduler.add_job(
        ocr_job,
        "interval",
        minutes=5,
        id="ocr_process",
        max_instances=1,
        replace_existing=True,
        next_run_time=datetime.now(),
    )

    scheduler.start()
    logger.info("排程已啟動: health_check(10s), download(手動), ocr(5min)")


def stop_scheduler():
    """停止排程器"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("排程已停止")
