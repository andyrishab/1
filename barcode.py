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
        self.supported_types = {"QRCODE", "EAN8", "EAN13", "UPCA", "UPCE", "CODE39", "CODE128", "DATAMATRIX"}

    def decode(self, image: Any) -> List[Dict[str, Any]]:
        if pyzbar is None or cv2 is None or np is None or Image is None:
            LOGGER.warning("Barcode decoding unavailable without imaging dependencies")
            return []
        if isinstance(image, Image.Image):
            image = np.array(image.convert("RGB"))
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        results: List[Dict[str, Any]] = []
        try:
            for item in pyzbar.decode(image):
                if item.type.upper() in self.supported_types:
                    results.append({"type": item.type, "data": item.data.decode("utf-8"), "rect": {"left": item.rect.left, "top": item.rect.top, "width": item.rect.width, "height": item.rect.height}})
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Barcode decode error: %s", exc)
        return results


def run_barcode_scan(image: Any) -> List[Dict[str, Any]]:
    return BarcodeProcessor().decode(image)
