from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import numpy as np
from PIL import Image

from barcode import run_barcode_scan
from config import EXPORT_DIR, LOGGER
from excel_export import ExcelExporter
from forms import FormBuilderService, create_default_form
from google_sheets import GoogleSheetsService
from importer import ExcelImporter
from inventory import ActivityService, InventoryService, MovementService, create_count_session
from ocr import run_ocr
from products import ProductService
from reports import ReportService
from utils import build_scan_form_payload


class InventoryAppController:
    """Controller for the Gradio inventory application."""

    def __init__(self) -> None:
        self.products_service = ProductService()
        self.form_service = FormBuilderService()
        self.inventory_service = InventoryService()
        self.movement_service = MovementService()
        self.activity_service = ActivityService()
        self.excel_exporter = ExcelExporter()
        self.sheet_service = GoogleSheetsService()
        self.importer = ExcelImporter()
        self.report_service = ReportService()

    def ocr_scan(self, image: np.ndarray | Image.Image) -> Tuple[Dict[str, Any], str]:
        if image is None:
            return {}, ""
        try:
            result = run_ocr(image)
            self.activity_service.log_action("ocr_scan", f"OCR scan completed with engine={result.get('engine')}")
            LOGGER.info("OCR scan completed: engine=%s", result.get("engine"))
            return result, result.get("product_name", "")
        except Exception as exc:
            LOGGER.error("OCR scan failed: %s", exc)
            return {"error": str(exc)}, ""

    def barcode_scan(self, image: np.ndarray | Image.Image) -> List[List[Any]]:
        if image is None:
            return []
        try:
            data = run_barcode_scan(image)
            self.activity_service.log_action("barcode_scan", f"Barcode scan returned {len(data)} results")
            LOGGER.info("Barcode scan: %d results", len(data))
            return [[item["type"], item["data"]] for item in data]
        except Exception as exc:
            LOGGER.error("Barcode scan failed: %s", exc)
            return []

    def add_product(
        self,
        product_name: str,
        sku: str,
        barcode: str,
        category: str,
        brand: str,
        current_stock: float,
        purchase_price: float,
        selling_price: float,
        notes: str,
    ) -> str:
        try:
            payload = {
                "product_name": product_name,
                "sku": sku,
                "barcode": barcode,
                "category": category,
                "brand": brand,
                "current_stock": int(current_stock or 0),
                "purchase_price": float(purchase_price or 0),
                "selling_price": float(selling_price or 0),
                "product_notes": notes,
            }
            product = self.products_service.add(payload)
            try:
                self.sheet_service.export_products(self.products_service.list())
                self.excel_exporter.export_products(self.products_service.list())
            except Exception as sync_exc:
                LOGGER.warning("Post-add sync failed: %s", sync_exc)
            self.activity_service.log_action("add_product", f"Added product {product.get('product_name')}")
            LOGGER.info("Added product: %s (id=%s)", product.get("product_name"), product.get("id"))
            return f"✅ Added product: {product.get('product_name')} (ID: {product.get('id')})"
        except Exception as exc:
            LOGGER.error("Failed to add product: %s", exc)
            return f"❌ Error adding product: {exc}"

    def update_product(self, product_id: int, payload: Dict[str, Any]) -> str:
        try:
            product = self.products_service.update(product_id, payload)
            if product:
                try:
                    self.sheet_service.export_products(self.products_service.list())
                    self.excel_exporter.export_products(self.products_service.list())
                except Exception as sync_exc:
                    LOGGER.warning("Post-update sync failed: %s", sync_exc)
                self.activity_service.log_action("update_product", f"Updated product id={product_id}")
                return f"✅ Updated product: {product.get('product_name')}"
            return "❌ Product not found"
        except Exception as exc:
            LOGGER.error("Failed to update product %s: %s", product_id, exc)
            return f"❌ Error: {exc}"

    def delete_product(self, product_id: float) -> str:
        try:
            pid = int(product_id or 0)
            if pid == 0:
                return "❌ Please enter a valid Product ID"
            deleted = self.products_service.delete(pid)
            if deleted:
                try:
                    self.sheet_service.export_products(self.products_service.list())
                    self.excel_exporter.export_products(self.products_service.list())
                except Exception as sync_exc:
                    LOGGER.warning("Post-delete sync failed: %s", sync_exc)
                self.activity_service.log_action("delete_product", f"Deleted product id={product_id}")
                LOGGER.info("Deleted product id=%s", product_id)
                return f"✅ Deleted product ID {pid}"
            return f"❌ Product ID {pid} not found"
        except Exception as exc:
            LOGGER.error("Failed to delete product %s: %s", product_id, exc)
            return f"❌ Error: {exc}"

    def search_products(self, keyword: str) -> List[List[Any]]:
        try:
            products = self.products_service.search(keyword)
            LOGGER.info("Search '%s' → %d results", keyword, len(products))
            return [
                [
                    product.get("id"),
                    product.get("product_name"),
                    product.get("sku"),
                    product.get("barcode"),
                    product.get("category"),
                    product.get("brand"),
                    product.get("current_stock"),
                ]
                for product in products
            ]
        except Exception as exc:
            LOGGER.error("Search failed: %s", exc)
            return []

    def duplicate_check(self, barcode: str) -> str:
        try:
            if not barcode:
                return "⚠️ Enter a barcode to check"
            if self.products_service.duplicate_barcode(barcode):
                return f"⚠️ Duplicate barcode detected: {barcode}"
            return f"✅ No duplicate found for: {barcode}"
        except Exception as exc:
            LOGGER.error("Duplicate check failed: %s", exc)
            return f"❌ Error: {exc}"

    def build_scan_payload(
        self, ocr_result: Dict[str, Any], barcode_rows: List[List[Any]]
    ) -> Dict[str, Any]:
        return build_scan_form_payload(ocr_result, barcode_rows)

    def create_count(self, session_name: str) -> str:
        try:
            session = create_count_session({"name": session_name or "Count Session", "warehouse": "Main"})
            self.activity_service.log_action(
                "count_session_created", f"Created count session {session.get('id')}"
            )
            LOGGER.info("Created count session id=%s name=%s", session.get("id"), session_name)
            return f"✅ Created count session #{session.get('id')}: {session.get('name')}"
        except Exception as exc:
            LOGGER.error("Failed to create count session: %s", exc)
            return f"❌ Error: {exc}"

    def list_sessions(self) -> List[List[Any]]:
        try:
            sessions = self.inventory_service.list_sessions()
            return [
                [
                    session.get("id"),
                    session.get("name"),
                    session.get("status"),
                    session.get("warehouse"),
                    session.get("created_at"),
                ]
                for session in sessions
            ]
        except Exception as exc:
            LOGGER.error("Failed to list sessions: %s", exc)
            return []

    def add_count_item(
        self, session_id: float, product_id: float, counted_quantity: float, notes: str
    ) -> str:
        try:
            sid = int(session_id or 0)
            pid = int(product_id or 0)
            qty = int(counted_quantity or 0)
            if sid == 0:
                return "❌ Please enter a valid Session ID"
            if pid == 0:
                return "❌ Please enter a valid Product ID"
            product = self.products_service.get(pid)
            if not product:
                return f"❌ Product ID {pid} not found"
            item = {
                "product_id": pid,
                "product_name": product.get("product_name"),
                "sku": product.get("sku"),
                "barcode": product.get("barcode"),
                "expected_quantity": int(product.get("current_stock", 0) or 0),
                "counted_quantity": qty,
                "status": "completed",
                "notes": notes,
            }
            row = self.inventory_service.add_count_item(sid, item)
            if row:
                self.activity_service.log_action(
                    "add_count_item",
                    f"Added count item for session {sid} product {pid}",
                )
                return f"✅ Count item added — {product.get('product_name')} counted: {qty}"
            return f"❌ Session ID {sid} not found"
        except Exception as exc:
            LOGGER.error("Failed to add count item: %s", exc)
            return f"❌ Error: {exc}"

    def import_excel(self, file_obj: Any) -> str:
        try:
            if file_obj is None:
                return "❌ No file selected"
            file_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
            imported_rows = self.importer.import_products(file_path)
            for row in imported_rows:
                self.products_service.add(row)
            try:
                self.sheet_service.export_products(self.products_service.list())
                excel_path = self.excel_exporter.export_products(self.products_service.list())
            except Exception as sync_exc:
                LOGGER.warning("Post-import sync failed: %s", sync_exc)
                excel_path = None
            self.activity_service.log_action(
                "import_excel", f"Imported {len(imported_rows)} rows from {file_path}"
            )
            LOGGER.info("Imported %d rows from %s", len(imported_rows), file_path)
            msg = f"✅ Imported {len(imported_rows)} rows"
            if excel_path:
                msg += f". Excel exported: {excel_path}"
            return msg
        except Exception as exc:
            LOGGER.error("Import failed: %s", exc)
            return f"❌ Import error: {exc}"

    def sync_google_sheets(self) -> str:
        try:
            sheet_url = self.sheet_service.export_products(self.products_service.list())
            if sheet_url:
                self.activity_service.log_action(
                    "sync_google_sheets", f"Synchronized products to Google Sheets: {sheet_url}"
                )
                return f"✅ Synced to Google Sheets: {sheet_url}"
            return "⚠️ Google Sheets sync unavailable (credentials not configured)"
        except Exception as exc:
            LOGGER.error("Google Sheets sync failed: %s", exc)
            return f"❌ Sync error: {exc}"

    def sheet_status(self) -> str:
        try:
            return self.sheet_service.status()
        except Exception as exc:
            LOGGER.error("Sheet status check failed: %s", exc)
            return f"❌ Error checking sheet status: {exc}"

    def export_low_stock(self) -> str:
        try:
            path = self.report_service.export_low_stock_report()
            self.activity_service.log_action("export_low_stock", f"Low stock report exported: {path}")
            LOGGER.info("Low stock report exported: %s", path)
            return f"✅ Low stock report exported to:\n{path}"
        except Exception as exc:
            LOGGER.error("Low stock export failed: %s", exc)
            return f"❌ Export error: {exc}"

    def export_product_master(self) -> str:
        try:
            path = self.report_service.export_product_master()
            self.activity_service.log_action("export_product_master", f"Product master exported: {path}")
            LOGGER.info("Product master exported: %s", path)
            return f"✅ Product master exported to:\n{path}"
        except Exception as exc:
            LOGGER.error("Product master export failed: %s", exc)
            return f"❌ Export error: {exc}"

    def export_count_report(self) -> str:
        try:
            path = self.report_service.export_count_report()
            self.activity_service.log_action("export_count_report", f"Count report exported: {path}")
            LOGGER.info("Count report exported: %s", path)
            return f"✅ Count report exported to:\n{path}"
        except Exception as exc:
            LOGGER.error("Count report export failed: %s", exc)
            return f"❌ Export error: {exc}"

    def export_inventory_valuation(self) -> str:
        try:
            path = self.report_service.export_inventory_valuation()
            self.activity_service.log_action("export_inventory_valuation", f"Valuation exported: {path}")
            LOGGER.info("Inventory valuation exported: %s", path)
            return f"✅ Inventory valuation exported to:\n{path}"
        except Exception as exc:
            LOGGER.error("Inventory valuation export failed: %s", exc)
            return f"❌ Export error: {exc}"

    def create_form(self, form_name: str) -> str:
        try:
            if not form_name:
                return "❌ Please enter a form name"
            form = self.form_service.create({"name": form_name, "fields": create_default_form()["fields"]})
            self.activity_service.log_action("create_form", f"Created form {form.get('name')}")
            LOGGER.info("Created form: %s", form.get("name"))
            return f"✅ Created form: {form.get('name')} (ID: {form.get('id')})"
        except Exception as exc:
            LOGGER.error("Failed to create form: %s", exc)
            return f"❌ Error: {exc}"

    def list_forms(self) -> List[List[Any]]:
        try:
            forms = self.form_service.list()
            return [[form.get("id"), form.get("name"), form.get("created_at") or ""] for form in forms]
        except Exception as exc:
            LOGGER.error("Failed to list forms: %s", exc)
            return []

    def delete_form(self, form_id: float) -> str:
        try:
            fid = int(form_id or 0)
            if fid == 0:
                return "❌ Please enter a valid Form ID"
            deleted = self.form_service.delete(fid)
            if deleted:
                self.activity_service.log_action("delete_form", f"Deleted form id={fid}")
                LOGGER.info("Deleted form id=%s", fid)
                return f"✅ Deleted form ID {fid}"
            return f"❌ Form ID {fid} not found"
        except Exception as exc:
            LOGGER.error("Failed to delete form %s: %s", form_id, exc)
            return f"❌ Error: {exc}"

    def load_dashboard(self) -> Tuple[Dict[str, Any], List[List[Any]], List[List[Any]]]:
        try:
            metrics = self.report_service.dashboard_metrics()
            products = self.products_service.recent_products()
            recent_activity = self.activity_service.list_activity(limit=10)
            product_rows = [
                [
                    product.get("id"),
                    product.get("product_name"),
                    product.get("current_stock"),
                    product.get("category"),
                    product.get("brand"),
                ]
                for product in products
            ]
            activity_rows = [
                [item.get("timestamp"), item.get("action"), item.get("details")]
                for item in recent_activity
            ]
            return metrics, product_rows, activity_rows
        except Exception as exc:
            LOGGER.error("Dashboard load failed: %s", exc)
            return {}, [], []

    def reset_all_data(self) -> Tuple[Dict[str, Any], List[List[Any]], List[List[Any]], str]:
        try:
            from config import (  # noqa: PLC0415
                ACTIVITY_JSON,
                COUNTS_JSON,
                FORMS_JSON,
                MOVEMENTS_JSON,
                PRODUCTS_JSON,
                save_json,
            )

            save_json(PRODUCTS_JSON, {"products": []})
            save_json(COUNTS_JSON, {"counts": []})
            save_json(MOVEMENTS_JSON, {"movements": []})
            save_json(ACTIVITY_JSON, {"activity": []})
            save_json(FORMS_JSON, {"forms": []})
            try:
                self.sheet_service.export_products([])
                self.excel_exporter.export_products([])
            except Exception:
                pass
            self.activity_service.log_action(
                "reset_all_data", "System Reset: Cleared all products, counts, and movements."
            )
            LOGGER.warning("All inventory data has been reset!")
            metrics, prods, acts = self.load_dashboard()
            return metrics, prods, acts, "✅ SUCCESS: All inventory data has been reset to zero!"
        except Exception as exc:
            LOGGER.error("Reset failed: %s", exc)
            return {}, [], [], f"❌ Reset error: {exc}"

    def get_sample_import_file(self) -> str:
        try:
            path = EXPORT_DIR / "sample_import.xlsx"
            if not path.exists():
                import pandas as pd  # noqa: PLC0415

                df = pd.DataFrame(
                    [
                        {
                            "product_name": "Sample Product A",
                            "sku": "SKU-SAMPLE-01",
                            "barcode": "8901234567890",
                            "category": "Electronics",
                            "brand": "SampleBrand",
                            "current_stock": 50,
                            "minimum_stock": 5,
                            "purchase_price": 100.0,
                            "selling_price": 150.0,
                            "unit": "pcs",
                            "warehouse": "Main",
                        }
                    ]
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                df.to_excel(str(path), index=False)
            LOGGER.info("Sample import file ready: %s", path)
            return str(path)
        except Exception as exc:
            LOGGER.error("Failed to generate sample import file: %s", exc)
            return ""


def _api_port() -> int:
    """Return the current mobile API port."""
    return int(os.getenv("MOBILE_API_PORT", "8765"))


def build_ui() -> gr.Blocks:
    controller = InventoryAppController()

    with gr.Blocks(title="InventoryFlow System") as demo:
        gr.Markdown("# 📦 AI Inventory & Stock Count System")
        gr.Markdown(
            "Enterprise inventory management powered by OCR, barcode scanning, "
            "FastAPI REST services, and Google Sheets sync."
        )

        with gr.Accordion("📱 Mobile UI & API Quick Access Portals", open=True):
            # Use a JS-rendered block so the port is dynamically injected at page load
            portal_html = gr.HTML(
                f"""
                <div id="portal-links" style="display: flex; gap: 12px; flex-wrap: wrap; margin: 10px 0 14px 0;">
                    <a href="http://localhost:{_api_port()}" target="_blank" style="text-decoration: none;">
                        <button style="background: linear-gradient(135deg, #91000a 0%, #b71c1c 100%); color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-flex; align-items: center; gap: 8px; transition: transform 0.15s ease;" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">
                            📱 Mobile UI Interface ({_api_port()})
                        </button>
                    </a>
                    <a href="http://localhost:{_api_port()}/docs" target="_blank" style="text-decoration: none;">
                        <button style="background: linear-gradient(135deg, #374151 0%, #4b5563 100%); color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-flex; align-items: center; gap: 8px; transition: transform 0.15s ease;" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">
                            📄 API Docs (/docs)
                        </button>
                    </a>
                    <a href="http://localhost:{_api_port()}/redoc" target="_blank" style="text-decoration: none;">
                        <button style="background: linear-gradient(135deg, #4b5563 0%, #6b7280 100%); color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-flex; align-items: center; gap: 8px; transition: transform 0.15s ease;" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">
                            📋 ReDoc (/redoc)
                        </button>
                    </a>
                    <a href="http://localhost:{_api_port()}/api/stats" target="_blank" style="text-decoration: none;">
                        <button style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-flex; align-items: center; gap: 8px; transition: transform 0.15s ease;" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">
                            📊 API Stats (/api/stats)
                        </button>
                    </a>
                    <a href="http://localhost:{_api_port()}/api/products" target="_blank" style="text-decoration: none;">
                        <button style="background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%); color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-flex; align-items: center; gap: 8px; transition: transform 0.15s ease;" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">
                            📦 API Products (/api/products)
                        </button>
                    </a>
                    <a href="http://localhost:{_api_port()}/api/export" target="_blank" style="text-decoration: none;">
                        <button style="background: linear-gradient(135deg, #15803d 0%, #166534 100%); color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-flex; align-items: center; gap: 8px; transition: transform 0.15s ease;" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">
                            ⬇️ API Export (/api/export)
                        </button>
                    </a>
                </div>
                """
            )

        with gr.Tabs():
            # ── Dashboard Tab ─────────────────────────────────────────────────
            with gr.TabItem("🏠 Dashboard"):
                metrics_out = gr.JSON(label="Dashboard Metrics")
                with gr.Row():
                    recent_products_tbl = gr.Dataframe(
                        headers=["ID", "Product", "Stock", "Category", "Brand"],
                        label="Recent Products",
                    )
                    recent_activity_tbl = gr.Dataframe(
                        headers=["Timestamp", "Action", "Details"],
                        label="Recent Activity",
                    )
                demo.load(controller.load_dashboard, outputs=[metrics_out, recent_products_tbl, recent_activity_tbl])
                with gr.Row():
                    export_low_btn = gr.Button("📉 Export Low Stock Report", variant="secondary")
                    export_master_btn = gr.Button("📋 Export Product Master", variant="secondary")
                    export_val_btn = gr.Button("💰 Export Valuation", variant="secondary")
                    reset_btn = gr.Button("⚠️ Reset All Data", variant="stop")

                export_low_status = gr.Textbox(label="Export Status", lines=2, interactive=False)
                reset_status = gr.Textbox(label="Reset Status", lines=1, interactive=False)

                export_low_btn.click(controller.export_low_stock, outputs=[export_low_status])
                export_master_btn.click(controller.export_product_master, outputs=[export_low_status])
                export_val_btn.click(controller.export_inventory_valuation, outputs=[export_low_status])
                reset_btn.click(
                    controller.reset_all_data,
                    outputs=[metrics_out, recent_products_tbl, recent_activity_tbl, reset_status],
                )

            # ── Product Master Tab ────────────────────────────────────────────
            with gr.TabItem("📦 Product Master"):
                with gr.Row():
                    product_name = gr.Textbox(label="Product Name", placeholder="e.g. Industrial Drill Bit")
                    sku = gr.Textbox(label="SKU", placeholder="SKU-1001")
                    barcode = gr.Textbox(label="Barcode", placeholder="12345678")
                    category = gr.Textbox(label="Category", placeholder="Tools")
                with gr.Row():
                    brand = gr.Textbox(label="Brand", placeholder="Bosch")
                    current_stock = gr.Number(label="Current Stock", value=0, minimum=0)
                    purchase_price = gr.Number(label="Purchase Price (₹)", value=0.0, minimum=0)
                    selling_price = gr.Number(label="Selling Price (₹)", value=0.0, minimum=0)
                with gr.Row():
                    notes = gr.Textbox(label="Notes", placeholder="Optional notes")
                with gr.Row():
                    save_product_button = gr.Button("💾 Add Product", variant="primary")
                    clear_btn = gr.Button("🗑️ Clear Form", variant="secondary")
                status_text = gr.Textbox(label="Status", lines=2, interactive=False)

                save_product_button.click(
                    controller.add_product,
                    inputs=[product_name, sku, barcode, category, brand, current_stock, purchase_price, selling_price, notes],
                    outputs=[status_text],
                )
                clear_btn.click(
                    lambda: ["", "", "", "", "", 0, 0.0, 0.0, "", ""],
                    outputs=[product_name, sku, barcode, category, brand, current_stock, purchase_price, selling_price, notes, status_text],
                )

            # ── Scanner Tab ───────────────────────────────────────────────────
            with gr.TabItem("📷 Scanner"):
                with gr.Row():
                    image_input = gr.Image(
                        label="Camera / Upload",
                        sources=["webcam", "upload"],
                        type="numpy",
                    )
                with gr.Row():
                    ocr_output = gr.JSON(label="OCR Result")
                    barcode_output = gr.Dataframe(
                        headers=["Type", "Value"],
                        label="Barcode Results",
                    )
                with gr.Row():
                    detected_product = gr.Textbox(label="Detected Product Name")
                with gr.Row():
                    scan_btn = gr.Button("🔍 Scan Image (OCR + Barcode)", variant="primary")
                    populate_btn = gr.Button("📋 Populate Product Form", variant="secondary")
                scan_status = gr.Textbox(label="Scan Status", lines=1, interactive=False)

                def do_full_scan(img):
                    ocr_res, prod_name = controller.ocr_scan(img)
                    bc_rows = controller.barcode_scan(img)
                    status = f"OCR: engine={ocr_res.get('engine', 'n/a')} | Barcodes found: {len(bc_rows)}"
                    return ocr_res, bc_rows, prod_name, status

                scan_btn.click(
                    do_full_scan,
                    inputs=[image_input],
                    outputs=[ocr_output, barcode_output, detected_product, scan_status],
                )

                def do_populate(ocr_result, barcode_rows):
                    payload = build_scan_form_payload(ocr_result or {}, barcode_rows or [])
                    return (
                        payload.get("product_name", ""),
                        payload.get("sku", ""),
                        payload.get("barcode", ""),
                        payload.get("brand", ""),
                        payload.get("category", ""),
                    )

                populate_btn.click(
                    do_populate,
                    inputs=[ocr_output, barcode_output],
                    outputs=[product_name, sku, barcode, brand, category],
                )

            # ── Search Tab ────────────────────────────────────────────────────
            with gr.TabItem("🔍 Search"):
                with gr.Row():
                    search_box = gr.Textbox(label="Search keyword", placeholder="Product name, SKU, barcode…")
                    search_button = gr.Button("🔍 Search", variant="primary")
                search_results = gr.Dataframe(
                    headers=["ID", "Product", "SKU", "Barcode", "Category", "Brand", "Stock"],
                    label="Search Results",
                )
                search_button.click(controller.search_products, inputs=[search_box], outputs=[search_results])
                search_box.submit(controller.search_products, inputs=[search_box], outputs=[search_results])

                gr.Markdown("---")
                with gr.Row():
                    delete_id = gr.Number(label="Product ID to Delete", minimum=1)
                    delete_button = gr.Button("🗑️ Delete Product", variant="stop")
                delete_status = gr.Textbox(label="Delete Status", lines=2, interactive=False)
                delete_button.click(controller.delete_product, inputs=[delete_id], outputs=[delete_status])

                gr.Markdown("---")
                with gr.Row():
                    barcode_check = gr.Textbox(label="Barcode for Duplicate Check", placeholder="Enter barcode")
                    duplicate_button = gr.Button("🔎 Check Duplicate", variant="secondary")
                duplicate_status = gr.Textbox(label="Duplicate Status", lines=1, interactive=False)
                duplicate_button.click(controller.duplicate_check, inputs=[barcode_check], outputs=[duplicate_status])

            # ── Counting Tab ──────────────────────────────────────────────────
            with gr.TabItem("📊 Counting"):
                with gr.Row():
                    session_name_inp = gr.Textbox(label="Count Session Name", placeholder="e.g. Monthly Count July 2026")
                    create_session_button = gr.Button("➕ Create Session", variant="primary")
                session_status_out = gr.Textbox(label="Session Status", lines=2, interactive=False)
                create_session_button.click(
                    controller.create_count,
                    inputs=[session_name_inp],
                    outputs=[session_status_out],
                )

                with gr.Row():
                    session_table = gr.Dataframe(
                        headers=["ID", "Name", "Status", "Warehouse", "Created At"],
                        label="Count Sessions",
                    )
                    refresh_sessions_btn = gr.Button("🔄 Refresh Sessions", variant="secondary")
                refresh_sessions_btn.click(controller.list_sessions, outputs=[session_table])
                demo.load(controller.list_sessions, outputs=[session_table])

                gr.Markdown("---")
                gr.Markdown("### Add Count Item to Session")
                with gr.Row():
                    count_session_id = gr.Number(label="Session ID", minimum=1)
                    count_product_id = gr.Number(label="Product ID", minimum=1)
                    count_quantity = gr.Number(label="Counted Quantity", minimum=0)
                    count_notes_inp = gr.Textbox(label="Notes", placeholder="Optional notes")
                with gr.Row():
                    add_count_button = gr.Button("➕ Add Count Item", variant="primary")
                count_status_out = gr.Textbox(label="Count Item Status", lines=2, interactive=False)
                add_count_button.click(
                    controller.add_count_item,
                    inputs=[count_session_id, count_product_id, count_quantity, count_notes_inp],
                    outputs=[count_status_out],
                )

            # ── Forms Tab ─────────────────────────────────────────────────────
            with gr.TabItem("📝 Forms"):
                with gr.Row():
                    form_name_inp = gr.Textbox(label="Form Name", placeholder="e.g. Monthly Inventory Form")
                    create_form_button = gr.Button("➕ Create Form", variant="primary")
                form_status_out = gr.Textbox(label="Form Status", lines=2, interactive=False)
                create_form_button.click(
                    controller.create_form, inputs=[form_name_inp], outputs=[form_status_out]
                )

                with gr.Row():
                    form_list = gr.Dataframe(
                        headers=["ID", "Name", "Created At"],
                        label="Forms",
                    )
                    refresh_forms_btn = gr.Button("🔄 Refresh Forms", variant="secondary")
                refresh_forms_btn.click(controller.list_forms, outputs=[form_list])
                demo.load(controller.list_forms, outputs=[form_list])

                gr.Markdown("---")
                with gr.Row():
                    delete_form_id = gr.Number(label="Form ID to Delete", minimum=1)
                    delete_form_button = gr.Button("🗑️ Delete Form", variant="stop")
                delete_form_status_out = gr.Textbox(label="Form Delete Status", lines=1, interactive=False)
                delete_form_button.click(
                    controller.delete_form, inputs=[delete_form_id], outputs=[delete_form_status_out]
                )

            # ── Import & Export Tab ───────────────────────────────────────────
            with gr.TabItem("📥 Import & Export"):
                gr.Markdown("### 📥 Download Sample Import Template")
                with gr.Row():
                    download_sample_btn = gr.Button(
                        "📥 Download Sample Import Template (sample_import.xlsx)",
                        variant="primary",
                    )
                sample_file_out = gr.File(label="Sample Import File (Click to download)")
                download_sample_btn.click(controller.get_sample_import_file, outputs=[sample_file_out])

                gr.Markdown("---")
                gr.Markdown("### 📤 Import Products from Excel")
                import_file = gr.File(
                    label="Import Excel File",
                    file_types=[".xlsx", ".xls", ".csv"],
                )
                with gr.Row():
                    import_button = gr.Button("📤 Import Excel", variant="primary")
                import_status = gr.Textbox(label="Import Status", lines=3, interactive=False)
                import_button.click(controller.import_excel, inputs=[import_file], outputs=[import_status])

                gr.Markdown("---")
                gr.Markdown("### 🔄 Google Sheets Sync")
                with gr.Row():
                    sync_button = gr.Button("🔄 Sync to Google Sheets", variant="secondary")
                sync_status = gr.Textbox(label="Sync Status", lines=2, interactive=False)
                sync_button.click(controller.sync_google_sheets, outputs=[sync_status])

                gr.Markdown("---")
                gr.Markdown("### 📊 Export Reports")
                with gr.Row():
                    export_products_btn = gr.Button("📊 Export Products (Excel)", variant="secondary")
                    export_count_btn = gr.Button("📋 Export Count Report", variant="secondary")
                export_report_status = gr.Textbox(label="Export Status", lines=2, interactive=False)
                export_products_btn.click(controller.export_product_master, outputs=[export_report_status])
                export_count_btn.click(controller.export_count_report, outputs=[export_report_status])

                gr.Markdown(
                    "Upload a spreadsheet with columns: product_name, sku, barcode, category, "
                    "brand, current_stock, minimum_stock, purchase_price, selling_price, unit, warehouse."
                )

            # ── Reports Tab ───────────────────────────────────────────────────
            with gr.TabItem("📈 Reports"):
                gr.Markdown("## Reports & Analytics")
                with gr.Row():
                    rpt_low_btn = gr.Button("📉 Low Stock Report", variant="secondary")
                    rpt_master_btn = gr.Button("📦 Product Master", variant="secondary")
                    rpt_count_btn = gr.Button("📋 Count Report", variant="secondary")
                    rpt_val_btn = gr.Button("💰 Valuation Report", variant="secondary")
                reports_status = gr.Textbox(label="Report Status", lines=3, interactive=False)

                rpt_low_btn.click(controller.export_low_stock, outputs=[reports_status])
                rpt_master_btn.click(controller.export_product_master, outputs=[reports_status])
                rpt_count_btn.click(controller.export_count_report, outputs=[reports_status])
                rpt_val_btn.click(controller.export_inventory_valuation, outputs=[reports_status])

            # ── Settings Tab ─────────────────────────────────────────────────
            with gr.TabItem("⚙️ Settings"):
                gr.Markdown("## Settings and Diagnostics")
                gr.Markdown(
                    "Use Google Colab authentication to mount Drive and sync spreadsheets. "
                    "Export files are saved in the `exports/` folder."
                )
                with gr.Row():
                    sheet_status_box = gr.Textbox(
                        label="Google Sheets Status",
                        lines=3,
                        interactive=False,
                        value="Click 'Refresh' to check status",
                    )
                    refresh_status_btn = gr.Button("🔄 Refresh Sheet Status", variant="secondary")
                refresh_status_btn.click(controller.sheet_status, outputs=[sheet_status_box])
                demo.load(controller.sheet_status, outputs=[sheet_status_box])

                gr.Markdown("---")
                gr.Markdown("### 🔌 API Connection Info")
                api_info_html = gr.HTML(
                    f"""
                    <div style="font-family: monospace; background: #1e1e1e; color: #d4d4d4;
                                padding: 16px; border-radius: 8px; font-size: 13px; line-height: 1.8;">
                        <strong style="color: #4ec9b0;">Mobile API Server</strong><br>
                        ● <a href="http://localhost:{_api_port()}" target="_blank" style="color:#9cdcfe;">
                            http://localhost:{_api_port()}/</a><br>
                        ● <a href="http://127.0.0.1:{_api_port()}" target="_blank" style="color:#9cdcfe;">
                            http://127.0.0.1:{_api_port()}/</a><br>
                        ● <a href="http://localhost:{_api_port()}/docs" target="_blank" style="color:#ce9178;">
                            http://localhost:{_api_port()}/docs</a> — Swagger UI<br>
                        ● <a href="http://localhost:{_api_port()}/redoc" target="_blank" style="color:#ce9178;">
                            http://localhost:{_api_port()}/redoc</a> — ReDoc<br>
                        ● <a href="http://localhost:{_api_port()}/api/stats" target="_blank" style="color:#b5cea8;">
                            http://localhost:{_api_port()}/api/stats</a> — Stats JSON<br>
                        ● <a href="http://localhost:{_api_port()}/api/products" target="_blank" style="color:#b5cea8;">
                            http://localhost:{_api_port()}/api/products</a> — Products JSON<br>
                        ● <a href="http://localhost:{_api_port()}/api/export" target="_blank" style="color:#b5cea8;">
                            http://localhost:{_api_port()}/api/export</a> — Export JSON<br>
                    </div>
                    """
                )

                gr.Markdown("---")
                diagnostics = gr.Textbox(
                    label="Diagnostics Log",
                    lines=10,
                    interactive=False,
                    value="Ready. Click 'Refresh Sheet Status' above to run diagnostics.",
                )

    return demo
