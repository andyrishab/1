"""
mobile_api.py — Lightweight REST API for the InventoryFlow Mobile UI
Runs on port 8765 alongside the Gradio app (port 7860+).

Endpoints:
  GET  /                         → Serve mobile_ui.html
  GET  /api                      → API info / health check
  GET  /api/stats                → Dashboard statistics
  GET  /api/products             → List / search products
  POST /api/products             → Create a product
  GET  /api/products/{id}        → Get single product
  PUT  /api/products/{id}        → Update product
  DELETE /api/products/{id}      → Delete product
  GET  /api/products/lookup      → Find by SKU or barcode
  GET  /api/search               → Search products (alias)
  GET  /api/categories           → Unique category list with counts
  GET  /api/counts               → List count sessions
  POST /api/counts               → Create new count session
  GET  /api/counts/{id}          → Get single session
  POST /api/counts/{id}/items    → Add counted item to session
  PUT  /api/counts/{id}/items/{iid} → Update counted item qty
  POST /api/counts/{id}/finish   → Complete session + update stock
  GET  /api/movements            → Recent stock movements
  GET  /api/activity             → Activity log
  GET  /api/settings             → App settings
  PUT  /api/settings             → Save app settings
  GET  /api/export               → Export products as JSON
  POST /api/import               → Import products from JSON body
  POST /api/reset                → Reset all data
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Resolve project root so imports work when run from any directory ─────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (
    ACTIVITY_JSON,
    COUNTS_JSON,
    EXPORT_DIR,
    FORMS_JSON,
    LOGGER,
    MOVEMENTS_JSON,
    PRODUCTS_JSON,
    SETTINGS_JSON,
    load_json,
    save_json,
)
from inventory import ActivityService, InventoryService, MovementService
from products import ProductService
from utils import safe_int, safe_text, utc_now

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="InventoryFlow Mobile API",
    version="1.0.0",
    description="REST API for InventoryFlow mobile and web clients",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

MOBILE_HTML = ROOT / "mobile_ui.html"


# ── Pydantic models ───────────────────────────────────────────────────────────
class ProductBody(BaseModel):
    product_name: str = ""
    sku: str = ""
    barcode: str = ""
    category: str = ""
    sub_category: str = ""
    brand: str = ""
    supplier: str = ""
    purchase_price: float = 0.0
    selling_price: float = 0.0
    mrp: float = 0.0
    unit: str = "pcs"
    warehouse: str = "Main"
    location: str = ""
    rack: str = ""
    current_stock: int = 0
    minimum_stock: int = 0
    maximum_stock: int = 0
    reorder_level: int = 0
    status: str = "active"
    product_description: str = ""


class CountSessionBody(BaseModel):
    name: str = ""
    doc_num: str = ""
    inspector: str = ""
    count_date: str = ""
    warehouse: str = "Main"
    location: str = ""
    category: str = ""
    type: str = "full_count"
    notes: str = ""


class CountItemBody(BaseModel):
    product_id: int = 0
    product_name: str = ""
    sku: str = ""
    barcode: str = ""
    expected_quantity: int = 0
    counted_quantity: int = 0
    notes: str = ""


class CountItemUpdate(BaseModel):
    counted_quantity: int
    status: str = "pending"
    notes: str = ""


class StockAdjustBody(BaseModel):
    quantity: int                # positive = add, negative = subtract
    reason: str = "manual_adjustment"
    mode: str = "adjust"         # "adjust" (delta) or "set" (absolute)


class SettingsBody(BaseModel):
    theme: str = "light"
    dark_mode: bool = False
    notifications: bool = True
    default_currency: str = "INR"
    company_name: str = "My Company"
    default_warehouse: str = "Main"
    qty_decimal: int = 0
    price_decimal: int = 2
    show_selling_price: bool = True
    use_purchase_price: bool = False


class ImportBody(BaseModel):
    products: List[Dict[str, Any]] = []


# ── Helpers ───────────────────────────────────────────────────────────────────
ps = ProductService()
inv = InventoryService()
mov = MovementService()
act = ActivityService()


def stock_status(product: Dict[str, Any]) -> str:
    stock = safe_int(product.get("current_stock"), 0)
    minimum = safe_int(product.get("minimum_stock"), 5)
    if stock <= 0:
        return "out"
    if minimum > 0 and stock <= minimum:
        return "low"
    return "in"


# ── Routes: UI ────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def serve_ui():
    """Serve the mobile UI HTML file."""
    if MOBILE_HTML.exists():
        return FileResponse(str(MOBILE_HTML), media_type="text/html")
    raise HTTPException(404, "mobile_ui.html not found")


# ── Routes: API Info ──────────────────────────────────────────────────────────
@app.get("/api")
async def api_info():
    """API health check and info endpoint."""
    return {
        "name": "InventoryFlow Mobile API",
        "version": "1.0.0",
        "status": "ok",
        "endpoints": [
            "/api/stats",
            "/api/products",
            "/api/categories",
            "/api/counts",
            "/api/movements",
            "/api/activity",
            "/api/settings",
            "/api/search",
            "/api/export",
            "/api/import",
            "/docs",
            "/redoc",
        ],
    }


# ── Routes: Stats ─────────────────────────────────────────────────────────────
@app.get("/api/stats")
async def get_stats():
    """Return dashboard statistics."""
    try:
        products = ps.load()
        total = len(products)
        total_value = sum(
            safe_int(p.get("current_stock"), 0) * float(p.get("selling_price", 0) or 0)
            for p in products
        )
        low_stock = sum(1 for p in products if stock_status(p) == "low")
        out_of_stock = sum(1 for p in products if stock_status(p) == "out")
        categories = len({safe_text(p.get("category")) for p in products if p.get("category")})
        active_sessions = len(inv.list_sessions(status="active"))
        LOGGER.info("API /api/stats → total=%d low=%d out=%d", total, low_stock, out_of_stock)
        return {
            "total_products": total,
            "total_value": round(total_value, 2),
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "categories": categories,
            "active_sessions": active_sessions,
        }
    except Exception as exc:
        LOGGER.error("Error in /api/stats: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Products ──────────────────────────────────────────────────────────
@app.get("/api/products")
async def list_products(
    q: str = Query("", alias="q"),
    category: str = Query("", alias="category"),
    status: str = Query("", alias="status"),
    limit: int = Query(200, alias="limit"),
    offset: int = Query(0, alias="offset"),
):
    """List or search products with optional filters."""
    try:
        filters: Dict[str, Any] = {}
        if category:
            filters["category"] = category
        results = ps.search(keyword=q, filters=filters or None)
        # Apply stock status filter
        if status in ("in", "low", "out"):
            results = [p for p in results if stock_status(p) == status]
        # Enrich with computed status
        for p in results:
            p["_status"] = stock_status(p)
        total = len(results)
        LOGGER.info("API /api/products q=%r status=%r → %d results", q, status, total)
        return {"total": total, "products": results[offset: offset + limit]}
    except Exception as exc:
        LOGGER.error("Error in /api/products: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.post("/api/products", status_code=201)
async def create_product(body: ProductBody):
    """Create a new product."""
    try:
        product = ps.add(body.model_dump())
        act.log_action(
            "product_created_mobile",
            f"Product '{product.get('product_name')}' added via mobile API",
        )
        LOGGER.info("API POST /api/products → created id=%s", product.get("id"))
        return product
    except Exception as exc:
        LOGGER.error("Error creating product: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.get("/api/products/lookup")
async def lookup_product(
    sku: str = Query(""),
    barcode: str = Query(""),
):
    """Find product by SKU or barcode (used during counting)."""
    try:
        if sku:
            product = ps.find_by_sku(sku)
            if product:
                product["_status"] = stock_status(product)
                LOGGER.info("API /api/products/lookup sku=%r → found id=%s", sku, product.get("id"))
                return product
        if barcode:
            product = ps.find_by_barcode(barcode)
            if product:
                product["_status"] = stock_status(product)
                LOGGER.info("API /api/products/lookup barcode=%r → found id=%s", barcode, product.get("id"))
                return product
        LOGGER.info("API /api/products/lookup sku=%r barcode=%r → not found", sku, barcode)
        raise HTTPException(404, "Product not found")
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error in product lookup: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.get("/api/products/{product_id}")
async def get_product(product_id: int):
    """Get a single product by ID."""
    try:
        product = ps.get(product_id)
        if not product:
            raise HTTPException(404, "Product not found")
        product["_status"] = stock_status(product)
        return product
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error getting product %s: %s", product_id, exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.put("/api/products/{product_id}")
async def update_product(product_id: int, body: ProductBody):
    """Update an existing product."""
    try:
        updated = ps.update(product_id, body.model_dump())
        if not updated:
            raise HTTPException(404, "Product not found")
        act.log_action(
            "product_updated_mobile",
            f"Product id={product_id} updated via mobile API",
        )
        LOGGER.info("API PUT /api/products/%s → updated", product_id)
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error updating product %s: %s", product_id, exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int):
    """Delete a product by ID."""
    try:
        ok = ps.delete(product_id)
        if not ok:
            raise HTTPException(404, "Product not found")
        act.log_action(
            "product_deleted_mobile",
            f"Product id={product_id} deleted via mobile API",
        )
        LOGGER.info("API DELETE /api/products/%s → deleted", product_id)
        return {"deleted": True, "product_id": product_id}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error deleting product %s: %s", product_id, exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.patch("/api/products/{product_id}/stock")
async def adjust_product_stock(product_id: int, body: StockAdjustBody):
    """Quickly adjust or set a product's stock without touching other fields."""
    try:
        if body.mode == "set":
            updated = ps.update_stock(product_id, body.quantity)
        else:
            updated = ps.adjust_stock(product_id, body.quantity, reason=body.reason)
        if not updated:
            raise HTTPException(404, "Product not found")
        act.log_action(
            "stock_adjusted_mobile",
            f"Product id={product_id} stock {body.mode}={body.quantity} ({body.reason})",
        )
        mov.record_movement({
            "product_id": product_id,
            "product_name": updated.get("product_name", ""),
            "type": "manual_adjustment",
            "quantity": body.quantity,
            "reason": body.reason,
            "warehouse_from": updated.get("warehouse", "Main"),
            "warehouse_to": updated.get("warehouse", "Main"),
        })
        LOGGER.info("API PATCH /api/products/%s/stock mode=%s qty=%s", product_id, body.mode, body.quantity)
        return {"product_id": product_id, "new_stock": updated.get("current_stock"), "mode": body.mode}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error adjusting stock for product %s: %s", product_id, exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Search ────────────────────────────────────────────────────────────
