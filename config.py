from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DRIVE_DIR = PROJECT_ROOT / "drive"
EXPORT_DIR = PROJECT_ROOT / "exports"
LOG_DIR = PROJECT_ROOT / "logs"
BACKUP_DIR = PROJECT_ROOT / "backups"
JSON_DIR = PROJECT_ROOT / "json"
SHEETS_FILE = DATA_DIR / "inventory_sheets.json"
PRODUCTS_JSON = JSON_DIR / "products.json"
FORMS_JSON = JSON_DIR / "forms.json"
COUNTS_JSON = JSON_DIR / "counts.json"
MOVEMENTS_JSON = JSON_DIR / "movements.json"
ACTIVITY_JSON = JSON_DIR / "activity.json"
SETTINGS_JSON = DATA_DIR / "settings.json"
COLAB_DRIVE_ROOT = Path("/content/drive/MyDrive")
COLAB_EXPORT_DIR = COLAB_DRIVE_ROOT / "AI_Inventory_System" / "exports"

for path in [DATA_DIR, DRIVE_DIR, EXPORT_DIR, LOG_DIR, BACKUP_DIR, JSON_DIR]:
    path.mkdir(parents=True, exist_ok=True)


def ensure_json_file(path: Path, default: Optional[Dict[str, Any]] = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        if default is None:
            default = {}
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
    return path


class InventoryConfig:
    """Central configuration object for inventory system."""

    def __init__(self) -> None:
        self.project_root = str(PROJECT_ROOT)
        self.colab = bool(os.getenv("COLAB_RELEASE_TAG"))
        self.sheet_name = os.getenv("INVENTORY_SHEET_NAME", "AI_Inventory_System")
        self.google_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(PROJECT_ROOT / "credentials.json"))
        self.logger_name = "inventory_system"
        self.default_form_name = "default_inventory_form"
        self.default_currency = os.getenv("INVENTORY_CURRENCY", "INR")
        self.default_locale = os.getenv("INVENTORY_LOCALE", "en_IN")
        self.drive_folder = os.getenv("INVENTORY_DRIVE_FOLDER", "AI_Inventory_System")
        self.drive_mounted = False
        self.sheet_state_file = SHEETS_FILE
        self.settings_file = SETTINGS_JSON


CONFIG = InventoryConfig()


def setup_logger() -> logging.Logger:
    logger = logging.getLogger(CONFIG.logger_name)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(LOG_DIR / "inventory.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


LOGGER = setup_logger()


def gradio_share_enabled() -> bool:
    setting = os.getenv("GRADIO_SHARE", "1" if CONFIG.colab else "0")
    return setting.strip().lower() in {"1", "true", "yes", "on"}


def running_in_notebook_kernel() -> bool:
    try:
        shell = get_ipython()  # type: ignore[name-defined]
    except NameError:
        return False
    return shell is not None and shell.__class__.__name__ == "ZMQInteractiveShell"


def initialize_colab() -> None:
    if not CONFIG.colab or not running_in_notebook_kernel():
        return
    try:
        from google.colab import auth  # type: ignore[import-not-found]
        auth.authenticate_user()
        LOGGER.info("Google authentication completed")
    except Exception as exc:  # pragma: no cover
        LOGGER.warning("Google authentication unavailable: %s", exc)

    try:
        from google.colab import drive  # type: ignore[import-not-found]

        drive.mount("/content/drive", force_remount=False)
        CONFIG.drive_mounted = True
        LOGGER.info("Google Drive mounted")
        if COLAB_EXPORT_DIR.parent.exists():
            COLAB_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # pragma: no cover
        LOGGER.warning("Drive mount failed: %s", exc)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


ensure_json_file(PRODUCTS_JSON, {"products": []})
ensure_json_file(FORMS_JSON, {"forms": []})
ensure_json_file(COUNTS_JSON, {"counts": []})
ensure_json_file(MOVEMENTS_JSON, {"movements": []})
ensure_json_file(ACTIVITY_JSON, {"activity": []})
ensure_json_file(SETTINGS_JSON, {"theme": "light", "default_sheet": CONFIG.sheet_name, "notifications": True, "dark_mode": False})

initialize_colab()
