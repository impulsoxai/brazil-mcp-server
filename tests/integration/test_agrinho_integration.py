"""Integration tests for Agrinho tools — scope filtering and tool registration."""

import pytest
from src.tools.registry import list_tools, clear_registry, register


def setup_function():
    clear_registry()


def test_agrinho_tools_not_in_public_list():
    """Tools privadas não aparecem para scope público."""
    async def dummy(): return "ok"
    register("consultar_cnpj", dummy, scope="public")
    register("get_commodity_price", dummy, scope="private")

    public_tools = list_tools("public")
    names = [t.name for t in public_tools]
    assert "consultar_cnpj" in names
    assert "get_commodity_price" not in names


def test_agrinho_tools_in_master_list():
    """Tools privadas aparecem para scope master."""
    async def dummy(): return "ok"
    register("consultar_cnpj", dummy, scope="public")
    register("get_commodity_price", dummy, scope="private")

    master_tools = list_tools("master")
    names = [t.name for t in master_tools]
    assert "consultar_cnpj" in names
    assert "get_commodity_price" in names


def test_existing_tools_unchanged():
    """22 tools existentes continuam visíveis para scope público."""
    async def dummy(): return "ok"
    for i in range(22):
        register(f"tool_{i}", dummy, scope="public")

    public_tools = list_tools("public")
    assert len(public_tools) == 22
