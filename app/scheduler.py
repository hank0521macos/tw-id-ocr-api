import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import SCAN_INTERVAL_MINUTES
from app.google_drive_service import GoogleDriveService

logger = logging.getLogger(__name__)

drive_service = GoogleDriveService()
scheduler = BackgroundScheduler()


def health_check_job():
    """每 10 秒的 health check log"""
    logger.info(f"[Health Check] 服務運作中 - {datetime.now().strftime('%H:%M:%S')}")


def download_job():
    """排程 1：從 Google Drive 下載最新的身分證圖片"""
    try:
        logger.info("=== 排程觸發：開始下載 Google Drive 圖片 ===")
        from app.drive_downloader import download_new_images
        count = download_new_images(drive_service)
        logger.info(f"=== 下載完成：{count} 張新圖片 ===")
    except Exception as e:
        logger.error(f"下載排程失敗: {e}", exc_info=True)


def ocr_job():
    """排程 2：處理已下載的圖片，OCR → 存 DB → 刪圖片"""
    try:
        logger.info("=== 排程觸發：開始 OCR 處理 ===")
        from app.ocr_processor import process_downloaded_images
        count = process_downloaded_images()
        logger.info(f"=== OCR 完成：{count} 張圖片已處理 ===")
    except Exception as e:
        logger.error(f"OCR 排程失敗: {e}", exc_info=True)


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

    # OCR 處理 - 暫時關閉排程，先手動觸發
    # scheduler.add_job(
    #     ocr_job,
    #     "interval",
    #     minutes=SCAN_INTERVAL_MINUTES,
    #     id="ocr_process",
    #     max_instances=1,
    #     replace_existing=True,
    #     next_run_time=datetime.now(),
    # )

    scheduler.start()
    logger.info(f"排程已啟動: health_check(10s), download(手動), ocr(手動)")


def stop_scheduler():
    """停止排程器"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("排程已停止")
