"""
app.py — InventoryFlow Main Entrypoint
======================================
Starts two servers concurrently:
  1.  FastAPI  / uvicorn  → Mobile UI + REST API   (default port 8765)
  2.  Gradio               → Desktop Dashboard       (default port 7860)

Usage
-----
    python app.py                        # local run
    GRADIO_SHARE=1 python app.py         # with public Gradio URL
    MOBILE_API_PORT=9000 python app.py   # custom API port

Environment Variables
---------------------
  GRADIO_SERVER_PORT   Preferred Gradio port   (default: 7860, auto-detects next free)
  MOBILE_API_PORT      Preferred API port      (default: 8765, auto-detects next free)
  GRADIO_SHARE         "1" to enable public URL (auto-enabled in Colab)
  INVENTORY_CURRENCY   Currency symbol          (default: INR)
  INVENTORY_SHEET_NAME Google Sheets doc name  (default: AI_Inventory_System)
"""

from __future__ import annotations

import os
import signal
import socket
import sys
import threading
import time
from typing import Any

# ── Import project config (sets up logger, creates dirs, etc.) ────────────────
from config import LOGGER, gradio_share_enabled


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 1 — Utilities
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _is_port_free(port: int, host: str = "0.0.0.0") -> bool:
    """Return True if *port* can be bound on *host*."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_free_port(start: int, end: int = 0) -> int:
    """
    Scan ports in [start, start+50] (or [start, end]) and return the first free one.
    Raises OSError if none found.
    """
    if end == 0:
        end = start + 50
    for port in range(start, end + 1):
        if _is_port_free(port):
            return port
    raise OSError(
        f"No free port found between {start} and {end}. "
        "Set GRADIO_SERVER_PORT / MOBILE_API_PORT to override."
    )


def wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 15.0) -> bool:
    """
    Poll until *port* on *host* is accepting connections (server is ready).
    Returns True on success, False on timeout.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                return True
            except (ConnectionRefusedError, TimeoutError, OSError):
                time.sleep(0.25)
    return False


def is_colab() -> bool:
    """Detect Google Colab environment."""
    return bool(
        os.getenv("COLAB_RELEASE_TAG")
        or os.getenv("COLAB_BACKEND_VERSION")
        or os.getenv("COLAB_GPU")
    )


def detect_environment() -> str:
    """Return a short label for the current runtime environment."""
    if is_colab():
        return "colab"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("darwin"):
        return "macos"
    return "linux"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 2 — Mobile API (FastAPI + uvicorn)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_api_thread: threading.Thread | None = None


def _run_mobile_api(port: int) -> None:
    """Target function for the mobile-API daemon thread."""
    try:
        import uvicorn
        from mobile_api import app as mobile_app  # noqa: PLC0415

        LOGGER.info("Mobile API  → http://0.0.0.0:%d  (docs: /docs)", port)
        uvicorn.run(
            mobile_app,
            host="0.0.0.0",
            port=port,
            log_level="warning",
            access_log=False,
        )
    except ImportError as exc:
        LOGGER.error("Mobile API import failed — is uvicorn installed? %s", exc)
    except Exception as exc:  # pragma: no cover
        LOGGER.error("Mobile API crashed: %s", exc)


