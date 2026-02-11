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

    if side == "front":
        side_hint = """## 台灣身分證「正面」版面配置

卡片上印刷的固定標籤（由上到下、由左到右）：
  「中華民國國民身分證」（標題，忽略）
  「姓名」→ 右側為持證人姓名（2-4 個中文字，例如：莊欣於、李建佑）
  「出生」＋「年月日」→ 右側為出生日期，格式：民國XX年X月X日
  「性別」→ 右側為「男」或「女」
  「統一編號」→ 右側為身分證字號，格式：1 個大寫英文字母 + 9 個數字（例如 A125439580）
  「發證日期」→ 右側為日期，格式：民國XXX年X月X日
  發證日期後方通常有括號標示發證地點（縣市），例如「（北市）」「（新北市）」「（臺中市）」
  最後標示發證類型：「換發」「補發」或「初發」

## 常見 OCR 問題與處理規則
- 浮水印雜訊：IWANT、ANTAIW、TAIWAN 等英文字混在文字中，請忽略。
- APP 名稱雜訊：如「限聚流去哪喫APP」「藍新金流使用」等，請忽略。
- 「中華民國國民身分證」「國民」「身分證」等標題文字，請忽略。
- 姓名可能與「姓名」標籤黏在一起，如「姓名莊欣於」→ 姓名=莊欣於。
- 姓名可能被拆到不同區塊，如「姓名李」+「建佑」→ 姓名=李建佑。
- 「年月日」三個字是標籤的一部分，不是日期的值，請忽略。
- 統一編號中英文字母可能被 OCR 誤判（如 O→0、I→1），請根據格式修正。
- 發證地點可能用簡稱：「北市」=臺北市、「高市」=高雄市、「中市」=臺中市、「南市」=臺南市、「桃市」=桃園市。請保留原始辨識值，不要自行展開。"""
    else:
        side_hint = """## 台灣身分證「反面」版面配置

卡片上印刷的固定標籤（由上到下）：
  「父」→ 右側為父親姓名（2-4 個中文字）
  「母」→ 右側為母親姓名（2-4 個中文字）
  「配偶」→ 右側為配偶姓名（2-4 個中文字），未婚者此欄空白
  「役別」→ 右側為役別（男性：免役、常備役、替代役、未服役等；女性此欄空白）
  「出生地」→ 右側為出生地（縣市名稱，如「臺北市」「新北市」）
  「住址」→ 右側為完整戶籍地址（縣市＋區＋里＋鄰＋路段＋號＋樓）
  底部有一串純數字流水號（如 0090103724），不屬於任何欄位，請忽略。

## 常見 OCR 問題與處理規則
- 最關鍵問題：OCR 會把多個欄位的標籤和值黏在一起，必須根據標籤斷詞。
  例如：「父惠玉母鄔惠英」→ 父=惠玉、母=鄔惠英（這裡的「父」不是姓，是標籤）
  例如：「配偶莊永」+「福役別」→ 配偶=莊永福（「福」被拆到下一個區塊，而「役別」是下一個標籤）
  例如：「役別免役出生地」→ 役別=免役、出生地的值在下一個區塊
- 切分規則：「父」「母」「配偶」「役別」「出生地」「住址」這六個詞是固定標籤，兩個標籤之間的中文字就是前一個標籤的值。
- 姓名只包含中文字，不會包含數字或英文。
- 住址可能跨多個 OCR 區塊，請完整合併成一個地址字串。
- 浮水印雜訊：IWANT、ANTAIW、TAIWAN 等英文字請忽略。
- 女性沒有役別，如果看不到役別的值，請填 null。
- 配偶欄空白（未婚）時，請填 null。"""

    prompt = f"""你是台灣身分證 OCR 結果的欄位萃取專家。請從以下 OCR 辨識結果中，準確提取身分證{("正面" if side == "front" else "反面")}的欄位值。

{side_hint}

---

OCR 文字區塊（按偵測順序排列，值可能被截斷分散在相鄰區塊中，請跨區塊合併）：
{json.dumps(texts, ensure_ascii=False)}

OCR 完整文字：
{raw_text}

---

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
