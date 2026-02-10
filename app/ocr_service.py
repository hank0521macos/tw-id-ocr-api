import logging
from paddleocr import PaddleOCR
from opencc import OpenCC

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self):
        """初始化 PaddleOCR（繁體中文）"""
        logger.info("初始化 PaddleOCR (繁體中文)...")
        self.ocr = PaddleOCR(
            lang="chinese_cht",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        self.s2t = OpenCC("s2t")
        logger.info("PaddleOCR 初始化完成")

    def recognize(self, image_path: str) -> dict:
        """
        執行 OCR 辨識，回傳基礎結果

        Returns:
            dict with keys: texts, scores, raw_text, confidence

        Raises:
            RuntimeError: OCR 識別失敗
        """
        logger.info(f"開始辨識圖片: {image_path}")
        result = list(self.ocr.predict(image_path))

        if not result:
            logger.error("OCR 未能辨識任何文字")
            raise RuntimeError("OCR failed to recognize any text from image.")

        res = result[0]
        texts = [self.s2t.convert(t) for t in res["rec_texts"]]
        scores = list(res["rec_scores"])

        logger.info(f"辨識到 {len(texts)} 個文字區塊")
        for i, (text, score) in enumerate(zip(texts, scores), 1):
            logger.info(f"  [{i}] '{text}' (信心度: {score:.2f})")

        if not texts:
            logger.error("文字列表為空")
            raise RuntimeError("OCR failed to recognize any text from image.")

        raw_text = " ".join(texts)
        avg_confidence = sum(scores) / len(scores) if scores else 0.0
        logger.info(f"平均信心度: {avg_confidence:.2f}")
        logger.info(f"完整文字: {raw_text}")

        return {
            "texts": texts,
            "scores": scores,
            "raw_text": raw_text,
            "confidence": round(avg_confidence, 2),
        }
