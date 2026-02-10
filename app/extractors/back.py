import re
import logging

logger = logging.getLogger(__name__)


def extract_back_fields(texts: list[str]) -> dict:
    """
    從反面 OCR 結果提取所有欄位

    Returns:
        dict with keys: father, mother, spouse, military_service,
                        birthplace, address
        (only non-None values included)
    """
    data: dict = {}

    father = _extract_label_value(texts, "父")
    if father:
        data["father"] = father
        logger.info(f"提取到父: {father}")

    mother = _extract_label_value(texts, "母")
    if mother:
        data["mother"] = mother
        logger.info(f"提取到母: {mother}")

    spouse = _extract_label_value(texts, "配偶")
    if spouse:
        data["spouse"] = spouse
        logger.info(f"提取到配偶: {spouse}")

    military_service = _extract_label_value(texts, "役別")
    if military_service:
        data["military_service"] = military_service
        logger.info(f"提取到役別: {military_service}")

    birthplace = _extract_label_value(texts, "出生地")
    if birthplace:
        data["birthplace"] = birthplace
        logger.info(f"提取到出生地: {birthplace}")

    address = _extract_label_value(texts, "住址", multi_block=True)
    if address:
        data["address"] = address
        logger.info(f"提取到住址: {address}")

    return data


def _extract_label_value(
    texts: list[str], label: str, multi_block: bool = False
) -> str | None:
    """
    通用的標籤-值提取方法
    在 texts 中找到包含 label 的區塊，提取其後的中文值

    Args:
        texts: OCR 辨識的文字區塊列表
        label: 要找的標籤（如「父」「母」「配偶」）
        multi_block: 是否將後續多個區塊合併（用於住址等長欄位）
    """
    found_label = False
    collected_parts: list[str] = []

    for text in texts:
        if found_label:
            # 遇到其他標籤就停止收集
            if re.search(r"(父|母|配偶|役別|出生地|住址)", text) and label not in text:
                break
            value = re.sub(r"[：:\s]", "", text).strip()
            if value:
                # 純數字區塊為空白證流水號，不屬於欄位值
                if re.fullmatch(r"\d+", value):
                    break
                if not multi_block:
                    return value
                collected_parts.append(value)
            continue

        if label in text:
            # 同一區塊內 label 後面的值
            remaining = text.split(label)[-1].strip()
            remaining = re.sub(r"[：:\s]", "", remaining)
            # 截斷同一區塊內的其他標籤（如「父吳啟禎母吳美月」）
            other_labels = [lb for lb in ("父", "母", "配偶", "役別", "出生地", "住址") if lb != label]
            for lb in other_labels:
                if lb in remaining:
                    remaining = remaining[:remaining.index(lb)]
            remaining = remaining.strip()
            if remaining:
                chinese_match = re.search(r"[\u4e00-\u9fa5]+", remaining)
                if chinese_match:
                    if not multi_block:
                        return chinese_match.group(0)
                    collected_parts.append(chinese_match.group(0))
            found_label = True

    if collected_parts:
        return "".join(collected_parts)
    return None
