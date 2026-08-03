import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ui import InventoryAppController


def test_build_scan_payload_prefers_scanned_barcode_and_ocr_fields():
    controller = InventoryAppController()

    ocr_result = {
        "product_name": "Alpha Drink",
        "sku": "SKU-123",
        "barcode": "999",
    }
    barcode_result = [["EAN13", "1000000000000"]]

    payload = controller.build_scan_payload(ocr_result, barcode_result)

    assert payload["product_name"] == "Alpha Drink"
    assert payload["sku"] == "SKU-123"
    assert payload["barcode"] == "1000000000000"
