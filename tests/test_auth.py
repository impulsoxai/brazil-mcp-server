import pytest
from unittest.mock import patch, AsyncMock
from src.middleware.auth import verificar_autenticacao


@pytest.mark.asyncio
async def test_master_key_valid():
    with patch("src.middleware.auth.IMPULSOX_MASTER_KEY", "impulsox-master-abc123"):
        result = await verificar_autenticacao({"x-api-key": "impulsox-master-abc123"})
        assert result["valid"] is True
        assert result["scope"] == "master"


@pytest.mark.asyncio
async def test_master_key_no_rate_limit():
    with patch("src.middleware.auth.IMPULSOX_MASTER_KEY", "impulsox-master-abc123"):
        result = await verificar_autenticacao({"x-api-key": "impulsox-master-abc123"})
        assert result.get("skip_rate_limit") is True


@pytest.mark.asyncio
async def test_public_key_has_scope():
    with patch("src.middleware.auth.IMPULSOX_MASTER_KEY", "impulsox-master-abc123"), \
         patch("src.middleware.auth.usage") as mock_usage:
        mock_usage.validate_key = AsyncMock(return_value={"plan": "free", "scope": "public"})
        result = await verificar_autenticacao({"x-api-key": "free-abc123"})
        assert result["valid"] is True
        assert result["scope"] == "public"


@pytest.mark.asyncio
async def test_invalid_key():
    with patch("src.middleware.auth.IMPULSOX_MASTER_KEY", "impulsox-master-abc123"), \
         patch("src.middleware.auth.usage") as mock_usage:
        mock_usage.validate_key = AsyncMock(return_value=None)
        result = await verificar_autenticacao({"x-api-key": "invalid-key"})
        assert result["valid"] is False


@pytest.mark.asyncio
async def test_missing_key():
    result = await verificar_autenticacao({})
    assert result["valid"] is False
