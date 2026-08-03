import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_config(monkeypatch, **environment):
    for key in ("COLAB_RELEASE_TAG", "GRADIO_SHARE"):
        monkeypatch.delenv(key, raising=False)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    import config

    return importlib.reload(config)


def test_gradio_sharing_defaults_to_colab_only(monkeypatch):
    config = load_config(monkeypatch, COLAB_RELEASE_TAG="release")
    assert config.CONFIG.colab is True
    assert config.gradio_share_enabled() is True

    config = load_config(monkeypatch)
    assert config.CONFIG.colab is False
    assert config.gradio_share_enabled() is False


def test_gradio_sharing_can_be_overridden(monkeypatch):
    config = load_config(monkeypatch, GRADIO_SHARE="false")
    assert config.gradio_share_enabled() is False

    config = load_config(monkeypatch, GRADIO_SHARE="yes")
    assert config.gradio_share_enabled() is True


def test_colab_initialization_is_skipped_without_notebook_kernel(monkeypatch):
    config = load_config(monkeypatch, COLAB_RELEASE_TAG="release")
    assert config.running_in_notebook_kernel() is False
    assert config.CONFIG.drive_mounted is False