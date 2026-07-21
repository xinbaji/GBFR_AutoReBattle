"""
OCR 抽象接口

定义 OCR 识别统一协议，便于未来切换 OCR 引擎
（例如从 RapidOCR 切换到 PaddleOCR / Tesseract）。
"""

from abc import ABC, abstractmethod

from PIL import Image


class OCRProvider(ABC):
    """OCR 抽象基类

    子类必须实现:
        ocr()   – 对图片进行文字识别

    返回统一格式:
        list[dict] 或 None
        dict = {
            "text":     str,        # 识别文字
            "location": tuple[int, int, int, int],  # (x1, y1, x2, y2)
            "score":    float,      # 置信度
        }
    """

    @abstractmethod
    def ocr(self,
            img: Image.Image,
            confidence: float = 0.6) -> list[dict] | None:
        """对 PIL Image 进行 OCR 识别

        :param img:        PIL Image 对象
        :param confidence: 最低置信度阈值（低于此值的识别结果被过滤）
        :return:           [{"text": str, "location": (x1,y1,x2,y2), "score": float}, ...]
                           没有识别到文本时返回 None
        """
        ...
