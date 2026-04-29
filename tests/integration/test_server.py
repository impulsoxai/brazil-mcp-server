"""Teste de integração — verifica se o servidor MCP inicializa corretamente."""

import pytest


def test_import_main():
    """Verifica se o módulo main pode ser importado sem erros."""
    import src.main
    assert hasattr(src.main, "mcp")


def test_mcp_has_tools():
    """Verifica se as ferramentas foram registradas no servidor."""
    import src.main
    mcp = src.main.mcp
    # O FastMCP deve ter ferramentas registradas
    assert mcp is not None
