import re
import logging

logger = logging.getLogger(__name__)

# 台灣身分證字號：首字母 → 對應數值（用於驗證 checksum）
_LETTER_MAP = {
    "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15,
    "G": 16, "H": 17, "I": 34, "J": 18, "K": 19, "L": 20,
    "M": 21, "N": 22, "O": 35, "P": 23, "Q": 24, "R": 25,
    "S": 26, "T": 27, "U": 28, "V": 29, "W": 32, "X": 30,
    "Y": 31, "Z": 33,
}

# OCR 常見誤判：字母 ↔ 數字
_OCR_TO_DIGIT = {"O": "0", "o": "0", "I": "1", "l": "1", "S": "5", "s": "5",
                 "B": "8", "Z": "2", "z": "2", "G": "6", "g": "6", "b": "6",
                 "D": "0", "q": "9"}
_OCR_TO_LETTER = {"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G"}


def extract_front_fields(texts: list[str], raw_text: str) -> dict:
    """
    從正面 OCR 結果提取所有欄位

    Returns:
        dict with keys: name, birthday, issue_date, issue_type,
                        id_number, gender, issue_location
        (only non-None values included)
    """
    data: dict = {}

    id_number = _extract_id_number(texts, raw_text)
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


# ──────────────────────────────────────────────
# 身分證字號
# ──────────────────────────────────────────────

def _verify_id_checksum(id_number: str) -> bool:
    """
    驗證台灣身分證字號 checksum
    公式：首字母轉 2 位數，加權總和 mod 10 == 0
    """
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


def _fix_ocr_id(candidate: str) -> str | None:
    """
    嘗試修正 OCR 誤判的身分證字號
    - 第 1 碼：必須是大寫英文，數字嘗試轉字母
    - 第 2 碼：必須是 1 或 2（或新式 8, 9）
    - 第 3-10 碼：必須是數字，字母嘗試轉數字
    """
    if len(candidate) != 10:
        return None

    chars = list(candidate.upper())

    # 修正第 1 碼（應為字母）
    if chars[0].isdigit():
        if chars[0] in _OCR_TO_LETTER:
            chars[0] = _OCR_TO_LETTER[chars[0]]
        else:
            return None
    if chars[0] not in _LETTER_MAP:
        return None

    # 修正第 2-10 碼（應為數字）
    for i in range(1, 10):
        if not chars[i].isdigit():
            if chars[i] in _OCR_TO_DIGIT:
                chars[i] = _OCR_TO_DIGIT[chars[i]]
            else:
                return None

    # 第 2 碼只能是 1, 2, 8, 9
    if chars[1] not in ("1", "2", "8", "9"):
        return None

    result = "".join(chars)
    return result


def _extract_id_number(texts: list[str], raw_text: str) -> str | None:
    """
    提取身分證號（含 OCR 容錯）
    1. 直接比對標準格式
    2. 找疑似 10 碼候選，嘗試 OCR 修正
    3. 用 checksum 驗證
    """
    # 先清理：移除所有空白
    cleaned = re.sub(r"\s+", "", raw_text)

    # 策略 1：直接比對標準格式 [A-Z][1289]\d{8}
    match = re.search(r"[A-Z][1289]\d{8}", cleaned)
    if match:
        candidate = match.group(0)
        if _verify_id_checksum(candidate):
            return candidate
        # checksum 不過也先記著，後面沒更好的就用它
        fallback = candidate
    else:
        fallback = None

    # 策略 2：從各 text block 找疑似候選（含字母數字混合的 10 碼）
    all_text = cleaned
    for text in texts:
        all_text += " " + re.sub(r"\s+", "", text)

    # 找所有可能的 10 碼英數混合序列
    candidates = re.findall(r"[A-Za-z0-9]{10}", all_text)
    for candidate in candidates:
        fixed = _fix_ocr_id(candidate)
        if fixed and _verify_id_checksum(fixed):
            return fixed

    # 策略 3：放寬搜尋 — 找 1 字母開頭 + 後面有 9 個數字/字母的模式
    # 處理中間被插入特殊字元的情況（如 E12-461-2445）
    for m in re.finditer(r"[A-Za-z]", all_text):
        start = m.start()
        # 從這個字母開始，收集後面的英數字元（跳過特殊字元）
        following = re.findall(r"[A-Za-z0-9]", all_text[start:start + 15])
        if len(following) >= 10:
            candidate = "".join(following[:10])
            fixed = _fix_ocr_id(candidate)
            if fixed and _verify_id_checksum(fixed):
                return fixed

    # 沒有通過 checksum 的，退回策略 1 的結果
    if fallback:
        return fallback

    # 最後嘗試：放寬第二碼限制 [A-Z]\d{9}
    match = re.search(r"[A-Z]\d{9}", cleaned)
    if match:
        return match.group(0)

    return None


