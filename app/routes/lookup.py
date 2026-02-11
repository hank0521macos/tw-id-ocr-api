import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import OcrFrontResult, OcrBackResult
from app.models import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lookup", tags=["Lookup"])


class LookupRequest(BaseModel):
    """批次查詢請求：傳入多個門店名稱"""
    store_names: list[str]


@router.post("/batch", response_model=StandardResponse)
def batch_lookup(req: LookupRequest, db: Session = Depends(get_db)):
    """
    批次查詢門店身分證 OCR 結果。

    以門店名稱精準比對搜尋正反面 OCR 結果。
    設計給 Google Sheets Apps Script 批次呼叫使用。
    """
    results = []

    for raw_name in req.store_names:
        name = raw_name.strip()
        if not name:
            results.append({"query": raw_name, "matched_store": None})
            continue

        front = (
            db.query(OcrFrontResult)
            .filter_by(store_name=name)
            .order_by(OcrFrontResult.time.desc())
            .first()
        )

        back = (
            db.query(OcrBackResult)
            .filter_by(store_name=name)
            .order_by(OcrBackResult.time.desc())
            .first()
        )

        matched = (front.store_name if front else back.store_name) if (front or back) else None

        record = {
            "query": raw_name,
            "matched_store": matched,
            # 正面
            "name": front.name if front else None,
            "id_number": front.id_number if front else None,
            "birthday": front.birthday if front else None,
            "gender": front.gender if front else None,
            "issue_date": front.issue_date if front else None,
            "issue_type": front.issue_type if front else None,
            "issue_location": front.issue_location if front else None,
            "front_confidence": front.confidence if front else None,
            # 反面
            "father": back.father if back else None,
            "mother": back.mother if back else None,
            "spouse": back.spouse if back else None,
            "military_service": back.military_service if back else None,
            "birthplace": back.birthplace if back else None,
            "address": back.address if back else None,
            "back_confidence": back.confidence if back else None,
        }
        results.append(record)

    found = sum(1 for r in results if r["matched_store"])
    return StandardResponse(
        data=results,
        success=True,
        message=f"查詢 {len(req.store_names)} 筆，匹配 {found} 筆。",
    )


class FilenameLookupRequest(BaseModel):
    """批次查詢請求：傳入多個檔名"""
    file_names: list[str]


@router.post("/batch-by-file", response_model=StandardResponse)
def batch_lookup_by_file(req: FilenameLookupRequest, db: Session = Depends(get_db)):
    """
    以檔名批次查詢身分證 OCR 結果。

    以檔名精準比對，同一檔名有多筆時取最新一筆。
    """
    results = []

    for raw_name in req.file_names:
        name = raw_name.strip()
        if not name:
            results.append({"query": raw_name, "matched_file": None})
            continue

        front = (
            db.query(OcrFrontResult)
            .filter_by(file_name=name)
            .order_by(OcrFrontResult.time.desc())
            .first()
        )

        back = (
            db.query(OcrBackResult)
            .filter_by(file_name=name)
            .order_by(OcrBackResult.time.desc())
            .first()
        )

        matched = (front.file_name if front else back.file_name) if (front or back) else None

        record = {
            "query": raw_name,
            "matched_file": matched,
            "store_name": (front.store_name if front else back.store_name) if (front or back) else None,
            # 正面
            "name": front.name if front else None,
            "id_number": front.id_number if front else None,
            "birthday": front.birthday if front else None,
            "gender": front.gender if front else None,
            "issue_date": front.issue_date if front else None,
            "issue_type": front.issue_type if front else None,
            "issue_location": front.issue_location if front else None,
            "front_confidence": front.confidence if front else None,
            # 反面
            "father": back.father if back else None,
            "mother": back.mother if back else None,
            "spouse": back.spouse if back else None,
            "military_service": back.military_service if back else None,
            "birthplace": back.birthplace if back else None,
            "address": back.address if back else None,
            "back_confidence": back.confidence if back else None,
        }
        results.append(record)

    found = sum(1 for r in results if r["matched_file"])
    return StandardResponse(
        data=results,
        success=True,
        message=f"查詢 {len(req.file_names)} 筆，匹配 {found} 筆。",
    )
