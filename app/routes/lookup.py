import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
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

    接受多個門店名稱，以模糊比對搜尋正反面 OCR 結果。
    比對時會忽略空格、半形/全形空白，用 LIKE 模糊搜尋。

    設計給 Google Sheets Apps Script 批次呼叫使用。
    """
    results = []

    for raw_name in req.store_names:
        name = raw_name.strip()
        if not name:
            results.append({"query": raw_name, "matched_store": None, "front": None, "back": None})
            continue

        # 移除所有空白字元後做 LIKE 比對
        stripped = name.replace(" ", "").replace("\u3000", "").replace("\t", "")

        # 用 DB 端 REPLACE 移除空格後比對，避免空格差異導致找不到
        front = (
            db.query(OcrFrontResult)
            .filter(
                func.replace(func.replace(OcrFrontResult.store_name, " ", ""), "\u3000", "")
                .ilike(f"%{stripped}%")
            )
            .order_by(OcrFrontResult.time.desc())
            .first()
        )

        back = (
            db.query(OcrBackResult)
            .filter(
                func.replace(func.replace(OcrBackResult.store_name, " ", ""), "\u3000", "")
                .ilike(f"%{stripped}%")
            )
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

    用 ILIKE 模糊比對 file_name，忽略空格差異。
    同一檔名有多筆時取最新一筆。
    """
    results = []

    for raw_name in req.file_names:
        name = raw_name.strip()
        if not name:
            results.append({"query": raw_name, "matched_file": None})
            continue

        stripped = name.replace(" ", "").replace("\u3000", "").replace("\t", "")

        front = (
            db.query(OcrFrontResult)
            .filter(
                func.replace(func.replace(OcrFrontResult.file_name, " ", ""), "\u3000", "")
                .ilike(f"%{stripped}%")
            )
            .order_by(OcrFrontResult.time.desc())
            .first()
        )

        back = (
            db.query(OcrBackResult)
            .filter(
                func.replace(func.replace(OcrBackResult.file_name, " ", ""), "\u3000", "")
                .ilike(f"%{stripped}%")
            )
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


