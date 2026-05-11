"""Onda 1 — Ferramentas de lógica pura (scope public)."""

from src.tools.onda1.mensagem import register_tools as register_mensagem
from src.tools.onda1.calculos import register_tools as register_calculos
from src.tools.onda1.datas import register_tools as register_datas
from src.tools.onda1.validacao import register_tools as register_validacao


def register_tools(mcp) -> None:
    """Registra todas as ferramentas da Onda 1 no servidor MCP."""
    register_mensagem(mcp)
    register_calculos(mcp)
    register_datas(mcp)
    register_validacao(mcp)
