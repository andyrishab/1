import builtins
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_ocr_and_barcode_import_without_cv2(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "cv2":
            raise ImportError("libGL.so.1")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("ocr", None)
    sys.modules.pop("barcode", None)

    ocr = importlib.import_module("ocr")
    barcode = importlib.import_module("barcode")

    assert ocr.cv2 is None
    assert barcode.cv2 is None
