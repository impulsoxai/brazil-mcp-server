import pytest
from src.services import usage


def setup_function():
    usage.init()
    usage._keys.clear()
    usage.reset_windows()


def test_create_key_default_scope():
    usage.create_key("free-test123", "free")
    key_data = usage.validate_key("free-test123")
    assert key_data["scope"] == "public"


def test_existing_key_without_scope():
    """Keys existentes sem campo scope devem retornar 'public' via .get()."""
    usage._keys["old-key"] = {"plan": "free", "usage": 0}
    key_data = usage.validate_key("old-key")
    assert key_data.get("scope", "public") == "public"
