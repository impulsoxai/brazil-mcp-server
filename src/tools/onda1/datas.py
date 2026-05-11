"""Ferramentas de data — calcular_idade, formatar_data_br, calcular_diferenca_datas."""

from datetime import date, datetime, timedelta
from typing import Annotated
from pydantic import Field
from mcp.server.fastmcp import FastMCP


_DIAS_POR_MES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_NOMES_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
_NOMES_DIAS = ["segunda-feira", "terça-feira", "quarta-feira",
               "quinta-feira", "sexta-feira", "sábado", "domingo"]


def _parse_data(data_str: str) -> date:
    """Parse data em dd/mm/aaaa, aaaa-mm-dd, ou dd-mm-aaaa."""
    data_str = data_str.strip()

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(data_str, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Formato de data não reconhecido: {data_str}. Use dd/mm/aaaa, aaaa-mm-dd ou dd-mm-aaaa.")


def calcular_idade(data_nascimento: str) -> dict:
    """Calcula idade exata a partir de data de nascimento.

    Use para verificar faixa etária em clínicas, academias, atendimentos.
    Retorna anos, meses, dias e próximo aniversário.
    """
    try:
        nasc = _parse_data(data_nascimento)
    except ValueError as e:
        return {"erro": f"❌ Data inválida: {e}"}

    hoje = date.today()

    if nasc > hoje:
        return {"erro": f"❌ Data de nascimento no futuro: {data_nascimento}. Use uma data passada."}

    anos = hoje.year - nasc.year
    meses = hoje.month - nasc.month
    dias = hoje.day - nasc.day

    if dias < 0:
        meses -= 1
        prev_month = (hoje.month - 2) % 12
        dias += _DIAS_POR_MES[prev_month] + 1

    if meses < 0:
        anos -= 1
        meses += 12

    # Próximo aniversário
    proximo = date(hoje.year, nasc.month, nasc.day)
    if proximo < hoje:
        proximo = date(hoje.year + 1, nasc.month, nasc.day)

    return {
        "anos": anos,
        "meses": meses,
        "dias": dias,
        "proximo_aniversario": proximo.strftime("%d/%m/%Y")
    }


def formatar_data_br(data: str) -> dict:
    """Converte qualquer formato de data para dd/mm/aaaa.

    Use para garantir que o agente nunca mande data em formato americano.
    Retorna data formatada, dia da semana em PT-BR, e data por extenso.
    """
    try:
        d = _parse_data(data)
    except ValueError as e:
        return {"erro": f"❌ Data inválida: {e}"}

    dia_semana = _NOMES_DIAS[d.weekday()]
    data_formatada = d.strftime("%d/%m/%Y")
    extenso = f"{d.day} de {_NOMES_MESES[d.month - 1]} de {d.year}"

    return {
        "data_formatada": data_formatada,
        "dia_semana": dia_semana,
        "extenso": extenso
    }


def calcular_diferenca_datas(data_inicio: str, data_fim: str) -> dict:
    """Calcula diferença entre duas datas.

    Use para prazos de garantia, tempo desde último atendimento, vencimentos.
    Retorna dias, semanas, meses, anos e dias úteis (exclui fins de semana).
    """
    try:
        inicio = _parse_data(data_inicio)
        fim = _parse_data(data_fim)
    except ValueError as e:
        return {"erro": f"❌ Data inválida: {e}"}

    if fim < inicio:
        return {"erro": "❌ Data final é anterior à data inicial. data_fim deve ser >= data_inicio."}

    delta = fim - inicio
    dias = delta.days

    semanas = round(dias / 7, 1)
    meses = round(dias / 30.44, 1)
    anos = round(dias / 365.25, 1)

    # Dias úteis (exclui sábados e domingos)
    dias_uteis = sum(
        1 for i in range(dias + 1)
        if (inicio + timedelta(days=i)).weekday() < 5
    )

    return {
        "dias": dias,
        "semanas": semanas,
        "meses": meses,
        "anos": anos,
        "dias_uteis": dias_uteis
    }


def register_tools(mcp: FastMCP) -> None:
    """Registra ferramentas de data no servidor MCP."""

    @mcp.tool()
    async def calcular_idade_tool(data_nascimento: Annotated[str, Field(description="Data de nascimento (dd/mm/aaaa ou ISO)")]) -> str:
        """Calcula idade exata a partir de data de nascimento.

        Use para verificar faixa etária em clínicas, academias, atendimentos.
        """
        result = calcular_idade(data_nascimento)

        if "erro" in result:
            return result["erro"]

        return (
            f"✅ Idade calculada:\n"
            f"Anos: {result['anos']}\n"
            f"Meses: {result['meses']}\n"
            f"Dias: {result['dias']}\n"
            f"Próximo aniversário: {result['proximo_aniversario']}"
        )

    @mcp.tool()
    async def formatar_data_br_tool(data: Annotated[str, Field(description="Data para formatar (aceita ISO, americano, BR)")]) -> str:
        """Converte qualquer formato de data para dd/mm/aaaa.

        Use para garantir que o agente nunca mande data em formato americano.
        """
        result = formatar_data_br(data)

        if "erro" in result:
            return result["erro"]

        return (
            f"✅ Data formatada:\n"
            f"Formatada: {result['data_formatada']}\n"
            f"Dia da semana: {result['dia_semana']}\n"
            f"Extenso: {result['extenso']}"
        )

    @mcp.tool()
    async def calcular_diferenca_datas_tool(
        data_inicio: Annotated[str, Field(description="Data inicial (dd/mm/aaaa ou ISO)")],
        data_fim: Annotated[str, Field(description="Data final (dd/mm/aaaa ou ISO)")],
    ) -> str:
        """Calcula diferença entre duas datas.

        Use para prazos de garantia, vencimentos, tempo desde último atendimento.
        """
        result = calcular_diferenca_datas(data_inicio, data_fim)

        if "erro" in result:
            return result["erro"]

        return (
            f"✅ Diferença calculada:\n"
            f"Dias: {result['dias']}\n"
            f"Semanas: {result['semanas']}\n"
            f"Meses: {result['meses']}\n"
            f"Anos: {result['anos']}\n"
            f"Dias úteis: {result['dias_uteis']}"
        )