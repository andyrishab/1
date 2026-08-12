from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TypeVar

from config import LOGGER

T = TypeVar("T")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def parse_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(str(value)).date().isoformat()
    except ValueError:
        LOGGER.warning("Unable to parse date: %s", value)
        return ""


def normalize_currency(value: Any) -> str:
    number = safe_float(value)
    return f"{number:.2f}"


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = safe_text(value).lower()
    return text in {"true", "yes", "1", "y", "on"}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    """Atomically write JSON — uses a temp file then rename to prevent corruption."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to temp file in the same directory, then rename
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)  # atomic on POSIX; near-atomic on Windows
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def validate_required(payload: Dict[str, Any], fields: Sequence[str]) -> List[str]:
    errors: List[str] = []
    for field in fields:
        if not safe_text(payload.get(field)):
            errors.append(f"{field} is required")
    return errors


def create_activity(action: str, details: str) -> Dict[str, Any]:
    return {"action": action, "details": details, "timestamp": utc_now()}


def append_activity(activity_log: List[Dict[str, Any]], action: str, details: str) -> List[Dict[str, Any]]:
    activity_log.append(create_activity(action, details))
    return activity_log


def build_scan_form_payload(ocr_result: Dict[str, Any], barcode_rows: List[List[Any]]) -> Dict[str, Any]:
    barcode_value = ""
    if barcode_rows:
        barcode_value = str(barcode_rows[0][1] or "")
    output = {
        "product_name": ocr_result.get("product_name", "") or "",
        "sku": ocr_result.get("sku", "") or "",
        "barcode": barcode_value or ocr_result.get("barcode", "") or "",
        "brand": ocr_result.get("brand", "") or "",
        "category": ocr_result.get("category", "") or "",
        "price": ocr_result.get("price", "") or "",
        "mrp": ocr_result.get("mrp", "") or "",
        "batch_number": ocr_result.get("batch", "") or "",
        "expiry_date": ocr_result.get("expiry", "") or "",
    }
    return output


def merge_dicts(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(fallback)
    merged.update({k: v for k, v in primary.items() if v is not None and v != ""})
    return merged
