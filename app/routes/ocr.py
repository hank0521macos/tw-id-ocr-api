import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.models import StandardResponse, FrontOCRResult, BackOCRResult
from app.ocr_service import OCRService
from app.extractors.front import extract_front_fields
from app.extractors.back import extract_back_fields

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/api/ocr", tags=["OCR"])
ocr_service = OCRService()


def _validate_and_save_file(file: UploadFile, content: bytes) -> tuple[Path, str]:
    """
    驗證檔案格式與大小，儲存至暫存目錄

    Returns:
        (filepath, ext)

    Raises:
        ValueError: 檔案格式或大小不合法
    """
    if not file.filename:
        raise ValueError("Invalid file format. Only jpg/png allowed.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Invalid file format. Only jpg/png allowed.")

    if len(content) > MAX_FILE_SIZE:
        raise ValueError("File size exceeds 10MB limit.")

    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(content)
    logger.info(f"檔案已儲存至: {filepath}")

    return filepath, ext


@router.post("/front", response_model=StandardResponse)
async def ocr_front(
    file: UploadFile = File(..., description="身分證正面圖片檔案（jpg/png，最大10MB）"),
):
    """
    上傳身分證正面圖片進行 OCR 識別

    回傳欄位：name, birthday, issue_date, issue_type, id_number, gender, issue_location
    """
    logger.info(f"收到正面 OCR 請求 - 檔案名稱: {file.filename}")
    content = await file.read()

    try:
        filepath, _ = _validate_and_save_file(file, content)
    except ValueError as e:
        return StandardResponse(data=None, success=False, message=str(e))

    try:
        ocr_result = ocr_service.recognize(str(filepath))
        fields = extract_front_fields(ocr_result["texts"], ocr_result["raw_text"])

        result = FrontOCRResult(
            **fields,
            confidence=ocr_result["confidence"],
            raw_text=ocr_result["raw_text"],
        )

        logger.info(f"正面 OCR 完成 - 身分證字號: {fields.get('id_number')}, 姓名: {fields.get('name')}")
        return StandardResponse(
            data=result.model_dump(exclude_none=True),
            success=True,
            message="OCR recognition completed successfully.",
        )
    except Exception as e:
        logger.error(f"OCR 處理異常: {str(e)}", exc_info=True)
        return StandardResponse(
            data=None,
            success=False,
            message="Unable to extract data from image.",
        )
    finally:
        if filepath.exists():
            filepath.unlink()


@router.post("/back", response_model=StandardResponse)
async def ocr_back(
    file: UploadFile = File(..., description="身分證反面圖片檔案（jpg/png，最大10MB）"),
):
    """
    上傳身分證反面圖片進行 OCR 識別

    回傳欄位：father, mother, spouse, military_service, birthplace, address
    """
    logger.info(f"收到反面 OCR 請求 - 檔案名稱: {file.filename}")
    content = await file.read()

    try:
        filepath, _ = _validate_and_save_file(file, content)
    except ValueError as e:
        return StandardResponse(data=None, success=False, message=str(e))

    try:
        ocr_result = ocr_service.recognize(str(filepath))
        fields = extract_back_fields(ocr_result["texts"])

        result = BackOCRResult(
            **fields,
            confidence=ocr_result["confidence"],
            raw_text=ocr_result["raw_text"],
        )

        logger.info(f"反面 OCR 完成 - 父: {fields.get('father')}, 母: {fields.get('mother')}")
        return StandardResponse(
            data=result.model_dump(exclude_none=True),
            success=True,
            message="OCR recognition completed successfully.",
        )
    except Exception as e:
        logger.error(f"OCR 處理異常: {str(e)}", exc_info=True)
        return StandardResponse(
            data=None,
            success=False,
            message="Unable to extract data from image.",
        )
    finally:
        if filepath.exists():
            filepath.unlink()