@app.get("/api/search")
async def search_products(
    q: str = Query("", alias="q"),
    category: str = Query("", alias="category"),
    status: str = Query("", alias="status"),
    limit: int = Query(100, alias="limit"),
):
    """Search products by keyword, category, or stock status."""
    try:
        filters: Dict[str, Any] = {}
        if category:
            filters["category"] = category
        results = ps.search(keyword=q, filters=filters or None)
        if status in ("in", "low", "out"):
            results = [p for p in results if stock_status(p) == status]
        for p in results:
            p["_status"] = stock_status(p)
        LOGGER.info("API /api/search q=%r → %d results", q, len(results))
        return {"total": len(results), "products": results[:limit]}
    except Exception as exc:
        LOGGER.error("Error in /api/search: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Export ────────────────────────────────────────────────────────────
@app.get("/api/export")
async def export_products(fmt: str = Query("json", alias="fmt")):
    """Export all products as JSON."""
    try:
        products = ps.load()
        for p in products:
            p["_status"] = stock_status(p)
        act.log_action("export_products_mobile", f"Exported {len(products)} products via REST API")
        LOGGER.info("API /api/export → %d products", len(products))
        return {
            "exported_at": utc_now(),
            "total": len(products),
            "products": products,
        }
    except Exception as exc:
        LOGGER.error("Error in /api/export: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Import ────────────────────────────────────────────────────────────
@app.post("/api/import", status_code=201)
async def import_products(body: ImportBody):
    """Import products from a JSON payload."""
    try:
        imported = []
        errors = []
        for item in body.products:
            try:
                product = ps.add(item)
                imported.append(product)
            except Exception as e:
                errors.append({"item": item, "error": str(e)})
        act.log_action(
            "import_products_mobile",
            f"Imported {len(imported)} products via REST API ({len(errors)} errors)",
        )
        LOGGER.info("API POST /api/import → imported=%d errors=%d", len(imported), len(errors))
        return {
            "imported": len(imported),
            "errors": len(errors),
            "error_details": errors,
            "products": imported,
        }
    except Exception as exc:
        LOGGER.error("Error in /api/import: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Categories ────────────────────────────────────────────────────────
@app.get("/api/categories")
async def list_categories():
    """List all unique categories with product counts."""
    try:
        products = ps.load()
        cat_map: Dict[str, int] = {}
        for p in products:
            cat = safe_text(p.get("category")) or "Uncategorized"
            cat_map[cat] = cat_map.get(cat, 0) + 1
        return [{"name": k, "count": v} for k, v in sorted(cat_map.items())]
    except Exception as exc:
        LOGGER.error("Error in /api/categories: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Count Sessions ────────────────────────────────────────────────────
@app.get("/api/counts")
async def list_counts(
    status: str = Query(""),
    limit: int = Query(50, alias="limit"),
):
    """List count sessions, optionally filtered by status."""
    try:
        sessions = inv.list_sessions(status=status or None)
        sessions = sorted(sessions, key=lambda s: s.get("created_at", ""), reverse=True)
        LOGGER.info("API /api/counts → %d sessions", len(sessions))
        return {"total": len(sessions), "sessions": sessions[:limit]}
    except Exception as exc:
        LOGGER.error("Error in /api/counts: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.post("/api/counts", status_code=201)
async def create_count(body: CountSessionBody):
    """Create a new stock count session."""
    try:
        payload = body.model_dump()
        if not payload.get("name"):
            payload["name"] = payload.get("doc_num") or f"Count-{utc_now()[:10]}"
        session = inv.create_session(payload)
        LOGGER.info("API POST /api/counts → session id=%s", session.get("id"))
        return session
    except Exception as exc:
        LOGGER.error("Error creating count session: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.get("/api/counts/{session_id}")
async def get_count(session_id: int):
    """Get a single count session by ID."""
    try:
        session = inv.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        return session
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error getting count session %s: %s", session_id, exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.post("/api/counts/{session_id}/items", status_code=201)
async def add_count_item(session_id: int, body: CountItemBody):
    """Add a counted item to a session."""
    try:
        # Auto-resolve product if product_id == 0 and sku/barcode provided
        item = body.model_dump()
        if item.get("product_id", 0) == 0:
            product = None
            if item.get("sku"):
                product = ps.find_by_sku(item["sku"])
            if not product and item.get("barcode"):
                product = ps.find_by_barcode(item["barcode"])
            if product:
                item["product_id"] = int(product.get("id", 0))
                item["product_name"] = item.get("product_name") or safe_text(product.get("product_name"))
                item["expected_quantity"] = item.get("expected_quantity") or safe_int(product.get("current_stock"), 0)
                item["sku"] = item.get("sku") or safe_text(product.get("sku"))
        row = inv.add_count_item(session_id, item)
        if not row:
            raise HTTPException(404, "Session not found")
        LOGGER.info("API POST /api/counts/%s/items → item_id=%s", session_id, row.get("item_id"))
        return row
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error adding count item to session %s: %s", session_id, exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.put("/api/counts/{session_id}/items/{item_id}")
async def update_count_item(session_id: int, item_id: int, body: CountItemUpdate):
    """Update a counted item in a session."""
    try:
        updated = inv.update_count_item(session_id, item_id, body.model_dump())
        if not updated:
            raise HTTPException(404, "Item or session not found")
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error updating count item %s in session %s: %s", item_id, session_id, exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.post("/api/counts/{session_id}/finish")
async def finish_count(session_id: int):
    """
    Mark session complete and apply stock adjustments for each counted item.
    """
    try:
        session = inv.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        items = session.get("items", [])
        adjusted = []
        for item in items:
            pid = int(item.get("product_id", 0))
            counted = safe_int(item.get("counted_quantity"), 0)
            if pid > 0:
                product = ps.get(pid)
                if product:
                    old_stock = safe_int(product.get("current_stock"), 0)
                    ps.update_stock(pid, counted)
                    diff = counted - old_stock
                    if diff != 0:
                        mov.record_movement({
                            "product_id": pid,
                            "product_name": product.get("product_name"),
                            "type": "count_adjustment",
                            "quantity": diff,
                            "reason": f"Stock count session #{session_id}",
                            "warehouse_from": session.get("warehouse", "Main"),
                            "warehouse_to": session.get("warehouse", "Main"),
                        })
                    adjusted.append({
                        "product_id": pid,
                        "product_name": product.get("product_name"),
                        "old_stock": old_stock,
                        "new_stock": counted,
                        "difference": diff,
                    })
        inv.complete_session(session_id)
        act.log_action(
            "count_session_finished",
            f"Session {session_id} completed. {len(adjusted)} products updated.",
        )
        LOGGER.info("API POST /api/counts/%s/finish → %d adjustments", session_id, len(adjusted))
        return {"status": "completed", "adjustments": adjusted}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error finishing count session %s: %s", session_id, exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Movements ─────────────────────────────────────────────────────────
@app.get("/api/movements")
async def list_movements(limit: int = Query(50)):
    """List recent stock movements."""
    try:
        movements = mov.load()
        movements = sorted(movements, key=lambda m: m.get("created_at", ""), reverse=True)
        return {"total": len(movements), "movements": movements[:limit]}
    except Exception as exc:
        LOGGER.error("Error in /api/movements: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Activity ──────────────────────────────────────────────────────────
@app.get("/api/activity")
async def list_activity(limit: int = Query(30)):
    """List recent activity log entries."""
    try:
        data = load_json(ACTIVITY_JSON)
        activity = data.get("activity", [])
        activity = sorted(activity, key=lambda a: a.get("created_at", a.get("timestamp", "")), reverse=True)
        return {"total": len(activity), "activity": activity[:limit]}
    except Exception as exc:
        LOGGER.error("Error in /api/activity: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Settings ──────────────────────────────────────────────────────────
@app.get("/api/settings")
async def get_settings():
    """Get application settings."""
    try:
        data = load_json(SETTINGS_JSON)
        return data
    except Exception as exc:
        LOGGER.error("Error in GET /api/settings: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


@app.put("/api/settings")
async def save_settings(body: SettingsBody):
    """Save application settings."""
    try:
        existing = load_json(SETTINGS_JSON)
        updated = {**existing, **body.model_dump()}
        save_json(SETTINGS_JSON, updated)
        LOGGER.info("API PUT /api/settings → saved")
        return updated
    except Exception as exc:
        LOGGER.error("Error in PUT /api/settings: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Download Sample ───────────────────────────────────────────────────
@app.get("/api/download/sample-import")
async def download_sample_import():
    """Download a sample import template Excel file."""
    try:
        file_path = EXPORT_DIR / "sample_import.xlsx"
        if not file_path.exists():
            # Generate sample file on demand
            try:
                import pandas as pd
                df = pd.DataFrame([{
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
                }])
                EXPORT_DIR.mkdir(parents=True, exist_ok=True)
                df.to_excel(str(file_path), index=False)
            except ImportError:
                raise HTTPException(500, "pandas/openpyxl not available to generate sample file")
        return FileResponse(
            str(file_path),
            filename="sample_import.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Error serving sample import: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Routes: Reset ─────────────────────────────────────────────────────────────
@app.post("/api/reset")
async def reset_all_data(confirm: str = Query("")):
    """Reset all inventory data. Requires ?confirm=YES to execute."""
    if confirm.strip().upper() != "YES":
        raise HTTPException(
            400,
            "Safety guard: append ?confirm=YES to the URL to confirm data reset. "
            "This action is irreversible.",
        )
    try:
        save_json(PRODUCTS_JSON, {"products": []})
        save_json(COUNTS_JSON, {"counts": []})
        save_json(MOVEMENTS_JSON, {"movements": []})
        save_json(ACTIVITY_JSON, {"activity": []})
        save_json(FORMS_JSON, {"forms": []})
        act.log_action("reset_all_data_mobile", "System Reset: All inventory data cleared via REST API")
        LOGGER.warning("API POST /api/reset → all data cleared")
        return {"status": "success", "message": "All inventory data has been reset to zero."}
    except Exception as exc:
        LOGGER.error("Error in /api/reset: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}") from exc


# ── Runner ────────────────────────────────────────────────────────────────────
# NOTE: Normally started as a daemon thread from app.py alongside Gradio.
# Run this file directly only for standalone API testing.
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MOBILE_API_PORT", "8765"))
    print("=" * 60)
    print("  InventoryFlow Mobile API — Standalone Mode")
    print(f"  Local URL    : http://localhost:{port}")
    print(f"  Network URL  : http://0.0.0.0:{port}")
    print(f"  API Docs     : http://localhost:{port}/docs")
    print(f"  ReDoc        : http://localhost:{port}/redoc")
    print(f"  Mobile UI    : http://localhost:{port}/")
    print()
    print("  TIP: To get a public URL, run via app.py (with GRADIO_SHARE=1)")
    print("       or tunnel this port:  ngrok http", port)
    print("=" * 60)
    LOGGER.info("Starting InventoryFlow Mobile API on http://0.0.0.0:%d", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
