from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

from config import EXPORT_DIR, LOGGER


class ExcelExporter:
    """Export inventory data to Excel workbooks."""

    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = Path(output_dir or EXPORT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_products(self, products: List[Dict[str, Any]], filename: str = "products.xlsx") -> str:
        df = pd.DataFrame(products)
        path = self.output_dir / filename
        df.to_excel(path, index=False)
        LOGGER.info("Exported products to %s", path)
        return str(path)

    def export_stock(self, rows: List[Dict[str, Any]], filename: str = "stock.xlsx") -> str:
        df = pd.DataFrame(rows)
        path = self.output_dir / filename
        df.to_excel(path, index=False)
        return str(path)

    def export_count_report(self, rows: List[Dict[str, Any]], filename: str = "count_report.xlsx") -> str:
        df = pd.DataFrame(rows)
        path = self.output_dir / filename
        df.to_excel(path, index=False)
        return str(path)

    def export_variance(self, rows: List[Dict[str, Any]], filename: str = "variance.xlsx") -> str:
        df = pd.DataFrame(rows)
        path = self.output_dir / filename
        df.to_excel(path, index=False)
        return str(path)
