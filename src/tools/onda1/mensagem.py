"""Ferramentas de mensagem WhatsApp — formatar e gerar link."""

from urllib.parse import quote
from typing import Annotated
from pydantic import Field
from mcp.server.fastmcp import FastMCP


def formatar_mensagem_whatsapp(
    texto: Annotated[str, Field(description="Texto da mensagem")],
    negrito: Annotated[bool, Field(description="Negrito", default=False)] = False,
    italico: Annotated[bool, Field(description="Itálico", default=False)] = False,
    itens: Annotated[str | None, Field(description="Lista com marcadores (string separada por vírgula)", default=None)] = None,
) -> str:
    """Formata texto para WhatsApp com markdown correto.

    Use para formatar respostas do agente antes de enviar no WhatsApp.
    Suporta: *negrito*, _itálico_, - lista.
    """
    resultado = texto

    if isinstance(itens, str) and itens:
        itens = [i.strip() for i in itens.split(',')]

    if negrito:
        resultado = f"*{resultado}*"

    if italico:
        resultado = f"_{resultado}_"

    if itens:
        linhas = ["- " + item for item in itens]
        resultado = (resultado + "\n" + "\n".join(linhas)) if resultado else "\n".join(linhas)

    return resultado


def gerar_link_whatsapp(
    telefone: Annotated[str, Field(description="Telefone com DDI (ex: 5548999123456)")],
    mensagem: Annotated[str, Field(description="Mensagem opcional", default="")] = "",
) -> str:
    """Gera link wa.me com mensagem pré-preenchida.

    Use quando o agente precisa indicar um número de WhatsApp para contato.
    Ex: gerar_link_whatsapp("5548999123456", "Olá") → https://wa.me/5548999123456?text=Ola%21
    """
    numeros = "".join(c for c in telefone if c.isdigit())

    if not numeros:
        return "❌ Telefone vazio. Informe o número com DDI (ex: 5548999123456)."

    if not numeros.startswith("55"):
        numeros = "55" + numeros.lstrip("0")

    base = f"https://wa.me/{numeros}"

    if mensagem:
        encoded = quote(mensagem, safe="")
        base += f"?text={encoded}"

    return base


def register_tools(mcp: FastMCP) -> None:
    """Registra ferramentas de mensagem WhatsApp no servidor MCP."""

    @mcp.tool()
    async def formatar_mensagem_whatsapp_tool(
        texto: Annotated[str, Field(description="Texto da mensagem")],
        negrito: Annotated[bool, Field(description="Negrito", default=False)] = False,
        italico: Annotated[bool, Field(description="Itálico", default=False)] = False,
        itens: Annotated[str | None, Field(description="Lista com marcadores (string separada por vírgula)", default=None)] = None,
    ) -> str:
        """Formata texto para WhatsApp com markdown correto.

        Use para formatar respostas do agente antes de enviar no WhatsApp.
        """
        result = formatar_mensagem_whatsapp(texto, negrito, italico, itens)
        return f"✅ Mensagem formatada:\n{result}"

    @mcp.tool()
    async def gerar_link_whatsapp_tool(
        telefone: Annotated[str, Field(description="Telefone com DDI (ex: 5548999123456)")],
        mensagem: Annotated[str, Field(description="Mensagem opcional", default="")] = "",
    ) -> str:
        """Gera link wa.me com mensagem pré-preenchida.

        Use quando o agente precisa indicar um número de WhatsApp para contato.
        """
        result = gerar_link_whatsapp(telefone, mensagem)
        if result.startswith("❌"):
            return result
        return f"✅ Link gerado:\n{result}"