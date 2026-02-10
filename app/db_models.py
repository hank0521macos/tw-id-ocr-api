from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, PrimaryKeyConstraint, UniqueConstraint
from app.database import Base


class OcrTask(Base):
    """OCR 任務狀態機"""
    __tablename__ = "ocr_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(255), nullable=False)
    file_name = Column(String(500), nullable=False)
    store_name = Column(String(255))
    side = Column(String(10))
    business_folder = Column(String(255))
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text)
    image_path = Column(String(500))
    modified_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("file_id", "modified_time", name="uq_ocr_tasks_file_modified"),
    )


class Store(Base):
    """店家主檔"""
    __tablename__ = "stores"

    store_name = Column(String(255), primary_key=True)
    business_folder = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OcrFrontResult(Base):
    """身分證正面 OCR 結果（hypertable）"""
    __tablename__ = "ocr_front_results"

    file_name = Column(String(500), nullable=False)
    time = Column(DateTime(timezone=True), nullable=False)
    file_id = Column(String(255))
    store_name = Column(String(255), nullable=False)

    name = Column(String(100))
    id_number = Column(String(20))
    birthday = Column(String(20))
    gender = Column(String(10))
    issue_date = Column(String(20))
    issue_type = Column(String(20))
    issue_location = Column(String(50))

    confidence = Column(Float)
    raw_text = Column(Text)
    update_ts = Column(DateTime, nullable=False, default=datetime.utcnow)
    create_ts = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        PrimaryKeyConstraint("file_name", "time", name="ocr_front_results_pk"),
    )


class OcrBackResult(Base):
    """身分證反面 OCR 結果（hypertable）"""
    __tablename__ = "ocr_back_results"

    file_name = Column(String(500), nullable=False)
    time = Column(DateTime(timezone=True), nullable=False)
    file_id = Column(String(255))
    store_name = Column(String(255), nullable=False)

    father = Column(String(100))
    mother = Column(String(100))
    spouse = Column(String(100))
    military_service = Column(String(100))
    birthplace = Column(String(100))
    address = Column(Text)

    confidence = Column(Float)
    raw_text = Column(Text)
    update_ts = Column(DateTime, nullable=False, default=datetime.utcnow)
    create_ts = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        PrimaryKeyConstraint("file_name", "time", name="ocr_back_results_pk"),
    )