def start_mobile_api(port: int) -> threading.Thread:
    """
    Spawn the FastAPI server in a background daemon thread and wait until
    the port is actually accepting connections before returning.
    """
    global _api_thread
    _api_thread = threading.Thread(
        target=_run_mobile_api,
        args=(port,),
        daemon=True,
        name="mobile-api",
    )
    _api_thread.start()

    if wait_for_port(port, timeout=15.0):
        LOGGER.info("Mobile API is ready on port %d ✓", port)
    else:
        LOGGER.warning(
            "Mobile API did not respond within 15 s on port %d — continuing anyway.", port
        )
    return _api_thread


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 3 — Gradio Dashboard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_gradio_app() -> Any | None:
    """Import and build the Gradio UI. Returns None on failure."""
    try:
        from ui import build_ui  # noqa: PLC0415
        return build_ui()
    except ImportError as exc:
        LOGGER.error("Cannot import ui.py: %s", exc)
    except Exception as exc:  # pragma: no cover
        LOGGER.error("Gradio UI build failed: %s", exc)
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 4 — Startup Banner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║         📦  InventoryFlow — AI Inventory System              ║
║              Powered by Gradio · FastAPI · Python            ║
╠══════════════════════════════════════════════════════════════╣
║  Environment  : {env:<46}║
║  Gradio UI    : http://localhost:{gradio_port:<29}║
║  Mobile UI    : http://localhost:{api_port:<29}║
║  API Docs     : http://localhost:{api_port}/docs{docs_pad}║
║  API Stats    : http://localhost:{api_port}/api/stats{stats_pad}║
║  Gradio Share : {share_status:<46}║
╚══════════════════════════════════════════════════════════════╝
"""

def _print_banner(env: str, gradio_port: int, api_port: int, share: bool) -> None:
    share_status = "enabled — public URL will appear below" if share else "disabled  (set GRADIO_SHARE=1 to enable)"
    docs_url   = f"http://localhost:{api_port}/docs"
    stats_url  = f"http://localhost:{api_port}/api/stats"

    banner = _BANNER.format(
        env=env,
        gradio_port=gradio_port,
        api_port=api_port,
        share_status=share_status,
        docs_pad=" " * (28 - len(str(api_port))),
        stats_pad=" " * (23 - len(str(api_port))),
    )
    print(banner, flush=True)
    LOGGER.info("Startup complete — Gradio=%d  MobileAPI=%d  Share=%s", gradio_port, api_port, share)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 5 — Graceful Shutdown
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _install_signal_handlers() -> None:
    """Install SIGINT / SIGTERM handlers for clean shutdown (Unix + Windows)."""
    def _shutdown(sig: int, _frame: Any) -> None:
        print(f"\n[InventoryFlow] Received signal {sig} — shutting down…", flush=True)
        LOGGER.info("Shutdown signal %d received — exiting.", sig)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    try:
        signal.signal(signal.SIGTERM, _shutdown)
    except (AttributeError, OSError):
        pass  # SIGTERM may not exist on Windows


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 6 — Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main() -> None:
    _install_signal_handlers()

    env = detect_environment()
    LOGGER.info("InventoryFlow starting — env=%s", env)

    # ── Resolve ports ─────────────────────────────────────────────────────────
    raw_api = os.getenv("MOBILE_API_PORT", "")
    api_port = int(raw_api) if raw_api.isdigit() else find_free_port(8765)
    os.environ["MOBILE_API_PORT"] = str(api_port)

    raw_gradio = os.getenv("GRADIO_SERVER_PORT", "")
    gradio_port = int(raw_gradio) if raw_gradio.isdigit() else find_free_port(7860)

    share = gradio_share_enabled()

    # ── Start Mobile API ──────────────────────────────────────────────────────
    start_mobile_api(api_port)

    # ── Build Gradio app ──────────────────────────────────────────────────────
    gradio_app = build_gradio_app()
    if gradio_app is None:
        LOGGER.critical("Gradio app could not be built — aborting.")
        sys.exit(1)

    # ── Print startup banner ──────────────────────────────────────────────────
    _print_banner(env, gradio_port, api_port, share)

    # ── Launch Gradio (blocks until stopped) ──────────────────────────────────
    import gradio as gr  # noqa: PLC0415 — deferred to speed up early imports
    gradio_app.launch(
        server_name="0.0.0.0",
        server_port=gradio_port,
        share=share,
        show_error=True,
        quiet=False,
        inbrowser=(env != "colab"),
    )


if __name__ == "__main__":
    main()
