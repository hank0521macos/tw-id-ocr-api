import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    """取得 DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """建立所有 table（如果不存在）+ migrate 新欄位"""
    from app.db_models import Store, OcrTask, OcrFrontResult, OcrBackResult  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("資料庫 table 初始化完成")
