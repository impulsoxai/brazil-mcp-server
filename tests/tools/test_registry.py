import pytest
from src.tools.registry import ToolEntry, register, list_tools, clear_registry


def setup_function():
    clear_registry()


def test_register_public_tool():
    async def my_tool(): return "ok"
    register("my_tool", my_tool, scope="public")
    tools = list_tools("public")
    assert len(tools) == 1
    assert tools[0].name == "my_tool"
    assert tools[0].scope == "public"


def test_register_private_tool():
    async def my_tool(): return "ok"
    register("my_tool", my_tool, scope="private")
    tools = list_tools("public")
    assert len(tools) == 0


def test_master_sees_all():
    async def pub(): return "ok"
    async def priv(): return "ok"
    register("pub", pub, scope="public")
    register("priv", priv, scope="private")
    tools = list_tools("master")
    assert len(tools) == 2


def test_public_sees_only_public():
    async def pub(): return "ok"
    async def priv(): return "ok"
    register("pub", pub, scope="public")
    register("priv", priv, scope="private")
    tools = list_tools("public")
    assert len(tools) == 1
    assert tools[0].name == "pub"


def test_default_scope_is_public():
    async def my_tool(): return "ok"
    register("my_tool", my_tool)
    tools = list_tools("public")
    assert len(tools) == 1
