from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config import LOGGER
from excel_export import ExcelExporter
from inventory import InventoryService, MovementService, ActivityService
from products import ProductService
from utils import safe_int, safe_text, utc_now


class ReportService:
    """Generate reports and analytics summaries."""

    def __init__(self) -> None:
        self.products_service = ProductService()
        self.inventory_service = InventoryService()
        self.movement_service = MovementService()
        self.activity_service = ActivityService()

    def dashboard_metrics(self) -> Dict[str, Any]:
        products = self.products_service.list()
        total_products = len(products)
        total_inventory = sum(safe_int(product.get("current_stock", 0), 0) for product in products)
        inventory_value = sum(safe_int(product.get("current_stock", 0), 0) * float(product.get("purchase_price", 0) or 0.0) for product in products)
        low_stock = sum(1 for product in products if safe_int(product.get("current_stock", 0), 0) <= safe_int(product.get("reorder_level", 0), 0) and safe_int(product.get("reorder_level", 0), 0) > 0)
        out_of_stock = sum(1 for product in products if safe_int(product.get("current_stock", 0), 0) <= 0)
        overstock = sum(1 for product in products if safe_int(product.get("current_stock", 0), 0) >= safe_int(product.get("maximum_stock", 0), 0) and safe_int(product.get("maximum_stock", 0), 0) > 0)
        near_expiry = sum(1 for product in products if product.get("expiry_date") and self._is_near_expiry(product.get("expiry_date")))
        recent_products = self.products_service.recent_products(limit=10)
        recently_updated = self.products_service.recently_updated(limit=10)
        recent_activity = self.activity_service.list_activity(limit=10)
        session_counts = len(self.inventory_service.list_sessions())
        return {
            "total_products": total_products,
            "total_inventory": total_inventory,
            "inventory_value": round(inventory_value, 2),
            "today_count_sessions": sum(1 for session in self.inventory_service.list_sessions() if self._is_today(session.get("created_at"))),
            "pending_count_sessions": sum(1 for session in self.inventory_service.list_sessions() if safe_text(session.get("status")).lower() in {"active", "paused"}),
            "completed_count_sessions": sum(1 for session in self.inventory_service.list_sessions() if safe_text(session.get("status")).lower() == "completed"),
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "overstock": overstock,
            "near_expiry": near_expiry,
            "recent_products": recent_products,
            "recently_updated": recently_updated,
            "recent_activity": recent_activity,
            "session_count": session_counts,
            "brand_breakdown": dict(Counter(product.get("brand", "") for product in products)),
            "category_breakdown": dict(Counter(product.get("category", "") for product in products)),
        }

    def _is_today(self, timestamp: Any) -> bool:
        if not timestamp:
            return False
        try:
            created = datetime.fromisoformat(str(timestamp))
            return created.date() == datetime.utcnow().date()
        except ValueError:
            return False

    def _is_near_expiry(self, expiry_date: Any, days: int = 30) -> bool:
        if not expiry_date:
            return False
        try:
            expiry = datetime.fromisoformat(str(expiry_date))
            return 0 <= (expiry - datetime.utcnow()).days <= days
        except ValueError:
            return False

    def product_master_report(self) -> List[Dict[str, Any]]:
        return self.products_service.list()

    def stock_report(self) -> List[Dict[str, Any]]:
        return self.products_service.list()

    def count_report(self) -> List[Dict[str, Any]]:
        reports: List[Dict[str, Any]] = []
        for session in self.inventory_service.list_sessions():
            metrics = self.inventory_service.session_metrics(int(session.get("id", 0)))
            reports.append({"session": session, "metrics": metrics})
        return reports

    def variance_report(self) -> List[Dict[str, Any]]:
        reports: List[Dict[str, Any]] = []
        for session in self.inventory_service.list_sessions():
            for item in session.get("items", []):
                reports.append(
                    {
                        "session_id": session.get("id"),
                        "product_name": item.get("product_name"),
                        "barcode": item.get("barcode"),
                        "expected_quantity": item.get("expected_quantity"),
                        "counted_quantity": item.get("counted_quantity"),
                        "difference": item.get("difference"),
                        "status": item.get("status"),
                    }
                )
        return reports

    def low_stock_report(self) -> List[Dict[str, Any]]:
        return [product for product in self.products_service.list() if safe_int(product.get("current_stock", 0), 0) <= safe_int(product.get("reorder_level", 0), 0) and safe_int(product.get("reorder_level", 0), 0) > 0]

    def expiry_report(self, days: int = 30) -> List[Dict[str, Any]]:
        return [product for product in self.products_service.list() if product.get("expiry_date") and self._is_near_expiry(product.get("expiry_date"), days)]

    def inventory_valuation(self) -> Dict[str, Any]:
        products = self.products_service.list()
        valuation = sum(safe_int(product.get("current_stock", 0), 0) * float(product.get("purchase_price", 0) or 0.0) for product in products)
        return {"inventory_valuation": round(valuation, 2), "product_count": len(products)}

    def brand_report(self) -> Dict[str, int]:
        return dict(Counter(product.get("brand", "") for product in self.products_service.list()))

    def category_report(self) -> Dict[str, int]:
        return dict(Counter(product.get("category", "") for product in self.products_service.list()))

    def supplier_report(self) -> Dict[str, int]:
        return dict(Counter(product.get("supplier", "") for product in self.products_service.list()))

    def movement_report(self, movement_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.movement_service.list_movements(movement_type)

    def activity_report(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.activity_service.list_activity(limit=limit)

    def daily_activity_report(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        if date_str is None:
            date_str = datetime.utcnow().date().isoformat()
        return [item for item in self.activity_service.list_activity() if str(item.get("timestamp", "")).startswith(date_str)]

    def weekly_activity_report(self) -> List[Dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(days=7)
        return [item for item in self.activity_service.list_activity() if self._parse_timestamp(item.get("timestamp")) >= cutoff]

    def monthly_activity_report(self) -> List[Dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(days=30)
        return [item for item in self.activity_service.list_activity() if self._parse_timestamp(item.get("timestamp")) >= cutoff]

    def _parse_timestamp(self, value: Any) -> datetime:
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return datetime.min

    def export_low_stock_report(self) -> str:
        low_stock_products = self.low_stock_report()
        exporter = ExcelExporter()
        return exporter.export_stock(low_stock_products, filename="low_stock_report.xlsx")

    def export_inventory_valuation(self) -> str:
        rows = [
            {
                "Product Name": product.get("product_name", ""),
                "Current Stock": product.get("current_stock", 0),
                "Purchase Price": product.get("purchase_price", 0.0),
                "Inventory Value": safe_int(product.get("current_stock", 0), 0) * float(product.get("purchase_price", 0) or 0.0),
            }
            for product in self.products_service.list()
        ]
        exporter = ExcelExporter()
        return exporter.export_stock(rows, filename="inventory_valuation.xlsx")

    def export_product_master(self) -> str:
        exporter = ExcelExporter()
        return exporter.export_products(self.products_service.list(), filename="product_master.xlsx")

    def export_count_report(self) -> str:
        reports = self.count_report()
        rows = [
            {
                "Session ID": report["session"].get("id"),
                "Session Name": report["session"].get("name"),
                "Total Items": report["metrics"].get("total_items"),
                "Counted": report["metrics"].get("counted_quantity"),
                "Expected": report["metrics"].get("expected_quantity"),
                "Variance": report["metrics"].get("variance"),
            }
            for report in reports
        ]
        exporter = ExcelExporter()
        return exporter.export_count_report(rows, filename="count_report.xlsx")


def generate_dashboard_metrics() -> Dict[str, Any]:
    return ReportService().dashboard_metrics()
