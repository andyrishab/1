from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

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
    from pyzbar import pyzbar
except Exception:  # pragma: no cover
    pyzbar = None

from config import LOGGER


class BarcodeProcessor:
    """Barcode and QR scanner implementation."""

    def __init__(self) -> None:
        self.supported_types = {
            "QRCODE", "EAN8", "EAN13", "UPCA", "UPCE",
            "CODE39", "CODE128", "DATAMATRIX", "ITF", "PDF417",
        }

    def _to_bgr(self, image: Any) -> Any:
        """Convert any input image to a BGR numpy array suitable for pyzbar."""
        if Image is not None and isinstance(image, Image.Image):
            # PIL → numpy RGB → BGR
            image = np.array(image.convert("RGB"))
            return image[:, :, ::-1]  # RGB to BGR

        if np is not None and cv2 is not None and isinstance(image, np.ndarray):
            if image.ndim == 2:
                # Already grayscale — convert to BGR
                return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            if image.ndim == 3 and image.shape[2] == 4:
                # BGRA → BGR
                return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            if image.ndim == 3 and image.shape[2] == 3:
                return image  # already BGR
        return image

    def _preprocess(self, bgr: Any) -> Any:
        """
        Apply grayscale + adaptive threshold to improve barcode detection
        under poor lighting or low-contrast images.
        Returns a list of candidate images to try.
        """
        candidates = [bgr]
        if cv2 is None or np is None:
            return candidates
        try:
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            candidates.append(gray)
            # Adaptive threshold — helps with shadows and uneven lighting
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2,
            )
            candidates.append(thresh)
        except Exception:
            pass
        return candidates

    def decode(self, image: Any) -> List[Dict[str, Any]]:
        if pyzbar is None or cv2 is None or np is None or Image is None:
            LOGGER.warning("Barcode decoding unavailable without imaging dependencies")
            return []

        bgr = self._to_bgr(image)
        seen: set = set()
        results: List[Dict[str, Any]] = []

        for candidate in self._preprocess(bgr):
            try:
                for item in pyzbar.decode(candidate):
                    if item.type.upper() not in self.supported_types:
                        continue
                    data = item.data.decode("utf-8", errors="replace")
                    key = (item.type, data)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({
                        "type": item.type,
                        "data": data,
                        "rect": {
                            "left": item.rect.left,
                            "top": item.rect.top,
                            "width": item.rect.width,
                            "height": item.rect.height,
                        },
                    })
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Barcode decode error on candidate: %s", exc)

        return results


def run_barcode_scan(image: Any) -> List[Dict[str, Any]]:
    return BarcodeProcessor().decode(image)
