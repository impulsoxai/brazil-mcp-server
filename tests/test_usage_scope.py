import pytest
from unittest.mock import patch, AsyncMock
from src.middleware.auth import verificar_autenticacao


@pytest.mark.asyncio
async def test_create_key_default_scope():
    with patch("src.middleware.auth.IMPULSOX_MASTER_KEY", "impulsox-master-abc123"), \
         patch("src.middleware.auth.usage") as mock_usage:
        mock_usage.validate_key = AsyncMock(return_value={
            "plan": "free", "scope": "public", "usage": 0,
            "reset_date": "2099-01-01T00:00:00+00:00", "status": "active",
        })
        result = await verificar_autenticacao({"x-api-key": "free-test123"})
        assert result["valid"] is True
        assert result["scope"] == "public"
