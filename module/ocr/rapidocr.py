"""
RapidOCR 实现

基于 rapidocr-onnxruntime-lite (CPU 压缩专版)。
"""

from PIL import Image

from module.log import Log
from module.ocr.ocr_abc import OCRProvider
from module.rapidocr_onnxruntime import RapidOCR

_log = Log("ocr", "i").logger


class RapidOCRProvider(OCRProvider):
    """基于 rapidocr-onnxruntime-lite 的 OCR 实现"""

    def __init__(self):
        self._engine = RapidOCR()
        _log.info("RapidOCR 引擎初始化完成")

    def ocr(self,
            img: Image.Image,
            confidence: float = 0.6) -> list[dict] | None:
        """对图片进行 OCR 识别

        :return: [{"text", "location", "score"}, ...] 或 None
        """
        result = self._engine(img, use_cls=False)

        if result is None or result[0] is None or len(result[0]) == 0:
            _log.debug("OCR: 未识别到文本")
            return None

        ocr_list: list[dict] = []
        for item in result[0]:
            score = item[2]
            if score > confidence:
                ocr_list.append({
                    "text": item[1],
                    "location": (
                        int(item[0][0][0]) - 1,
                        int(item[0][0][1]) - 1,
                        int(item[0][2][0]) + 1,
                        int(item[0][2][1]) + 1,
                    ),
                    "score": score,
                })

        texts = [t["text"] for t in ocr_list]
        _log.debug("OCR: %d 个文本 → %s", len(ocr_list), texts)
        return ocr_list if ocr_list else None
