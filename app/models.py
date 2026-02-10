from pydantic import BaseModel
from typing import Optional, Any


class StandardResponse(BaseModel):
    data: Optional[Any] = None
    success: bool
    message: str


class FrontOCRResult(BaseModel):
    name: Optional[str] = None
    birthday: Optional[str] = None
    issue_date: Optional[str] = None
    issue_type: Optional[str] = None
    id_number: Optional[str] = None
    gender: Optional[str] = None
    issue_location: Optional[str] = None
    confidence: float
    raw_text: str


class BackOCRResult(BaseModel):
    father: Optional[str] = None
    mother: Optional[str] = None
    spouse: Optional[str] = None
    military_service: Optional[str] = None
    birthplace: Optional[str] = None
    address: Optional[str] = None
    confidence: float
    raw_text: str
