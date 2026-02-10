import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import Store, OcrFrontResult, OcrBackResult
from app.models import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stores", tags=["Stores"])


@router.get("", response_model=StandardResponse)
def list_stores(db: Session = Depends(get_db)):
    """列出所有店家及其最新的正反面 OCR 結果"""
    stores = db.query(Store).order_by(Store.store_name).all()

    data = []
    for store in stores:
        front = (
            db.query(OcrFrontResult)
            .filter_by(store_name=store.store_name)
            .order_by(OcrFrontResult.time.desc())
            .first()
        )
        back = (
            db.query(OcrBackResult)
            .filter_by(store_name=store.store_name)
            .order_by(OcrBackResult.time.desc())
            .first()
        )

        data.append({
            "store_name": store.store_name,
            "business_folder": store.business_folder,
            "front": _front_to_dict(front) if front else None,
            "back": _back_to_dict(back) if back else None,
        })

    return StandardResponse(
        data=data,
        success=True,
        message=f"Found {len(data)} stores.",
    )


@router.get("/{store_name}", response_model=StandardResponse)
def get_store(store_name: str, db: Session = Depends(get_db)):
    """查詢特定店家的最新 OCR 結果"""
    store = db.query(Store).filter_by(store_name=store_name).first()
    if not store:
        return StandardResponse(data=None, success=False, message=f"Store '{store_name}' not found.")

    front = (
        db.query(OcrFrontResult)
        .filter_by(store_name=store_name)
        .order_by(OcrFrontResult.time.desc())
        .first()
    )
    back = (
        db.query(OcrBackResult)
        .filter_by(store_name=store_name)
        .order_by(OcrBackResult.time.desc())
        .first()
    )

    return StandardResponse(
        data={
            "store_name": store.store_name,
            "business_folder": store.business_folder,
            "front": _front_to_dict(front) if front else None,
            "back": _back_to_dict(back) if back else None,
        },
        success=True,
        message="Store found.",
    )


@router.get("/{store_name}/history", response_model=StandardResponse)
def get_store_history(store_name: str, db: Session = Depends(get_db)):
    """查詢特定店家的所有歷史 OCR 紀錄"""
    fronts = (
        db.query(OcrFrontResult)
        .filter_by(store_name=store_name)
        .order_by(OcrFrontResult.time.desc())
        .all()
    )
    backs = (
        db.query(OcrBackResult)
        .filter_by(store_name=store_name)
        .order_by(OcrBackResult.time.desc())
        .all()
    )

    return StandardResponse(
        data={
            "front": [_front_to_dict(r) for r in fronts],
            "back": [_back_to_dict(r) for r in backs],
        },
        success=True,
        message=f"Found {len(fronts)} front, {len(backs)} back records.",
    )


def _front_to_dict(r: OcrFrontResult) -> dict:
    return {
        "file_name": r.file_name,
        "time": r.time.isoformat() if r.time else None,
        "name": r.name,
        "id_number": r.id_number,
        "birthday": r.birthday,
        "gender": r.gender,
        "issue_date": r.issue_date,
        "issue_type": r.issue_type,
        "issue_location": r.issue_location,
        "confidence": r.confidence,
    }


def _back_to_dict(r: OcrBackResult) -> dict:
    return {
        "file_name": r.file_name,
        "time": r.time.isoformat() if r.time else None,
        "father": r.father,
        "mother": r.mother,
        "spouse": r.spouse,
        "military_service": r.military_service,
        "birthplace": r.birthplace,
        "address": r.address,
        "confidence": r.confidence,
    }
