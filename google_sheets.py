from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import gspread
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from gspread.exceptions import SpreadsheetNotFound

from config import CONFIG, LOGGER, SHEETS_FILE, ensure_json_file, load_json, save_json
from utils import safe_text, utc_now


class GoogleSheetsService:
    """Sync inventory data to Google Sheets."""

    def __init__(self, sheet_name: Optional[str] = None) -> None:
        self.sheet_name = sheet_name or CONFIG.sheet_name
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[Any] = None
        self.worksheet: Optional[Any] = None
        self.sheet_id: Optional[str] = None
        self.connected: bool = False
        self.auth_error: str = ""
        self._connect()

    def _connect(self) -> None:
        credentials = None
        try:
            credentials, _ = default(scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
            if credentials and not credentials.valid:
                credentials.refresh(Request())
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Default Google auth failed: %s", exc)
            credentials = None

        if credentials is None:
            credential_path = Path(CONFIG.google_credentials)
            if credential_path.exists():
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        str(credential_path),
                        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
                    )
                    LOGGER.info("Loaded service account credentials from %s", credential_path)
                except Exception as exc:  # pragma: no cover
                    LOGGER.warning("Service account credentials failed: %s", exc)
                    credentials = None

        if credentials is None:
            self.auth_error = "Google Sheets authentication unavailable. Sync features are disabled."
            LOGGER.warning(self.auth_error)
            return

        try:
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self._open_or_create_spreadsheet(self.sheet_name)
            self.worksheet = self.spreadsheet.sheet1
            self.sheet_id = self.spreadsheet.id
            self.connected = True
            self.auth_error = ""
            LOGGER.info("Connected to Google Sheets: %s", self.sheet_name)
        except Exception as exc:  # pragma: no cover
            self.auth_error = str(exc)
            LOGGER.warning("Sheets connection failed: %s", exc)

    def _open_or_create_spreadsheet(self, title: str) -> Any:
        try:
            return self.client.open(title)
        except SpreadsheetNotFound:
            spreadsheet = self.client.create(title)
            spreadsheet.share(None, perm_type="anyone", role="reader")
            return spreadsheet

    def _sheet_url(self) -> str:
        if self.sheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self.sheet_id}"
        return ""

    def append_rows(self, rows: List[List[Any]], worksheet_name: str = "Sheet1") -> None:
        if self.spreadsheet is None:
            return
        worksheet = self._get_worksheet(worksheet_name)
        if worksheet is None:
            return
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    def update_rows(self, rows: List[List[Any]], worksheet_name: str = "Sheet1") -> None:
        if self.spreadsheet is None:
            return
        worksheet = self._get_worksheet(worksheet_name)
        if worksheet is None:
            return
        header = worksheet.row_values(1)
        if not header:
            return
        for index, row in enumerate(rows, start=2):
            worksheet.update(f"A{index}", [row], value_input_option="USER_ENTERED")

    def export_products(self, products: List[Dict[str, Any]], worksheet_name: str = "Products") -> str:
        if self.spreadsheet is None:
            LOGGER.warning("Google Sheets export skipped: no spreadsheet connection.")
            return ""
        worksheet = self._get_worksheet(worksheet_name)
        if worksheet is None:
            worksheet = self.spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=40)
        headers = [
            "ID",
            "Product Name",
            "SKU",
            "Barcode",
            "Category",
            "Sub Category",
            "Brand",
            "Supplier",
            "Purchase Price",
            "Selling Price",
            "MRP",
            "HSN Code",
            "GST",
            "Unit",
            "Batch Number",
            "Manufacturing Date",
            "Expiry Date",
            "Warranty",
            "Serial Number",
            "Current Stock",
            "Opening Stock",
            "Minimum Stock",
            "Maximum Stock",
            "Reorder Level",
            "Warehouse",
            "Location",
            "Rack",
            "Shelf",
            "Bin",
            "Zone",
            "Status",
            "Created At",
            "Updated At",
        ]
        rows = [
            [
                product.get("id", ""),
                product.get("product_name", ""),
                product.get("sku", ""),
                product.get("barcode", ""),
                product.get("category", ""),
                product.get("sub_category", ""),
                product.get("brand", ""),
                product.get("supplier", ""),
                product.get("purchase_price", ""),
                product.get("selling_price", ""),
                product.get("mrp", ""),
                product.get("hsn_code", ""),
                product.get("gst", ""),
                product.get("unit", ""),
                product.get("batch_number", ""),
                product.get("manufacturing_date", ""),
                product.get("expiry_date", ""),
                product.get("warranty", ""),
                product.get("serial_number", ""),
                product.get("current_stock", ""),
                product.get("opening_stock", ""),
                product.get("minimum_stock", ""),
                product.get("maximum_stock", ""),
                product.get("reorder_level", ""),
                product.get("warehouse", ""),
                product.get("location", ""),
                product.get("rack", ""),
                product.get("shelf", ""),
                product.get("bin", ""),
                product.get("zone", ""),
                product.get("status", ""),
                product.get("created_at", ""),
                product.get("updated_at", ""),
            ]
            for product in products
        ]
        worksheet.clear()
        worksheet.append_row(headers, value_input_option="USER_ENTERED")
        if rows:
            worksheet.append_rows(rows, value_input_option="USER_ENTERED")
        state = self.load_sheet_state()
        state["last_exported_products"] = utc_now() if hasattr(self, "utc_now") else ""
        state["sheet_url"] = self._sheet_url()
        self.save_sheet_state(state)
        return self._sheet_url()

    def _get_worksheet(self, title: str) -> Optional[Any]:
        if self.spreadsheet is None:
            return None
        try:
            return self.spreadsheet.worksheet(title)
        except Exception:
            try:
                return self.spreadsheet.add_worksheet(title=title, rows=1000, cols=40)
            except Exception as exc:
                LOGGER.warning("Unable to create worksheet: %s", exc)
        return None

    def search_products(self, query: str, worksheet_name: str = "Products") -> List[List[Any]]:
        if not self.spreadsheet:
            return []
        worksheet = self._get_worksheet(worksheet_name)
        if worksheet is None:
            return []
        values = worksheet.get_all_values()
        if not values:
            return []
        headers = values[0]
        results: List[List[Any]] = []
        for row in values[1:]:
            row_text = " ".join(str(value).lower() for value in row)
            if str(query).lower() in row_text:
                results.append(row)
        return results

    def create_backup(self, filename: str, rows: List[List[Any]], worksheet_name: str = "Backup") -> str:
        backup_path = Path(CONFIG.project_root) / "backups" / filename
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        with backup_path.open("w", encoding="utf-8") as handle:
            json.dump({"worksheet": worksheet_name, "rows": rows}, handle, indent=2)
        LOGGER.info("Created Google Sheets backup: %s", backup_path)
        return str(backup_path)

    def load_sheet_state(self) -> Dict[str, Any]:
        state = load_json(Path(SHEETS_FILE))
        return state or {}

    def save_sheet_state(self, payload: Dict[str, Any]) -> None:
        save_json(Path(SHEETS_FILE), payload)

    def status(self) -> str:
        if self.connected:
            return f"Connected to Google Sheets: {self.sheet_name}"
        return f"Disconnected: {self.auth_error or 'authentication failed'}"


def save_sheet_state(payload: Dict[str, Any]) -> None:
    ensure_json_file(Path(SHEETS_FILE), {})
    save_json(Path(SHEETS_FILE), payload)
