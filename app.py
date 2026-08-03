from __future__ import annotations

import os
import socket
import sys
import threading
from typing import Any

import gradio as gr
from config import LOGGER, gradio_share_enabled


# ── Mobile API (FastAPI) background starter ───────────────────────────────────
def _start_mobile_api() -> None:
    """
    Launch the FastAPI mobile REST server in a daemon thread so it runs
    alongside the Gradio process without blocking it.
    """
    try:
        import uvicorn
        from mobile_api import app as mobile_app  # noqa: PLC0415

        port = int(os.getenv("MOBILE_API_PORT", "8765"))
        LOGGER.info("Mobile API  → http://0.0.0.0:%d   (docs: /docs)", port)
        uvicorn.run(
            mobile_app,
            host="0.0.0.0",
            port=port,
            log_level="warning",   # keep terminal tidy; Gradio logs are verbose
        )
    except Exception as exc:  # pragma: no cover
        LOGGER.error("Mobile API failed to start: %s", exc)


# ── Gradio app builder ────────────────────────────────────────────────────────
def build_app() -> Any:
    try:
        from ui import build_ui
    except Exception as exc:  # pragma: no cover
        LOGGER.warning("UI initialization failed: %s", exc)
        return None
    return build_ui()


def find_available_port(start_port: int = 7860, max_port: int = 7910) -> int:
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise OSError("No free port available")


def find_available_api_port(start_port: int = 8765, max_port: int = 8800) -> int:
    """Find a free port for the mobile API server."""
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise OSError("No free API port available")


# ── Detect environment ────────────────────────────────────────────────────────
def is_colab() -> bool:
    """Detect if running in Google Colab."""
    return bool(os.getenv("COLAB_RELEASE_TAG") or os.getenv("COLAB_BACKEND_VERSION"))


def detect_environment() -> str:
    """Return a string describing the runtime environment."""
    if is_colab():
        return "colab"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("darwin"):
        return "macos"
    return "linux"


# ── Main entrypoint ───────────────────────────────────────────────────────────
def main() -> None:
    env = detect_environment()
    LOGGER.info("Environment detected: %s", env)

    # ── Step 1: Determine ports ───────────────────────────────────────────────
    # Mobile API port: respect MOBILE_API_PORT env var, auto-detect if busy
    preferred_api_port = os.getenv("MOBILE_API_PORT")
    if preferred_api_port and preferred_api_port.isdigit():
        api_port = int(preferred_api_port)
    else:
        api_port = find_available_api_port(8765)
    os.environ["MOBILE_API_PORT"] = str(api_port)

    # Gradio port: respect GRADIO_SERVER_PORT env var, auto-detect if busy
    preferred_gradio_port = os.getenv("GRADIO_SERVER_PORT")
    if preferred_gradio_port and preferred_gradio_port.isdigit():
        server_port = int(preferred_gradio_port)
    else:
        server_port = find_available_port(7860)

    # ── Step 2: Start Mobile API server in background thread ─────────────────
    api_thread = threading.Thread(
        target=_start_mobile_api,
        daemon=True,          # exits automatically when main process exits
        name="mobile-api",
    )
    api_thread.start()
    LOGGER.info("Mobile API thread started on port %d", api_port)

    # ── Step 3: Build and launch Gradio ──────────────────────────────────────
    app = build_app()
    if app is None:
        LOGGER.error("Unable to initialize the Gradio app; exiting.")
        sys.exit(1)

    share = gradio_share_enabled()
    inbrowser = env != "colab"  # Don't open browser automatically in Colab

    # ── Startup summary ───────────────────────────────────────────────────────
    LOGGER.info("=" * 60)
    LOGGER.info("  InventoryFlow — Starting up")
    LOGGER.info("  Environment      : %s", env)
    LOGGER.info("  Gradio dashboard : http://localhost:%d", server_port)
    LOGGER.info("  Gradio dashboard : http://127.0.0.1:%d", server_port)
    LOGGER.info("  Mobile UI        : http://localhost:%d", api_port)
    LOGGER.info("  Mobile API docs  : http://localhost:%d/docs", api_port)
    LOGGER.info("  Mobile API redoc : http://localhost:%d/redoc", api_port)
    LOGGER.info("  API Stats        : http://localhost:%d/api/stats", api_port)
    LOGGER.info("  API Products     : http://localhost:%d/api/products", api_port)
    if share:
        LOGGER.info("  Gradio share     : enabled — public URL will appear below")
    LOGGER.info("=" * 60)

    import gradio as gr  # noqa: PLC0415
    app.launch(
        server_name="0.0.0.0",
        server_port=server_port,
        share=share,
        show_error=True,
        quiet=False,
        inbrowser=inbrowser,
    )


if __name__ == "__main__":
    main()
