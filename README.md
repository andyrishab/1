# 📦 InventoryFlow — AI Inventory & Stock Count System

Enterprise inventory management powered by **OCR**, **barcode scanning**, **FastAPI REST API**, **Gradio Dashboard**, **Google Sheets sync**, and a full **mobile-first single-page web UI**.

---

## 🌟 Single-Port Unified Architecture

InventoryFlow runs **everything on ONE port** (`8765` by default) using FastAPI and Gradio combined:

| Interface | URL | Description |
|-----------|-----|-------------|
| 📱 **Mobile UI** | [http://localhost:8765/](http://localhost:8765/) | Mobile-first Web App for barcode scanning & stock counting |
| 🖥️ **Gradio Dashboard** | [http://localhost:8765/dashboard/](http://localhost:8765/dashboard/) | Full Desktop Management & Analytics Dashboard |
| 📄 **API Docs (Swagger)** | [http://localhost:8765/docs](http://localhost:8765/docs) | Interactive OpenAPI / REST Documentation |
| 📋 **API Docs (ReDoc)** | [http://localhost:8765/redoc](http://localhost:8765/redoc) | Clean API Reference |

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📱 **Mobile UI (SPA)** | Fast, responsive single-page mobile app with bottom navigation bar |
| 🖥️ **Gradio Dashboard** | Rich desktop analytics dashboard mounted at `/dashboard/` |
| 📷 **Barcode Scanner** | Embedded camera scanner (Html5Qrcode) with rapid scanning & auto-increment |
| 🆕 **Unknown Barcode Flow** | Quick modal to register new products directly during a count |
| 📊 **Stock Count Sessions** | Create sessions with auto-generated Doc # (`SC-YYYYMMDD-XXX`), date, location & notes |
| ✏️ **Session & Item CRUD** | Full Edit (modal) and Delete (with confirmation) support for sessions & items |
| 🔍 **OCR Extraction** | Automatically extract product metadata from images using OCR |
| 📦 **Product Master** | Full product CRUD with SKU, barcode, category, unit price, & initial stock |
| 🗂️ **Categories** | Auto-managed categories dynamically aggregated from product data |
| 📈 **Reports & Analytics** | Stock valuation, low stock warnings, variance calculation & movement history |
| 🔄 **Google Sheets Sync** | Optional real-time auto-sync to Google Sheets |
| 📥 **Excel Import/Export** | Bulk import and export via `.xlsx` files |
| 🌐 **Unified REST API** | Complete FastAPI backend under `/api/` |
| ☁️ **Colab & Public Link** | Easy deployment in Google Colab with `GRADIO_SHARE=1` public tunnels |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Windows Note:** `pyzbar` uses ZBar DLLs. Ensure C++ runtime is installed or install via Conda if using standalone pyzbar.  
> **Linux Note:** Install zbar via `sudo apt-get install libzbar0`.

### 2. Run the Application

```bash
python app.py
```

Console output will confirm startup on single port `8765`:

```
╔══════════════════════════════════════════════════════════════╗
║      📦  InventoryFlow — AI Inventory System  (v2)           ║
║            Single-Port Mode · FastAPI + Gradio               ║
╠══════════════════════════════════════════════════════════════╣
║  Environment  : windows                                      ║
║  🌐 One URL   : http://localhost:8765                       ║
║                                                              ║
║  📱 Mobile UI : http://localhost:8765/                       ║
║  🖥️  Dashboard : http://localhost:8765/dashboard/            ║
║  📋 API Docs  : http://localhost:8765/docs                   ║
╚══════════════════════════════════════════════════════════════╝
```

### 3. Public Share URL (Optional / Google Colab)

To generate a public share link (e.g., for mobile camera access across network or in Colab):

```bash
# Windows PowerShell
$env:GRADIO_SHARE="1"; python app.py

# Linux / macOS
GRADIO_SHARE=1 python app.py
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_PORT` | `8765` (auto-detects free port) | Port for single-port FastAPI + Gradio app |
| `GRADIO_SHARE` | `0` (`1` in Colab) | Set to `1` to enable public `.gradio.live` link |
| `GOOGLE_APPLICATION_CREDENTIALS` | `credentials.json` | Path to Google Service Account JSON |
| `INVENTORY_SHEET_NAME` | `AI_Inventory_System` | Target Google Sheets file name |
| `INVENTORY_CURRENCY` | `INR` | Default currency symbol (e.g., `USD`, `EUR`, `INR`) |

---

## 📁 Project Structure

```
inventoryflow/
├── app.py              # Main entrypoint — single-port server launcher
├── mobile_api.py       # FastAPI REST API endpoints & route handlers
├── mobile_ui.html      # Mobile UI SPA frontend (HTML/JS/Tailwind)
├── ui.py               # Gradio Desktop Dashboard interface
├── config.py           # Paths, logger, environment settings
├── products.py         # Product Master CRUD engine
├── inventory.py        # Stock count sessions & inventory logic
├── movements.py        # Stock movement recording & audit logs
├── reports.py          # Excel reports & valuation generator
├── ocr.py              # OCR engine wrapper (EasyOCR / PaddleOCR)
├── barcode.py          # Barcode decoding utilities (PyZBar / OpenCV)
├── importer.py         # Excel product import engine
├── excel_export.py     # Excel export generator
├── google_sheets.py    # Google Sheets synchronization engine
├── utils.py            # Shared helper functions
├── requirements.txt    # Required Python packages
│
├── json/               # Persistent data storage (products, counts, movements)
├── exports/            # Output Excel/JSON reports
├── logs/               # Application runtime logs
└── data/               # App configuration & state
```

---

## 🌐 REST API Reference

Base URL: `http://localhost:8765`

### 📦 Products API
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/products` | Search & list products |
| `POST` | `/api/products` | Create new product |
| `GET` | `/api/products/{id}` | Get product details |
| `PUT` | `/api/products/{id}` | Update product details |
| `DELETE` | `/api/products/{id}` | Delete product |
| `GET` | `/api/products/lookup` | Find by SKU or barcode |
| `GET` | `/api/categories` | List categories with product counts |

### 📊 Count Sessions API
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/counts` | List count sessions |
| `POST` | `/api/counts` | Create stock count session |
| `GET` | `/api/counts/{id}` | Get count session & items |
| `PATCH` | `/api/counts/{id}` | Update session info (name, inspector, location, status) |
| `DELETE` | `/api/counts/{id}` | Permanently delete count session |
| `POST` | `/api/counts/{id}/items` | Add counted item to session |
| `PUT` | `/api/counts/{id}/items/{item_id}` | Update counted quantity of an item |
| `DELETE` | `/api/counts/{id}/items/{item_id}` | Remove counted item from session |
| `POST` | `/api/counts/{id}/finish` | Finalize count session & adjust inventory |

### 📈 Reports & System API
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stats` | System statistics & totals |
| `GET` | `/api/movements` | Stock movement history |
| `GET` | `/api/activity` | Activity audit logs |
| `GET` | `/api/export` | Export full inventory as JSON |
| `POST` | `/api/import` | Import products from JSON |
| `GET` | `/api/settings` | Retrieve app settings |
| `PUT` | `/api/settings` | Save app settings |

---

## 🗄️ Storage & Logging

- **Database-Free JSON Storage:** Data is saved in human-readable JSON files inside `json/` (`products.json`, `counts.json`, `movements.json`, `activity.json`).
- **Clean Terminal Logs:** Suppresses noisy 404 logs from browser devtools, map files, and manifest queries.

---

## 🏢 Credits

Powered by **NEXORION® · SAP Gold Partner**

> Built with FastAPI, Gradio, Python, and ❤️
"# -new_test" 
