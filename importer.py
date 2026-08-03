from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from config import LOGGER


class ExcelImporter:
    """Import product data from Excel files into the JSON store."""

    def __init__(self, upload_dir: str | None = None) -> None:
        self.upload_dir = Path(upload_dir or "uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def import_products(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)
        dataframe = pd.read_excel(file_path)
        dataframe.columns = [str(column).strip().lower().replace(" ", "_") for column in dataframe.columns]
        cleaned_rows: List[Dict[str, Any]] = []
        for _, row in dataframe.iterrows():
            row_dict = row.to_dict()
            cleaned_rows.append({
                "product_name": self._get_value(row_dict, ["product_name", "name", "item_name"]),
                "sku": self._get_value(row_dict, ["sku", "item_sku"]),
                "barcode": self._get_value(row_dict, ["barcode", "qr_code", "upc"]),
                "category": self._get_value(row_dict, ["category", "item_category"]),
                "brand": self._get_value(row_dict, ["brand", "manufacturer"]),
                "current_stock": int(self._to_float(self._get_value(row_dict, ["current_stock", "stock", "inventory"]))),
                "purchase_price": float(self._to_float(self._get_value(row_dict, ["purchase_price", "cost"]))),
                "selling_price": float(self._to_float(self._get_value(row_dict, ["selling_price", "price", "unit_price"]))),
                "notes": self._get_value(row_dict, ["notes", "description"]),
            })
        LOGGER.info("Imported %d rows from %s", len(cleaned_rows), file_path)
        return cleaned_rows

    def _get_value(self, row_dict: Dict[str, Any], keys: List[str]) -> str:
        for key in keys:
            if key in row_dict and row_dict[key] not in (None, ""):
                return str(row_dict[key])
        return ""

    def _to_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
