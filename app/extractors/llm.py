import json
import logging

from openai import OpenAI

from app.config import LLM_TOKEN

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_TOKEN)
    return _client


def extract_fields_with_llm(texts: list[str], raw_text: str, side: str) -> dict:
    """
    用 GPT-4o-mini 從 OCR raw text 中萃取身分證欄位。

    Args:
        texts: OCR 辨識的文字區塊列表
        raw_text: 所有文字合併的字串
        side: "front" 或 "back"

    Returns:
        dict with extracted fields
    """
    if side == "front":
        schema = {
            "name": "姓名（2-4個中文字）",
            "id_number": "統一編號（1個英文字母+9個數字，如 A123456789）",
            "birthday": "出生年月日（格式：民國XX年X月X日）",
            "gender": "性別（男 或 女）",
            "issue_date": "發證日期（格式：民國XXX年X月X日）",
            "issue_type": "發證類型（換發、補發、初發）",
            "issue_location": "發證地點（縣市名稱）",
        }
    else:
        schema = {
            "father": "父親姓名",
            "mother": "母親姓名",
            "spouse": "配偶姓名（沒有則 null）",
            "military_service": "役別（如：免役、常備役、替代役等，沒有則 null）",
            "birthplace": "出生地",
            "address": "住址（完整地址）",
        }

    schema_str = json.dumps(schema, ensure_ascii=False, indent=2)

    prompt = f"""你是台灣身分證 OCR 結果的欄位萃取專家。
以下是 OCR 辨識出的文字，可能包含雜訊（如浮水印 IWANT、APP名稱等），請忽略雜訊，準確提取身分證{("正面" if side == "front" else "反面")}的欄位。

OCR 文字區塊：
{json.dumps(texts, ensure_ascii=False)}

OCR 完整文字：
{raw_text}

請提取以下欄位，以 JSON 格式回傳，無法辨識的欄位填 null：
{schema_str}

只回傳 JSON，不要其他文字。"""

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        logger.info(f"LLM 萃取結果 ({side}): {result}")
        return {k: v for k, v in result.items() if v is not None}
    except Exception as e:
        logger.error(f"LLM 萃取失敗: {e}", exc_info=True)
        return {}
