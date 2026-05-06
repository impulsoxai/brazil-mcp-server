import pytest
from unittest.mock import patch
from src.middleware.auth import verificar_autenticacao


def test_master_key_valid():
    with patch("src.middleware.auth.IMPULSOX_MASTER_KEY", "impulsox-master-abc123"):
        result = verificar_autenticacao({"x-api-key": "impulsox-master-abc123"})
        assert result["valid"] is True
        assert result["scope"] == "master"


def test_master_key_no_rate_limit():
    with patch("src.middleware.auth.IMPULSOX_MASTER_KEY", "impulsox-master-abc123"):
        result = verificar_autenticacao({"x-api-key": "impulsox-master-abc123"})
        assert result.get("skip_rate_limit") is True


def test_public_key_has_scope():
    with patch("src.middleware.auth.IMPULSOX_MASTER_KEY", "impulsox-master-abc123"), \
         patch("src.middleware.auth.usage") as mock_usage:
        mock_usage.validate_key.return_value = {"plan": "free", "scope": "public"}
        result = verificar_autenticacao({"x-api-key": "free-abc123"})
        assert result["valid"] is True
        assert result["scope"] == "public"


def test_invalid_key():
    with patch("src.middleware.auth.IMPULSOX_MASTER_KEY", "impulsox-master-abc123"), \
         patch("src.middleware.auth.usage") as mock_usage:
        mock_usage.validate_key.return_value = None
        result = verificar_autenticacao({"x-api-key": "invalid-key"})
        assert result["valid"] is False


def test_missing_key():
    result = verificar_autenticacao({})
    assert result["valid"] is False
