import os
import pytest
from app.config import get_settings


@pytest.fixture(autouse=True)
def mock_env_for_testing(monkeypatch):
    """Ensure standard Gemini SDK mode is active during unit tests by default."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyDummyKeyForTesting1234567890")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
