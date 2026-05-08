import pytest
from src.services import database as usage


async def setup_function():
    await usage.init()
    # Note: direct dict manipulation removed — use DB for test setup


@pytest.mark.asyncio
async def test_create_key_default_scope():
    await usage.create_key("free-test123", "free")
    key_data = await usage.validate_key("free-test123")
    assert key_data["scope"] == "public"
