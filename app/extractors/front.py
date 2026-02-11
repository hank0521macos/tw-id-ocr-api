import re
import logging

from app.extractors.llm import extract_fields_with_llm

logger = logging.getLogger(__name__)

# 台灣身分證字號：首字母 → 對應數值（用於驗證 checksum）
_LETTER_MAP = {
    "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15,
    "G": 16, "H": 17, "I": 34, "J": 18, "K": 19, "L": 20,
    "M": 21, "N": 22, "O": 35, "P": 23, "Q": 24, "R": 25,
    "S": 26, "T": 27, "U": 28, "V": 29, "W": 32, "X": 30,
    "Y": 31, "Z": 33,
}


def _verify_id_checksum(id_number: str) -> bool:
    """驗證台灣身分證字號 checksum"""
    if len(id_number) != 10:
        return False
    letter = id_number[0].upper()
    if letter not in _LETTER_MAP:
        return False
    try:
        digits = [int(d) for d in id_number[1:]]
    except ValueError:
        return False

    code = _LETTER_MAP[letter]
    n1, n0 = divmod(code, 10)
    weights = [9, 8, 7, 6, 5, 4, 3, 2, 1]
    total = n1 + n0 * 9
    total += sum(d * w for d, w in zip(digits, weights))
    return total % 10 == 0


def extract_front_fields(texts: list[str], raw_text: str) -> dict:
    """
    用 LLM 從正面 OCR 結果提取所有欄位，並用 checksum 驗證身分證字號。
    """
    data = extract_fields_with_llm(texts, raw_text, side="front")

    # 身分證字號 checksum 驗證
    id_number = data.get("id_number")
    if id_number:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", id_number).upper()
        if len(cleaned) == 10 and _verify_id_checksum(cleaned):
            data["id_number"] = cleaned
        else:
            logger.warning(f"LLM 回傳的身分證號 checksum 不通過: {id_number}，保留原值")

    return data
