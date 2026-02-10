import logging
import time
from datetime import datetime

from app.config import TEMP_DIR
from app.database import SessionLocal
from app.db_models import OcrTask
from app.google_drive_service import GoogleDriveService

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def download_new_images(drive_service: GoogleDriveService) -> int:
    """
    從 Google Drive 下載新的/更新過的身分證圖片。

    流程：
    1. scan_all_id_cards() 取得所有圖片 metadata
    2. 查 DB ocr_tasks 是否已有 (file_id, modified_time) → 跳過
    3. 新檔案：insert ocr_tasks status=pending
    4. 下載圖片到 TEMP_DIR
    5. 成功 → status=downloaded，記錄 image_path
    6. 失敗 → status=failed，記錄 error_message

    回傳下載數量
    """
    all_cards = drive_service.scan_all_id_cards()
    if not all_cards:
        logger.info("沒有找到任何身分證圖片")
        return 0

    db = SessionLocal()
    count = 0

    try:
        for card in all_cards:
            file_id = card["file_id"]
            file_name = card["file_name"]
            modified_time = datetime.fromisoformat(
                card["modified_time"].replace("Z", "+00:00")
            )

            # 檢查是否已有記錄（同 file_id + modified_time）
            existing = (
                db.query(OcrTask)
                .filter_by(file_id=file_id, modified_time=modified_time)
                .first()
            )
            if existing:
                continue

            # 建立 pending task
            task = OcrTask(
                file_id=file_id,
                file_name=file_name,
                store_name=card.get("store_name"),
                side=card.get("side"),
                business_folder=card.get("business_folder"),
                status="pending",
                modified_time=modified_time,
            )
            db.add(task)
            db.flush()

            # 下載（含重試）
            dest_path = TEMP_DIR / file_name
            success = False
            error_msg = ""
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    drive_service.download_file(file_id, dest_path)
                    success = True
                    break
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"下載失敗 (第{attempt}次): {file_name} - {e}")
                    if attempt < MAX_RETRIES:
                        time.sleep(2 * attempt)

            if success:
                task.status = "downloaded"
                task.image_path = str(dest_path)
                count += 1
                logger.info(f"已下載 [{count}]: {file_name}")
            else:
                task.status = "failed"
                task.error_message = f"下載失敗: {error_msg}"
                logger.error(f"下載最終失敗: {file_name}")

            db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"下載流程異常: {e}", exc_info=True)
        raise
    finally:
        db.close()

    logger.info(f"下載階段完成，共 {count} 張新圖片")
    return count
