import logging

import cv2
import numpy as np

from app.database import SessionLocal
from app.db_models import Store, OcrTask, OcrFrontResult, OcrBackResult
from app.ocr_service import OCRService
from app.extractors.front import extract_front_fields
from app.extractors.back import extract_back_fields

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
_ocr_service = None


def _get_ocr_service() -> OCRService:
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


def recover_stale_tasks():
    """啟動時把卡在 processing 的 task 重設回 downloaded，避免 crash 後卡死"""
    db = SessionLocal()
    try:
        stale = db.query(OcrTask).filter_by(status="processing").all()
        if stale:
            for task in stale:
                task.status = "downloaded"
                task.error_message = None
            db.commit()
            logger.info(f"已重設 {len(stale)} 筆卡住的 processing task")
    finally:
        db.close()


def process_downloaded_images(side: str | None = None) -> int:
    """
    處理 status=downloaded 的 OCR 任務（逐張處理）：
    1. 查 DB 撈 status=downloaded（LIMIT BATCH_SIZE）
    2. 逐張：標記 processing → OCR → 存結果 → completed → 清除 image_data
    3. 失敗 → status=failed，記錄 error_message
    4. 每張處理完立刻 commit

    Args:
        side: "front" 或 "back"，None 表示全部處理

    回傳處理數量
    """
    db = SessionLocal()
    count = 0

    try:
        query = db.query(OcrTask).filter_by(status="downloaded")
        if side:
            query = query.filter_by(side=side)
        tasks = query.limit(BATCH_SIZE).all()

        if not tasks:
            logger.info("沒有待處理的圖片")
            return 0

        logger.info(f"找到 {len(tasks)} 張待處理圖片（批次上限: {BATCH_SIZE}）")
        ocr_service = _get_ocr_service()

        for task in tasks:
            try:
                # 標記 processing
                task.status = "processing"
                db.commit()

                if task.image_data is None:
                    task.status = "failed"
                    task.error_message = "圖片資料不存在 (image_data is None)"
                    db.commit()
                    logger.warning(f"圖片資料不存在，跳過: {task.file_name}")
                    continue

                # 將 bytes 轉為 numpy array
                nparr = np.frombuffer(task.image_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    task.status = "failed"
                    task.error_message = "無法解碼圖片 (cv2.imdecode returned None)"
                    db.commit()
                    logger.warning(f"圖片解碼失敗，跳過: {task.file_name}")
                    continue

                # OCR + 存結果
                _process_single(db, ocr_service, task, img)

                task.status = "completed"
                db.commit()
                count += 1
                logger.info(f"已處理 [{count}]: {task.file_name}")

            except Exception as e:
                db.rollback()
                task.status = "failed"
                task.error_message = str(e)
                db.commit()
                logger.error(f"OCR 處理失敗: {task.file_name} - {e}", exc_info=True)

        remaining = db.query(OcrTask).filter_by(status="downloaded").count()
        if remaining > 0:
            logger.info(f"剩餘 {remaining} 張將在下次排程處理")

    finally:
        db.close()

    return count


def _process_single(db, ocr_service: OCRService, task: OcrTask, img: np.ndarray):
    """處理單張圖片：OCR → 存 DB"""
    file_name = task.file_name
    store_name = task.store_name
    side = task.side
    modified_time = task.modified_time

    logger.info(f"OCR 處理: {file_name} ({side})")

    # 確保 stores 表有這家店
    store = db.query(Store).filter_by(store_name=store_name).first()
    if not store:
        store = Store(store_name=store_name, business_folder=task.business_folder)
        db.add(store)
        db.flush()

    # 檢查 DB 是否已有（避免重複）
    table = OcrFrontResult if side == "front" else OcrBackResult
    exists = db.query(table).filter_by(file_name=file_name, time=modified_time).first()
    if exists:
        logger.info(f"  DB 已存在，跳過: {file_name}")
        return

    # OCR
    ocr_result = ocr_service.recognize(img)

    if side == "front":
        fields = extract_front_fields(ocr_result["texts"], ocr_result["raw_text"])
        record = OcrFrontResult(
            file_name=file_name,
            time=modified_time,
            file_id=task.file_id,
            store_name=store_name,
            name=fields.get("name"),
            id_number=fields.get("id_number"),
            birthday=fields.get("birthday"),
            gender=fields.get("gender"),
            issue_date=fields.get("issue_date"),
            issue_type=fields.get("issue_type"),
            issue_location=fields.get("issue_location"),
            confidence=ocr_result["confidence"],
            raw_text=ocr_result["raw_text"],
        )
        logger.info(f"  正面: 姓名={fields.get('name')}, 證號={fields.get('id_number')}")
    else:
        fields = extract_back_fields(ocr_result["texts"])
        record = OcrBackResult(
            file_name=file_name,
            time=modified_time,
            file_id=task.file_id,
            store_name=store_name,
            father=fields.get("father"),
            mother=fields.get("mother"),
            spouse=fields.get("spouse"),
            military_service=fields.get("military_service"),
            birthplace=fields.get("birthplace"),
            address=fields.get("address"),
            confidence=ocr_result["confidence"],
            raw_text=ocr_result["raw_text"],
        )
        logger.info(f"  反面: 地址={fields.get('address')}")

    db.add(record)
    db.flush()
    logger.info(f"  已存入 DB: {file_name}")
