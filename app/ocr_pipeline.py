import logging

from app.google_drive_service import GoogleDriveService
from app.drive_downloader import download_new_images
from app.ocr_processor import process_downloaded_images

logger = logging.getLogger(__name__)


def run_ocr_pipeline(drive_service: GoogleDriveService) -> dict:
    """
    一條龍流程：掃描 Drive → 下載 → OCR → 存 DB

    全部透過 DB 狀態機驅動：
    1. download_new_images: 掃描 → pending → downloaded
    2. process_downloaded_images: downloaded → processing → completed
    """
    logger.info("=== OCR Pipeline 開始 ===")

    downloaded = download_new_images(drive_service)
    logger.info(f"下載階段完成: {downloaded} 張")

    processed = process_downloaded_images()
    logger.info(f"OCR 階段完成: {processed} 張")

    logger.info(f"=== OCR Pipeline 結束: 下載 {downloaded}, 處理 {processed} ===")
    return {"downloaded": downloaded, "processed": processed}
