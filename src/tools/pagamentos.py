"""Módulo de pagamentos — PIX, juros, financeiro.

Sprint 2 — Ferramentas planejadas:
- gerar_pix_copia_cola(chave, valor, nome, cidade) — payload PIX estático
- validar_chave_pix(chave) — valida tipo e formato da chave PIX
- calcular_juros_simples(principal, taxa, dias) — juros simples
- calcular_juros_compostos(principal, taxa, periodos) — juros compostos
- calcular_multa_atraso(valor, dias_atraso) — multa 2% + juros 1%/mês padrão BR
"""

from mcp.server.fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Registra as ferramentas de pagamentos no servidor MCP.

    Sprint 2 — implementação futura.
    """
    pass
