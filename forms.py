from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional

from config import FORMS_JSON, load_json, save_json
from utils import safe_text, slugify, utc_now

FORM_FIELD_TYPES = [
    "text",
    "number",
    "decimal",
    "currency",
    "percentage",
    "date",
    "time",
    "dropdown",
    "multi_select",
    "checkbox",
    "radio",
    "toggle",
    "barcode",
    "qr",
    "sku",
    "category",
    "brand",
    "supplier",
    "image",
    "pdf",
    "file",
    "rating",
    "notes",
    "formula",
    "uuid",
    "auto_increment",
]


class FormBuilderService:
    """Manage dynamic forms stored as JSON."""

    def __init__(self) -> None:
        self.path = FORMS_JSON

    def load(self) -> List[Dict[str, Any]]:
        payload = load_json(self.path)
        return payload.get("forms", [])

    def save(self, forms: List[Dict[str, Any]]) -> None:
        save_json(self.path, {"forms": forms})

    def _next_id(self, forms: List[Dict[str, Any]]) -> int:
        if not forms:
            return 1
        return max(int(form.get("id", 0)) for form in forms) + 1

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        forms = self.load()
        form = copy.deepcopy(payload)
        form["id"] = self._next_id(forms)
        form["slug"] = slugify(safe_text(form.get("name")))
        form["status"] = safe_text(form.get("status", "active"))
        form["archived"] = False
        form["default"] = bool(payload.get("default", False))
        form["created_at"] = utc_now()
        form["updated_at"] = utc_now()
        form["fields"] = payload.get("fields", [])
        forms.append(form)
        self.save(forms)
        if form["default"]:
            self.set_default(form["id"])
        return form

    def list(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        forms = self.load()
        if include_archived:
            return forms
        return [form for form in forms if not form.get("archived", False)]

    def get(self, form_id: int) -> Optional[Dict[str, Any]]:
        for form in self.load():
            if int(form.get("id", 0)) == int(form_id):
                return form
        return None

    def update(self, form_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        forms = self.load()
        updated_form = None
        for index, form in enumerate(forms):
            if int(form.get("id", 0)) == int(form_id):
                updated_form = {**form, **payload}
                updated_form["slug"] = slugify(safe_text(updated_form.get("name")))
                updated_form["updated_at"] = utc_now()
                forms[index] = updated_form
                break
        if updated_form is not None:
            self.save(forms)
        return updated_form

    def delete(self, form_id: int) -> bool:
        forms = self.load()
        cleaned = [form for form in forms if int(form.get("id", 0)) != int(form_id)]
        if len(cleaned) != len(forms):
            self.save(cleaned)
            return True
        return False

    def archive(self, form_id: int) -> bool:
        form = self.get(form_id)
        if form is None:
            return False
        return self.update(form_id, {"archived": True}) is not None

    def restore(self, form_id: int) -> bool:
        form = self.get(form_id)
        if form is None:
            return False
        return self.update(form_id, {"archived": False}) is not None

    def duplicate(self, form_id: int) -> Optional[Dict[str, Any]]:
        form = self.get(form_id)
        if form is None:
            return None
        duplicate = copy.deepcopy(form)
        duplicate.pop("id", None)
        duplicate["name"] = f"{form.get('name')} Copy"
        duplicate["default"] = False
        return self.create(duplicate)

    def set_default(self, form_id: int) -> bool:
        forms = self.load()
        updated = False
        for index, form in enumerate(forms):
            forms[index]["default"] = int(form.get("id", 0)) == int(form_id)
            updated = True
        if updated:
            self.save(forms)
        return updated

    def import_json(self, json_string: str) -> List[Dict[str, Any]]:
        try:
            payload = json.loads(json_string)
            forms = payload.get("forms") if isinstance(payload, dict) else []
            imported = []
            for form in forms:
                imported.append(self.create(form))
            return imported
        except json.JSONDecodeError:
            return []

    def export_json(self, form_id: Optional[int] = None) -> str:
        if form_id is None:
            payload = {"forms": self.load()}
        else:
            form = self.get(form_id)
            payload = {"forms": [form]} if form else {"forms": []}
        return json.dumps(payload, indent=2)


def create_default_form() -> Dict[str, Any]:
    return {
        "name": "Default Inventory Form",
        "description": "Default inventory form",
        "fields": [
            {"name": "product_name", "label": "Product Name", "type": "text", "required": True},
            {"name": "sku", "label": "SKU", "type": "text", "required": False},
            {"name": "barcode", "label": "Barcode", "type": "barcode", "required": False},
            {"name": "category", "label": "Category", "type": "text", "required": False},
            {"name": "brand", "label": "Brand", "type": "text", "required": False},
            {"name": "current_stock", "label": "Current Stock", "type": "number", "required": False},
            {"name": "purchase_price", "label": "Purchase Price", "type": "currency", "required": False},
            {"name": "selling_price", "label": "Selling Price", "type": "currency", "required": False},
            {"name": "notes", "label": "Notes", "type": "notes", "required": False},
        ],
    }
