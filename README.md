# 📦 InventoryFlow — AI Inventory & Stock Count System

Enterprise inventory management powered by **OCR**, **barcode scanning**, **FastAPI REST API**, **Google Sheets sync**, and a full **mobile-first web UI**.

## 🔴 Live Demo

| Interface | Public URL |
|-----------|------------|
| 🖥️ **Gradio Dashboard** | [https://3dc5af45673dd3df03.gradio.live](https://3dc5af45673dd3df03.gradio.live) |
| 📱 **Mobile UI / REST API** | [http://localhost:8765](http://localhost:8765) *(local network)* |

> **Note:** The Gradio public URL is active while `python app.py` is running. It expires after the session ends.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📱 **Mobile UI** | Responsive single-page app at `localhost:8765` |
| 🖥️ **Gradio Dashboard** | Desktop management UI at `localhost:7860` |
| 📷 **Barcode Scanner** | Real-time camera scanner via Html5Qrcode |
| 🔍 **OCR Extraction** | Auto-read product details from images |
| 📊 **Stock Counting** | Guided count sessions with variance reporting |
| 📦 **Product Master** | Full CRUD with SKU, barcode, category, price |
| 🗂️ **Categories** | Auto-generated from product data |
| 📈 **Reports** | Low stock, valuation, count, product master exports |
| 🔄 **Google Sheets Sync** | Optional auto-sync to Google Sheets |
| 📥 **Excel Import/Export** | Bulk import/export via `.xlsx` |
| 🌐 **REST API** | Full FastAPI backend at `localhost:8765/api` |
| 🔗 **Public URL** | Gradio live link → [https://3dc5af45673dd3df03.gradio.live](https://3dc5af45673dd3df03.gradio.live) |

---

## 🚀 Quick Start (Local — Windows / Linux / macOS)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> **Windows users**: `pyzbar` requires the ZBar DLL. Download from https://github.com/NaturalHistoryMuseum/pyzbar#installation or install via conda.
>
> **Linux users**: `sudo apt-get install libzbar0`

### 2. Run the application

```bash
python app.py
```

Both servers start automatically:

| Server | URL |
|--------|-----|
| 📱 Mobile UI | http://localhost:8765 |
| 🖥️ Gradio Dashboard | http://localhost:7860 |
| 📄 API Docs (Swagger) | http://localhost:8765/docs |
| 📋 API Docs (ReDoc) | http://localhost:8765/redoc |
| 📊 Stats Endpoint | http://localhost:8765/api/stats |
| 📦 Products Endpoint | http://localhost:8765/api/products |
| ⬇️ Export Endpoint | http://localhost:8765/api/export |

> Ports are **auto-detected** — if `8765` or `7860` are busy, the next free port is used automatically.

### 3. Enable public URL (optional)

```bash
# Windows (PowerShell)
$env:GRADIO_SHARE="1"; python app.py

# Linux / macOS
GRADIO_SHARE=1 python app.py
```

A `https://xxxxxxxx.gradio.live` URL will appear in the terminal.

**Current live URL:** [https://3dc5af45673dd3df03.gradio.live](https://3dc5af45673dd3df03.gradio.live)

---

## ☁️ Run in Google Colab

Open `Inventory_System_Colab.ipynb` in Google Colab, or follow these steps manually:

### Step 1 — Install dependencies

```python
!apt-get update -qq && apt-get install -y -qq libzbar0
!pip install -r requirements.txt --quiet
```

### Step 2 — Authenticate and start

```python
from google.colab import auth
auth.authenticate_user()

from app import main
main()
```

The app automatically detects the Colab environment:
- **Gradio Dashboard** → public `https://....gradio.live` link
- **Mobile UI & REST API** → accessible on port `8765`

---

## ⚙️ Configuration

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `GRADIO_SERVER_PORT` | `7860` (auto) | Preferred Gradio port |
| `MOBILE_API_PORT` | `8765` (auto) | Preferred Mobile API port |
| `GRADIO_SHARE` | `0` local / `1` Colab | Enable public Gradio link |
| `GOOGLE_APPLICATION_CREDENTIALS` | `credentials.json` | Path to Google service-account key |
| `INVENTORY_SHEET_NAME` | `AI_Inventory_System` | Google Sheets document name |
| `INVENTORY_CURRENCY` | `INR` | Default currency symbol |

---

## 📁 Project Structure

```
inventoryflow/
├── app.py              # Main entrypoint — starts Gradio + Mobile API
├── ui.py               # Gradio UI builder (all tabs)
├── mobile_api.py       # FastAPI REST server (port 8765)
├── mobile_ui.html      # Mobile single-page app
├── config.py           # Paths, logger, JSON helpers
├── products.py         # Product CRUD service
├── inventory.py        # Count sessions & movements
├── reports.py          # Excel report generation
├── ocr.py              # OCR engine wrapper
├── barcode.py          # Barcode decoder
├── importer.py         # Excel import parser
├── excel_export.py     # Excel export writer
├── google_sheets.py    # Google Sheets sync
├── forms.py            # Custom form builder
├── utils.py            # Shared utilities
├── requirements.txt    # Python dependencies
│
├── json/               # Live data (products, counts, movements…)
├── exports/            # Generated Excel & JSON exports
├── logs/               # Application log files
├── backups/            # Auto-backup snapshots
└── data/               # Settings & sheets state
```

---

## 🌐 REST API Reference

Base URL: `http://localhost:8765`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Mobile UI (HTML) |
| `GET` | `/api` | Health check |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |
| `GET` | `/api/stats` | Dashboard statistics |
| `GET` | `/api/products` | List / search products |
| `POST` | `/api/products` | Create product |
| `GET` | `/api/products/{id}` | Get product |
| `PUT` | `/api/products/{id}` | Update product |
| `DELETE` | `/api/products/{id}` | Delete product |
| `GET` | `/api/products/lookup` | Find by SKU or barcode |
| `GET` | `/api/search` | Search products |
| `GET` | `/api/export` | Export all products as JSON |
| `POST` | `/api/import` | Import products from JSON |
| `GET` | `/api/categories` | Category list with counts |
| `GET` | `/api/counts` | List count sessions |
| `POST` | `/api/counts` | Create count session |
| `GET` | `/api/counts/{id}` | Get count session |
| `POST` | `/api/counts/{id}/items` | Add counted item |
| `PUT` | `/api/counts/{id}/items/{iid}` | Update counted item |
| `POST` | `/api/counts/{id}/finish` | Finish session + adjust stock |
| `GET` | `/api/movements` | Recent stock movements |
| `GET` | `/api/activity` | Activity log |
| `GET` | `/api/settings` | App settings |
| `PUT` | `/api/settings` | Save settings |
| `POST` | `/api/reset` | Reset all data |

---

## 🗄️ Data Storage

All data is stored locally as **JSON files** in the `json/` directory — no database required.

| File | Contents |
|------|----------|
| `json/products.json` | All product records |
| `json/counts.json` | Stock count sessions |
| `json/movements.json` | Stock movement history |
| `json/activity.json` | User activity audit log |
| `json/forms.json` | Custom form definitions |
| `data/settings.json` | App settings |

Excel exports → `exports/`  
Logs → `logs/inventory.log`

---

## 🔧 Troubleshooting

### `Google Sheets authentication unavailable`
Expected when no `credentials.json` is present. All local features (JSON, Excel, inventory) work normally. To enable Sheets sync, download a Google service-account key and set `GOOGLE_APPLICATION_CREDENTIALS`.

### Port already in use
Ports are auto-detected. The app scans `7860–7910` for Gradio and `8765–8800` for the Mobile API. You can override with environment variables:
```bash
GRADIO_SERVER_PORT=7865 MOBILE_API_PORT=8770 python app.py
```

### Camera / barcode scanner not working
- Allow camera permission in your browser
- Use **HTTPS** or `localhost` (camera API requires secure context)
- On mobile, use Chrome or Safari

### OCR not extracting text
- Ensure `easyocr` or `paddleocr` is installed (`pip install easyocr`)
- First run downloads model weights (~200 MB)

### No public Gradio URL
Set `GRADIO_SHARE=1` and restart. Make sure port `7860` is not blocked by a firewall.

---

## 📋 Requirements

Key packages from `requirements.txt`:

```
gradio>=4.44.0
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
pandas>=2.2.0
openpyxl>=3.1.0
Pillow>=10.4.0
numpy>=1.26.0
opencv-python-headless>=4.9.0
pyzbar>=0.1.0
easyocr>=1.4.0
gspread>=5.0.0
google-auth>=2.0.0
```

---

## 🏢 Credits

Powered by **NEXORION® · SAP Gold Partner**

> Built with Gradio, FastAPI, Python, and ❤️
#
