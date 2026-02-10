import re
import logging

logger = logging.getLogger(__name__)


def extract_front_fields(texts: list[str], raw_text: str) -> dict:
    """
    從正面 OCR 結果提取所有欄位

    Returns:
        dict with keys: name, birthday, issue_date, issue_type,
                        id_number, gender, issue_location
        (only non-None values included)
    """
    data: dict = {}

    id_number = _extract_id_number(raw_text)
    if id_number:
        data["id_number"] = id_number
        logger.info(f"提取到身分證號: {id_number}")

    name = _extract_name(texts)
    if name:
        data["name"] = name
        logger.info(f"提取到姓名: {name}")

    birthday = _extract_birthday(raw_text)
    if birthday:
        data["birthday"] = birthday
        logger.info(f"提取到出生日期: {birthday}")

    gender = _extract_gender(raw_text)
    if gender:
        data["gender"] = gender
        logger.info(f"提取到性別: {gender}")

    issue_date = _extract_issue_date(raw_text)
    if issue_date:
        data["issue_date"] = issue_date
        logger.info(f"提取到發證日期: {issue_date}")

    issue_type = _extract_issue_type(raw_text)
    if issue_type:
        data["issue_type"] = issue_type
        logger.info(f"提取到發證類型: {issue_type}")

    issue_location = _extract_issue_location(raw_text)
    if issue_location:
        data["issue_location"] = issue_location
        logger.info(f"提取到發證地點: {issue_location}")

    return data


def _extract_id_number(text: str) -> str | None:
    """
    提取身分證號
    台灣身分證格式：1 個大寫英文 + 1 或 2 + 8 位數字
    """
    match = re.search(r"[A-Z][12]\d{8}", text)
    return match.group(0) if match else None


def _extract_name(texts: list[str]) -> str | None:
    """
    提取姓名
    策略：找「姓名」關鍵字後面的中文字串，或找連續 2-4 個中文字
    排除常見的非姓名中文詞彙
    """
    exclude_keywords = {
        "中華民國", "國民身分證", "身分證", "統一編號", "出生", "發證",
        "住址", "役別", "配偶", "姓名", "性別", "出生地", "父", "母",
        "補發", "換發", "初發", "內政部", "國民", "身分",
    }

    full_text = " ".join(texts)

    # 策略 1：找「姓名」關鍵字後的文字
    name_pattern = re.search(r"姓\s*名\s*[：:]*\s*([\u4e00-\u9fa5]{2,4})", full_text)
    if name_pattern:
        candidate = name_pattern.group(1)
        if candidate not in exclude_keywords:
            return candidate

    # 策略 2：在「姓名」關鍵字之後的下一個文字區塊中尋找
    found_name_label = False
    for text in texts:
        if "姓名" in text:
            remaining = text.split("姓名")[-1].strip()
            remaining = re.sub(r"[：:\s]", "", remaining)
            match = re.search(r"[\u4e00-\u9fa5]{2,4}", remaining)
            if match and match.group(0) not in exclude_keywords:
                return match.group(0)
            found_name_label = True
            continue

        if found_name_label:
            match = re.search(r"[\u4e00-\u9fa5]{2,4}", text)
            if match and match.group(0) not in exclude_keywords:
                return match.group(0)
            found_name_label = False

    # 策略 3：從所有文字中找最可能的姓名
    candidates = re.findall(r"[\u4e00-\u9fa5]{2,4}", full_text)
    for candidate in candidates:
        if candidate not in exclude_keywords:
            return candidate

    return None


def _extract_birthday(raw_text: str) -> str | None:
    """提取出生年月日，格式：民國XX年X月X日"""
    match = re.search(r"出生\s*[：:]*\s*(民國\s*\d{1,3}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)", raw_text)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    # 備用：找「民國...年...月...日」且前方不是「發證」
    match = re.search(r"(?<!發證.{0,5})(民國\s*\d{1,3}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)", raw_text)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    return None


def _extract_gender(raw_text: str) -> str | None:
    """提取性別：男 或 女"""
    match = re.search(r"性\s*別\s*[：:]*\s*(男|女)", raw_text)
    if match:
        return match.group(1)
    # 備用：透過身分證號第二碼判斷（1=男, 2=女）
    id_match = re.search(r"[A-Z]([12])\d{8}", raw_text)
    if id_match:
        return "男" if id_match.group(1) == "1" else "女"
    return None


def _extract_issue_date(raw_text: str) -> str | None:
    """提取發證日期"""
    match = re.search(r"發證日期\s*[：:]*\s*(民國\s*\d{1,3}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)", raw_text)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    # 備用：找第二個「民國...年...月...日」
    dates = re.findall(r"民國\s*\d{1,3}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日", raw_text)
    if len(dates) >= 2:
        return re.sub(r"\s+", "", dates[1])
    return None


def _extract_issue_type(raw_text: str) -> str | None:
    """提取發證類型：換發 / 補發 / 初發"""
    match = re.search(r"(換發|補發|初發)", raw_text)
    return match.group(1) if match else None


def _extract_issue_location(raw_text: str) -> str | None:
    """提取發證地點（通常在發證日期附近的括號內或後方的縣市名稱）"""
    # 嘗試找括號內的地點
    match = re.search(r"[（(]\s*([\u4e00-\u9fa5]{2,4}[縣市])\s*[）)]", raw_text)
    if match:
        return match.group(1)
    # 嘗試找「換發/補發/初發」後面的縣市
    match = re.search(r"(?:換發|補發|初發)\s*[（(]?\s*([\u4e00-\u9fa5]{2,4}[縣市])", raw_text)
    if match:
        return match.group(1)
    # 嘗試找獨立的縣市名稱（排除「出生地」後面的）
    match = re.search(r"(?<!出生地.{0,3})([\u4e00-\u9fa5]{1,3}[縣市])", raw_text)
    if match:
        return match.group(1)
    return None
