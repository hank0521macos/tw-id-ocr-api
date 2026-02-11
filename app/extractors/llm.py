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
            "id_number": "身分證字號（1個英文字母+9個數字，如 A123456789）",
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
        side_hint = """## 台灣中華民國國民身分證「正面」版面配置

卡片上印刷的固定標籤（由上到下、由左到右）：
  「中華民國國民身分證」（標題，忽略）
  「姓名」→ 右側為持證人姓名（2-4 個中文字，例如：莊欣於、李建佑、王仰聖）
  「出生」＋「年月日」→ 右側為出生日期，格式：民國XX年X月X日
  「性別」→ 右側只有兩種值：「男」或「女」，不會有其他值
  「身分證字號」→ 身分證字號（通常出現在卡片下方獨立區域）
  「發證日期」→ 右側為日期，格式：民國XXX年X月X日
  發證日期後方有括號標示發證地點，然後接發證類型

## 身分證字號（身分證字號）格式與驗證規則
- 格式：1 個大寫英文字母 + 9 個數字，共 10 碼
- 第 1 碼：大寫英文字母 A-Z（代表發證地）
- 第 2 碼：1（男）或 2（女），新式可為 8 或 9
- 第 3-9 碼：數字 0-9
- 第 10 碼：檢查碼
- 重要：身分證字號的第 2 碼與性別欄位必須一致（1=男、2=女）
- OCR 常見誤判修正：O→0、I→1、l→1、S→5、B→8、Z→2、G→6、D→0
- 身分證字號通常獨立出現，不會與其他標籤黏在一起，請從 OCR 文字中找到符合「1英文+9數字」格式的字串

## 發證地點（固定值，只會是以下之一）
台灣的縣市名稱，常見值：
- 完整名稱：臺北市、新北市、桃園市、臺中市、臺南市、高雄市、基隆市、新竹市、嘉義市、新竹縣、苗栗縣、彰化縣、南投縣、雲林縣、嘉義縣、屏東縣、宜蘭縣、花蓮縣、臺東縣、澎湖縣、金門縣、連江縣
- OCR 可能辨識出簡稱：北市、新北市、桃市、中市、南市、高市 等
- 請保留 OCR 辨識出的原始值，不要自行修改

## 發證類型（固定值，只會是以下三種之一）
- 換發、補發、初發

## 常見 OCR 雜訊（請完全忽略）
- 浮水印：IWANT、ANTAIW、TAIWAN、AN 等英文字
- APP 名稱：「限聚流去哪喫APP」「藍新金流使用」等
- 「中華民國國民身分證」「國民」「身分證」等標題文字
- 「婚#」等無意義符號
- 「年月日」三個字是出生欄位的標籤，不是日期的值

## 欄位提取注意事項
- 姓名可能與標籤黏在一起：「姓名王仰聖」→ 姓名=王仰聖
- 姓名可能被拆到不同區塊：「姓名張」+「信華」→ 姓名=張信華
- 性別只能是「男」或「女」，可用身分證字號第 2 碼交叉驗證（1=男、2=女）"""
    else:
        side_hint = """## 台灣中華民國國民身分證「反面」版面配置

卡片上印刷的固定標籤（由上到下）：
  「父」→ 右側為父親姓名（2-4 個中文字）
  「母」→ 右側為母親姓名（2-4 個中文字）
  「配偶」→ 右側為配偶姓名（2-4 個中文字），未婚者此欄空白
  「役別」→ 右側為役別，女性此欄空白
  「出生地」→ 右側為出生地（縣市名稱）
  「住址」→ 右側為完整戶籍地址
  底部有一串純數字流水號（如 0090103724），不屬於任何欄位，請忽略。

## 役別（固定值，男性只會是以下之一）
- 免役、常備役、替代役、未服役、禁役、後備役
- 女性沒有役別，填 null

## 出生地（固定值，只會是台灣的縣市）
- 臺北市、新北市、桃園市、臺中市、臺南市、高雄市、基隆市、新竹市、嘉義市
- 新竹縣、苗栗縣、彰化縣、南投縣、雲林縣、嘉義縣、屏東縣、宜蘭縣、花蓮縣、臺東縣、澎湖縣、金門縣、連江縣
- 也可能是中國大陸省份（早期移民）

## 常見 OCR 問題與處理規則
- 最關鍵問題：OCR 會把多個欄位的標籤和值黏在一起，必須根據標籤斷詞。
  例如：「父惠玉母鄔惠英」→ 父=惠玉、母=鄔惠英（「父」和「母」是標籤，不是姓氏的一部分）
  例如：「配偶莊永」+「福役別」→ 配偶=莊永福（「福」被拆到下一個區塊，「役別」是下一個標籤的開頭）
  例如：「役別免役出生地」→ 役別=免役、出生地的值在下一個區塊
  例如：「住址新北市板橋區」+「文化路一段100號」→ 住址=新北市板橋區文化路一段100號
- 切分規則：「父」「母」「配偶」「役別」「出生地」「住址」這六個詞是固定標籤，兩個標籤之間的中文字就是前一個標籤的值。
- 人名只包含中文字（2-4字），不會包含數字或英文。
- 住址可能跨多個 OCR 區塊，請完整合併成一個地址字串。住址格式：縣市＋區/鄉/鎮＋里＋鄰＋路/街＋段＋巷＋弄＋號＋樓。
- 浮水印雜訊：IWANT、ANTAIW、TAIWAN 等英文字請忽略。
- 配偶欄空白（未婚）時，填 null。"""

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


def test_llm_connection() -> dict:
    """測試 OpenAI 連線是否正常"""
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "回傳 JSON: {\"status\": \"ok\"}"}],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=20,
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "connected": True,
            "model": response.model,
            "response": result,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}
