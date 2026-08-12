from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from config import LOGGER, PRODUCTS_JSON
from utils import (
    hash_value,
    normalize_currency,
    parse_date,
    safe_float,
    safe_int,
    safe_text,
    save_json,
    slugify,
    utc_now,
    load_json,
)

DEFAULT_PRODUCT_SCHEMA = {
    "product_name": "",
    "sku": "",
    "barcode": "",
    "category": "",
    "sub_category": "",
    "brand": "",
    "supplier": "",
    "purchase_price": 0.0,
    "selling_price": 0.0,
    "mrp": 0.0,
    "hsn_code": "",
    "gst": "",
    "unit": "",
    "batch_number": "",
    "manufacturing_date": "",
    "expiry_date": "",
    "warranty": "",
    "serial_number": "",
    "product_description": "",
    "product_notes": "",
    "warehouse": "Main",
    "location": "",
    "rack": "",
    "shelf": "",
    "bin": "",
    "zone": "",
    "current_stock": 0,
    "opening_stock": 0,
    "minimum_stock": 0,
    "maximum_stock": 0,
    "reorder_level": 0,
    "status": "active",
    "images": [],
    "tags": [],
}


class ProductService:
    """Manage product records stored as JSON."""

    def __init__(self) -> None:
        self.path = PRODUCTS_JSON

    def load(self) -> List[Dict[str, Any]]:
        payload = load_json(self.path)
        return payload.get("products", [])

    def save(self, products: List[Dict[str, Any]]) -> None:
        save_json(self.path, {"products": products})

    def _next_id(self, products: List[Dict[str, Any]]) -> int:
        if not products:
            return 1
        return max(int(product.get("id", 0)) for product in products) + 1

    def _sanitize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        product = {**DEFAULT_PRODUCT_SCHEMA}
        for field, default in DEFAULT_PRODUCT_SCHEMA.items():
            if field in payload:
                if field in {"current_stock", "opening_stock", "minimum_stock", "maximum_stock", "reorder_level"}:
                    product[field] = safe_int(payload.get(field), default)
                elif field in {"purchase_price", "selling_price", "mrp"}:
                    product[field] = safe_float(payload.get(field), default)
                elif field in {"images", "tags"} and payload.get(field) is not None:
                    product[field] = list(payload.get(field)) if isinstance(payload.get(field), list) else [safe_text(payload.get(field))]
                elif field in {"manufacturing_date", "expiry_date"}:
                    product[field] = parse_date(payload.get(field))
                else:
                    product[field] = safe_text(payload.get(field)) or default
        product["barcode_hash"] = hash_value(product.get("barcode", ""))
        product["slug"] = slugify(product.get("product_name", ""))
        return product

    def add(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        products = self.load()
        product = self._sanitize_payload(payload)
        product["id"] = self._next_id(products)
        product["created_at"] = utc_now()
        product["updated_at"] = utc_now()
        if not product["opening_stock"]:
            product["opening_stock"] = product["current_stock"]
        products.append(product)
        self.save(products)
        LOGGER.info("Added product %s", product.get("product_name"))
        return product

    def list(self) -> List[Dict[str, Any]]:
        return self.load()

    def get(self, product_id: int) -> Optional[Dict[str, Any]]:
        for product in self.load():
            if int(product.get("id", 0)) == int(product_id):
                return product
        return None

    def update(self, product_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        products = self.load()
        for index, product in enumerate(products):
            if int(product.get("id", 0)) == int(product_id):
                # Only sanitize and merge fields that are explicitly provided
                # to prevent partial updates from wiping unrelated fields.
                if len(payload) > 5:  # full update — sanitize everything
                    sanitized = self._sanitize_payload(payload)
                    updated = {**product, **sanitized}
                else:  # targeted partial update — only merge provided keys
                    updated = dict(product)
                    for key, value in payload.items():
                        if value is not None:
                            if key in {"current_stock", "opening_stock", "minimum_stock", "maximum_stock", "reorder_level"}:
                                updated[key] = safe_int(value, 0)
                            elif key in {"purchase_price", "selling_price", "mrp"}:
                                updated[key] = safe_float(value, 0.0)
                            else:
                                updated[key] = value
                updated["id"] = int(product_id)
                updated["updated_at"] = utc_now()
                products[index] = updated
                self.save(products)
                LOGGER.info("Updated product %s", updated.get("product_name"))
                return updated
        return None

    def delete(self, product_id: int) -> bool:
        products = self.load()
        filtered = [product for product in products if int(product.get("id", 0)) != int(product_id)]
        if len(filtered) != len(products):
            self.save(filtered)
            LOGGER.info("Deleted product id=%s", product_id)
            return True
        return False

    def search(self, keyword: str = "", filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        keyword = safe_text(keyword).lower()
        results: List[Dict[str, Any]] = []
        for product in self.load():
            searchable = " ".join(
                [safe_text(product.get(field)) for field in [
                    "product_name",
                    "sku",
                    "barcode",
                    "category",
                    "sub_category",
                    "brand",
                    "supplier",
                    "warehouse",
                    "location",
                ]]
            ).lower()
            if keyword and keyword not in searchable:
                continue
            if filters:
                if not self._matches_filters(product, filters):
                    continue
            results.append(product)
        return results

    def _matches_filters(self, product: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if value in (None, ""):
                continue
            if safe_text(product.get(key)).lower() != safe_text(value).lower():
                return False
        return True

    def duplicate_barcode(self, barcode: str) -> bool:
        return any(safe_text(product.get("barcode")) == safe_text(barcode) and safe_text(barcode) for product in self.load())

    def duplicate_sku(self, sku: str) -> bool:
        return any(safe_text(product.get("sku")) == safe_text(sku) and safe_text(sku) for product in self.load())

    def find_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        barcode = safe_text(barcode)
        for product in self.load():
            if safe_text(product.get("barcode")) == barcode:
                return product
        return None

    def find_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        sku = safe_text(sku)
        for product in self.load():
            if safe_text(product.get("sku")) == sku:
                return product
        return None

    def adjust_stock(self, product_id: int, quantity: int, reason: str = "adjustment") -> Optional[Dict[str, Any]]:
        """Increment or decrement stock by quantity without touching other fields."""
        products = self.load()
        for index, product in enumerate(products):
            if int(product.get("id", 0)) == int(product_id):
                current = safe_int(product.get("current_stock"), 0)
                new_stock = max(0, current + quantity)
                if product.get("opening_stock") is None:
                    products[index]["opening_stock"] = current
                products[index]["current_stock"] = new_stock
                products[index]["updated_at"] = utc_now()
                self.save(products)
                LOGGER.info("Stock adjusted: product id=%s %+d → %d (%s)", product_id, quantity, new_stock, reason)
                return products[index]
        return None

    def update_stock(self, product_id: int, new_stock: int) -> Optional[Dict[str, Any]]:
        """Set stock to an absolute value without touching other fields."""
        products = self.load()
        for index, product in enumerate(products):
            if int(product.get("id", 0)) == int(product_id):
                products[index]["current_stock"] = safe_int(new_stock, 0)
                products[index]["updated_at"] = utc_now()
                self.save(products)
                LOGGER.info("Stock set: product id=%s → %d", product_id, new_stock)
                return products[index]
        return None

    def recent_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        products = sorted(self.load(), key=lambda item: item.get("created_at", ""), reverse=True)
        return products[:limit]

    def recently_updated(self, limit: int = 10) -> List[Dict[str, Any]]:
        products = sorted(self.load(), key=lambda item: item.get("updated_at", ""), reverse=True)
        return products[:limit]


def create_product(payload: Dict[str, Any]) -> Dict[str, Any]:
    return ProductService().add(payload)
