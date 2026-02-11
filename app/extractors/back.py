import logging

from app.extractors.llm import extract_fields_with_llm

logger = logging.getLogger(__name__)


def extract_back_fields(texts: list[str]) -> dict:
    """
    用 LLM 從反面 OCR 結果提取所有欄位。
    """
    raw_text = " ".join(texts)
    return extract_fields_with_llm(texts, raw_text, side="back")