# ──────────────────────────────────────────────
# 姓名
# ──────────────────────────────────────────────

def _extract_name(texts: list[str]) -> str | None:
    """
    提取姓名
    策略：找「姓名」關鍵字後面的中文字串
    處理 OCR 把姓和名拆成不同 block 的情況（如「姓名蕭」+「顥恒」）
    """
    exclude_keywords = {
        "中華民國", "國民身分證", "身分證", "統一編號", "出生", "發證",
        "住址", "役別", "配偶", "姓名", "性別", "出生地", "父", "母",
        "補發", "換發", "初發", "內政部", "國民", "身分", "民國",
        "年月日", "日期",
    }

    full_text = " ".join(texts)

    # 策略 1：找「姓名」關鍵字後的文字（完整 2-4 字在同一區塊）
    name_pattern = re.search(r"姓\s*名\s*[：:]*\s*([\u4e00-\u9fa5]{2,4})", full_text)
    if name_pattern:
        candidate = name_pattern.group(1)
        if candidate not in exclude_keywords:
            return candidate

    # 策略 2：處理姓名被拆成多個 block 的情況
    for i, text in enumerate(texts):
        if "姓名" not in text and "姓 名" not in text:
            continue

        # 取「姓名」後面的部分
        remaining = re.split(r"姓\s*名", text)[-1].strip()
        # 只保留中文字元
        surname_chars = re.findall(r"[\u4e00-\u9fa5]", remaining)

        if len(surname_chars) >= 2:
            candidate = "".join(surname_chars[:4])
            if candidate not in exclude_keywords:
                return candidate

        # 姓名 block 只有 0-1 個字（姓氏），需要往後找名字
        surname = "".join(surname_chars)
        for j in range(i + 1, min(i + 4, len(texts))):
            next_chars = re.findall(r"[\u4e00-\u9fa5]", texts[j])
            if not next_chars:
                continue
            next_word = "".join(next_chars)
            # 跳過干擾詞
            if next_word in exclude_keywords:
                continue
            candidate = surname + next_word
            if len(candidate) >= 2:
                return candidate[:4]

        if surname and len(surname) >= 2:
            return surname

    # 策略 3：從所有文字中找最可能的姓名（排除已知詞彙）
    candidates = re.findall(r"[\u4e00-\u9fa5]{2,4}", full_text)
    for candidate in candidates:
        if candidate not in exclude_keywords:
            return candidate

    return None


# ──────────────────────────────────────────────
# 其他欄位
# ──────────────────────────────────────────────

def _extract_birthday(raw_text: str) -> str | None:
    """提取出生年月日，格式：民國XX年X月X日"""
    match = re.search(r"出生\s*[：:]*\s*(民國\s*\d{1,3}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)", raw_text)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    # 備用：找「民國...年...月...日」且前方不是「發證」
    for m in re.finditer(r"民國\s*\d{1,3}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日", raw_text):
        preceding = raw_text[max(0, m.start() - 7):m.start()]
        if "發證" not in preceding:
            return re.sub(r"\s+", "", m.group())
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
    # 嘗試找括號內的地點（含簡稱如「北市」）
    match = re.search(r"[（(]\s*([\u4e00-\u9fa5]{1,4}[縣市])\s*[）)]", raw_text)
    if match:
        return match.group(1)
    # 嘗試找「換發/補發/初發」前的括號
    match = re.search(r"[（(]\s*([\u4e00-\u9fa5]{1,4})\s*[）)]\s*(?:換發|補發|初發)", raw_text)
    if match:
        return match.group(1)
    # 嘗試找「換發/補發/初發」後面的縣市
    match = re.search(r"(?:換發|補發|初發)\s*[（(]?\s*([\u4e00-\u9fa5]{2,4}[縣市])", raw_text)
    if match:
        return match.group(1)
    # 嘗試找獨立的縣市名稱（排除「出生地」後面的）
    match = re.search(r"(?<!出生地)([\u4e00-\u9fa5]{1,3}[縣市])", raw_text)
    if match:
        return match.group(1)
    return None
