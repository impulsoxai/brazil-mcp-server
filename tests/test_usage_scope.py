import pytest
from src.services import database as usage


@pytest.mark.asyncio
async def test_create_key_default_scope():
    await usage.init_db()
    await usage.create_key("free-test123", "free")
    key_data = await usage.validate_key("free-test123")
    assert key_data["scope"] == "public"
