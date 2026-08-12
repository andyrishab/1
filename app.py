"""
app.py — InventoryFlow Main Entrypoint (Single-Port Mode)
==========================================================
Runs EVERYTHING on ONE port using FastAPI + Gradio mounted together.

  http://localhost:8765/          → Mobile UI  (scan barcodes, count stock)
  http://localhost:8765/dashboard → Gradio Desktop Dashboard
  http://localhost:8765/api/...   → REST API
  http://localhost:8765/docs      → Swagger API Docs

Usage
-----
    python app.py                        # local run — port 8765
    SERVER_PORT=9000 python app.py       # custom port
    GRADIO_SHARE=1   python app.py       # with public Gradio share URL
    INVENTORY_CURRENCY=USD python app.py # custom currency

Environment Variables
---------------------
  SERVER_PORT        Single port for everything  (default: 8765)
  GRADIO_SHARE       "1" to enable public URL
  INVENTORY_CURRENCY Currency symbol             (default: INR)
"""

from __future__ import annotations

import os
import signal
import socket
import sys
from typing import Any

from config import LOGGER, gradio_share_enabled


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 1 — Utilities
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _is_port_free(port: int, host: str = "0.0.0.0") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_free_port(start: int, end: int = 0) -> int:
    if end == 0:
        end = start + 50
    for port in range(start, end + 1):
        if _is_port_free(port):
            return port
    raise OSError(f"No free port found between {start} and {end}.")


def is_colab() -> bool:
    return bool(
        os.getenv("COLAB_RELEASE_TAG")
        or os.getenv("COLAB_BACKEND_VERSION")
        or os.getenv("COLAB_GPU")
    )


def detect_environment() -> str:
    if is_colab():
        return "colab"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("darwin"):
        return "macos"
    return "linux"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 2 — Graceful Shutdown
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _install_signal_handlers() -> None:
    def _shutdown(sig: int, _frame: Any) -> None:
        print(f"\n[InventoryFlow] Signal {sig} received — shutting down…", flush=True)
        LOGGER.info("Shutdown signal %d — exiting.", sig)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    try:
        signal.signal(signal.SIGTERM, _shutdown)
    except (AttributeError, OSError):
        pass  # SIGTERM not available on Windows


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 3 — Startup Banner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║      📦  InventoryFlow — AI Inventory System  (v2)           ║
║            Single-Port Mode · FastAPI + Gradio               ║
╠══════════════════════════════════════════════════════════════╣
║  Environment  : {env:<46}║
║  🌐 One URL   : http://localhost:{port:<29}║
║                                                              ║
║  📱 Mobile UI : http://localhost:{port}/          {m_pad}║
║  🖥️  Dashboard : http://localhost:{port}/dashboard{d_pad}║
║  📋 API Docs  : http://localhost:{port}/docs      {a_pad}║
╚══════════════════════════════════════════════════════════════╝
"""

def _print_banner(env: str, port: int) -> None:
    p = str(port)
    banner = _BANNER.format(
        env=env,
        port=p,
        m_pad=" " * (10 - len(p)),
        d_pad=" " * (10 - len(p)),
        a_pad=" " * (10 - len(p)),
    )
    print(banner, flush=True)
    LOGGER.info("InventoryFlow started on port %d — env=%s", port, env)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 4 — Main (Single-Port Launcher)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main() -> None:
    _install_signal_handlers()

    env  = detect_environment()
    share = gradio_share_enabled()

    # ── Resolve single port ───────────────────────────────────────────────────
    raw = os.getenv("SERVER_PORT", os.getenv("MOBILE_API_PORT", ""))
    port = int(raw) if raw.isdigit() else find_free_port(8765)

    LOGGER.info("InventoryFlow starting — env=%s  port=%d", env, port)

    # ── Import FastAPI app (mobile_api.py) ────────────────────────────────────
    from mobile_api import app as fastapi_app  # noqa: PLC0415

    # ── Build Gradio UI ───────────────────────────────────────────────────────
    try:
        import gradio as gr  # noqa: PLC0415
        from ui import build_ui  # noqa: PLC0415
        gradio_blocks = build_ui()
    except Exception as exc:
        LOGGER.error("Gradio UI build failed: %s — running API-only mode.", exc)
        gradio_blocks = None

    # ── Mount Gradio into FastAPI at /dashboard ───────────────────────────────
    if gradio_blocks is not None:
        try:
            import gradio as gr  # noqa: PLC0415 (may already be imported above)
            fastapi_app = gr.mount_gradio_app(
                fastapi_app,
                gradio_blocks,
                path="/dashboard",
            )
            LOGGER.info("Gradio mounted at /dashboard ✓")
        except Exception as exc:
            LOGGER.error("Could not mount Gradio: %s — API still available.", exc)

    # ── Print startup banner ──────────────────────────────────────────────────
    _print_banner(env, port)

    # ── Launch single uvicorn server (blocks here) ────────────────────────────
    import uvicorn  # noqa: PLC0415

    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
