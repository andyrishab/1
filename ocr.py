from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from PIL import Image

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

try:
    from paddleocr import PaddleOCR
except Exception:  # pragma: no cover
    PaddleOCR = None

try:
    import easyocr
except Exception:  # pragma: no cover
    easyocr = None

from config import LOGGER


class OCRProcessor:
    """OCR processor with PaddleOCR and EasyOCR fallback."""

    def __init__(self) -> None:
        self.paddle_reader = None
        self.easy_reader = None
        self._initialize()

    def _initialize(self) -> None:
        if PaddleOCR is not None:
            try:
                self.paddle_reader = PaddleOCR(use_angle_cls=True, lang="en")
                LOGGER.info("PaddleOCR initialized")
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("PaddleOCR failed: %s", exc)
        if easyocr is not None:
            try:
                self.easy_reader = easyocr.Reader(["en", "hi"])
                LOGGER.info("EasyOCR initialized")
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("EasyOCR failed: %s", exc)

    def preprocess(self, image: Any) -> Any:
        if cv2 is None or np is None or Image is None:
            return image
        if isinstance(image, Image.Image):
            image = np.array(image.convert("RGB"))
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    def extract(self, image: Any) -> Dict[str, Any]:
        processed = self.preprocess(image)
        text = ""
        confidence = 0.0
        engine = "none"

        if self.paddle_reader is not None:
            try:
                result = self.paddle_reader.ocr(processed)
                if result:
                    text = self._extract_paddle_result(result)
                    confidence = self._extract_paddle_confidence(result)
                    engine = "paddleocr"
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Paddle OCR error: %s", exc)

        if not text and self.easy_reader is not None:
            try:
                result = self.easy_reader.readtext(processed)
                text = self._extract_easyocr_result(result)
                confidence = self._extract_easyocr_confidence(result)
                engine = "easyocr"
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("EasyOCR error: %s", exc)

        return {
            "text": text,
            "confidence": round(confidence, 2),
            "engine": engine,
            "product_name": self._guess_product_name(text),
            "barcode": self._guess_barcode(text),
            "price": self._guess_price(text),
            "mrp": self._guess_mrp(text),
            "sku": self._guess_sku(text),
            "batch": self._guess_batch(text),
            "expiry": self._guess_expiry(text),
        }

    def _extract_paddle_result(self, result: Any) -> str:
        texts = []
        for item in result[0]:
            if item and len(item) > 1:
                texts.append(str(item[1][0]))
        return "\n".join(texts)

    def _extract_paddle_confidence(self, result: Any) -> float:
        values = []
        for item in result[0]:
            if item and len(item) > 1:
                values.append(float(item[1][1]))
        return sum(values) / len(values) if values else 0.0

    def _extract_easyocr_result(self, result: Any) -> str:
        return "\n".join([item[1] for item in result if item])

    def _extract_easyocr_confidence(self, result: Any) -> float:
        values = [float(item[2]) for item in result if item and len(item) > 2]
        return sum(values) / len(values) if values else 0.0

    def _guess_product_name(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[0] if lines else ""

    def _guess_barcode(self, text: str) -> str:
        for token in re.findall(r"\b\d{8,13}\b", text):
            return token
        return ""

    def _guess_price(self, text: str) -> str:
        matches = re.findall(r"(?:Rs|₹)?\s*(\d+(?:\.\d{1,2})?)", text)
        return matches[0] if matches else ""

    def _guess_mrp(self, text: str) -> str:
        matches = re.findall(r"MRP\s*(\d+(?:\.\d{1,2})?)", text, flags=re.IGNORECASE)
        return matches[0] if matches else ""

    def _guess_sku(self, text: str) -> str:
        matches = re.findall(r"SKU[:\s]*([A-Za-z0-9-]+)", text, flags=re.IGNORECASE)
        return matches[0] if matches else ""

    def _guess_batch(self, text: str) -> str:
        matches = re.findall(r"BATCH[:\s]*([A-Za-z0-9-]+)", text, flags=re.IGNORECASE)
        return matches[0] if matches else ""

    def _guess_expiry(self, text: str) -> str:
        matches = re.findall(r"(?:EXP|EXPIRY)[:\s]*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text, flags=re.IGNORECASE)
        return matches[0] if matches else ""


def run_ocr(image: Any) -> Dict[str, Any]:
    processor = OCRProcessor()
    return processor.extract(image)
