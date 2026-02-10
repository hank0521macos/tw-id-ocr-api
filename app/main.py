import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import StandardResponse
from app.routes.ocr import router as ocr_router

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Taiwan ID Card OCR API",
    description="Upload Taiwan ID card image to extract ID number and name",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr_router)


@app.get("/health", response_model=StandardResponse, tags=["Health"])
async def health_check():
    """
    健康檢查端點
    """
    return StandardResponse(
        data={"status": "ok", "service": "tw-id-ocr", "version": "1.0.0"},
        success=True,
        message="Service is running.",
    )
