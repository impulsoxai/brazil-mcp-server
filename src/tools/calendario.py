"""Módulo de calendário — feriados, dias úteis, prazos."""

import sys
from datetime import date, datetime, timedelta
from mcp.server.fastmcp import FastMCP

from src.utils import http_client
from src.utils.cache import get_cached, set_cached, TTL_FERIADOS
from src.config import BRASIL_API_BASE


def _parse_data(data_str: str) -> date | None:
    """Converte string de data para objeto date. Aceita YYYY-MM-DD ou DD/MM/YYYY."""
    data_str = data_str.strip()[:500]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return date.fromisoformat(data_str) if fmt == "%Y-%m-%d" else datetime.strptime(data_str, fmt).date()
        except ValueError:
            continue
    return None


def _formatar_data(d: date) -> str:
    """Formata data no padrão brasileiro DD/MM/YYYY."""
    return d.strftime("%d/%m/%Y")


async def _obter_feriados(ano: int) -> set[str]:
    """Obtém feriados nacionais do BrasilAPI. Usa cache de 24h."""
    cache_key = f"feriados:{ano}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        response = await http_client.get(f"{BRASIL_API_BASE}/feriados/v1/{ano}")
        response.raise_for_status()
        data = response.json()

        feriados = set()
        for feriado in data:
            dt = feriado.get("date", "")
            if dt:
                partes = dt.split("-")
                if len(partes) == 3:
                    feriados.add(f"{partes[1]}-{partes[2]}")

        set_cached(cache_key, feriados, TTL_FERIADOS)
        return feriados
    except Exception as e:
        print(f"Erro ao buscar feriados de {ano}: {e}", file=sys.stderr)
        return set()


def _eh_feriado(d: date, feriados: set[str]) -> bool:
    """Verifica se uma data é feriado."""
    mm_dd = f"{d.month:02d}-{d.day:02d}"
    return mm_dd in feriados


def _eh_dia_util(d: date, feriados: set[str]) -> bool:
    """Verifica se uma data é dia útil (não é fim de semana nem feriado)."""
    if d.weekday() >= 5:
        return False
    return not _eh_feriado(d, feriados)


async def _proximo_dia_util_interno(d: date, feriados: set[str]) -> date:
    """Encontra o próximo dia útil a partir de uma data (exclusivo)."""
    d = d + timedelta(days=1)
    while not _eh_dia_util(d, feriados):
        d += timedelta(days=1)
    return d


def register_tools(mcp: FastMCP) -> None:
    """Registra as ferramentas de calendário no servidor MCP."""

    @mcp.tool()
    async def listar_feriados_nacionais(ano: int) -> str:
        """
        Lista os feriados nacionais do Brasil para um determinado ano.

        Use quando precisar saber os feriados oficiais brasileiros.
        Consulta a BrasilAPI com cache de 24h.
        Aceita anos entre 2000 e 2100.
        """
        if ano < 2000 or ano > 2100:
            return (
                f"❌ Ano inválido: {ano}.\n"
                "Dica: informe um ano entre 2000 e 2100."
            )

        cache_key = f"feriados_raw:{ano}"
        cached = get_cached(cache_key)
        if cached is not None:
            data = cached
        else:
            try:
                response = await http_client.get(f"{BRASIL_API_BASE}/feriados/v1/{ano}")
                response.raise_for_status()
                data = response.json()
                set_cached(cache_key, data, TTL_FERIADOS)
            except Exception as e:
                print(f"Erro ao buscar feriados: {e}", file=sys.stderr)
                return (
                    "❌ Erro ao consultar feriados na BrasilAPI.\n"
                    "Dica: tente novamente em alguns segundos."
                )

        if not data:
            return f"❌ Nenhum feriado encontrado para o ano {ano}."

        linhas = []
        for feriado in data:
            nome = feriado.get("name", feriado.get("nome", ""))
            dt = feriado.get("date", "")
            if dt and nome:
                partes = dt.split("-")
                if len(partes) == 3:
                    dt_fmt = f"{partes[2]}/{partes[1]}/{partes[0]}"
                else:
                    dt_fmt = dt
                linhas.append(f"  • {dt_fmt} — {nome}")

        return (
            f"✅ Feriados nacionais de {ano} ({len(linhas)} feriados):\n"
            + "\n".join(linhas)
        )

    @mcp.tool()
    async def verificar_dia_util(data: str) -> str:
        """
        Verifica se uma data é dia útil no Brasil.

        Considera fins de semana e feriados nacionais.
        Aceita formato YYYY-MM-DD ou DD/MM/YYYY.
        """
        d = _parse_data(data)
        if d is None:
            return (
                f"❌ Data inválida: '{data}'.\n"
                "Dica: use o formato YYYY-MM-DD (ex: 2026-04-15) ou DD/MM/YYYY (ex: 15/04/2026)."
            )

        feriados = await _obter_feriados(d.year)
        data_fmt = _formatar_data(d)

        if _eh_dia_util(d, feriados):
            return f"✅ {data_fmt} é dia útil."
        elif d.weekday() >= 5:
            dia_semana = "Sábado" if d.weekday() == 5 else "Domingo"
            return f"✅ {data_fmt} NÃO é dia útil ({dia_semana})."
        else:
            return f"✅ {data_fmt} NÃO é dia útil (feriado)."

    @mcp.tool()
    async def calcular_prazo_util(data_inicio: str, dias_uteis: int) -> str:
        """
        Calcula a data final somando N dias úteis a uma data inicial.

        Use para calcular prazos bancários, vencimentos ou SLAs.
        Considera feriados nacionais e fins de semana.
        Aceita formato YYYY-MM-DD ou DD/MM/YYYY.
        Máximo: 3650 dias úteis (10 anos).
        """
        d = _parse_data(data_inicio)
        if d is None:
            return (
                f"❌ Data inválida: '{data_inicio}'.\n"
                "Dica: use o formato YYYY-MM-DD (ex: 2026-04-15) ou DD/MM/YYYY (ex: 15/04/2026)."
            )

        if dias_uteis < 0:
            return "❌ O número de dias úteis não pode ser negativo."

        if dias_uteis > 3650:
            return (
                f"❌ Limite excedido: {dias_uteis} dias úteis (máximo 3650).\n"
                "Dica: use um período de até 10 anos."
            )

        if dias_uteis == 0:
            return (
                f"✅ Prazo de 0 dias úteis.\n"
                f"Data inicial: {_formatar_data(d)}\n"
                f"Data final: {_formatar_data(d)}"
            )

        feriados = await _obter_feriados(d.year)
        if d.month >= 11:
            feriados_prox = await _obter_feriados(d.year + 1)
            feriados = feriados | feriados_prox

        contador = 0
        atual = d
        while contador < dias_uteis:
            atual += timedelta(days=1)
            if _eh_dia_util(atual, feriados):
                contador += 1

        return (
            f"✅ Prazo calculado:\n"
            f"Data inicial: {_formatar_data(d)}\n"
            f"Dias úteis: {dias_uteis}\n"
            f"Data final: {_formatar_data(atual)}"
        )

    @mcp.tool()
    async def proximo_dia_util(data: str) -> str:
        """
        Retorna o próximo dia útil a partir de uma data.

        Se a data for dia útil, retorna o dia útil seguinte.
        Considera feriados nacionais e fins de semana.
        Aceita formato YYYY-MM-DD ou DD/MM/YYYY.
        """
        d = _parse_data(data)
        if d is None:
            return (
                f"❌ Data inválida: '{data}'.\n"
                "Dica: use o formato YYYY-MM-DD (ex: 2026-04-15) ou DD/MM/YYYY (ex: 15/04/2026)."
            )

        feriados = await _obter_feriados(d.year)
        proximo = await _proximo_dia_util_interno(d, feriados)

        return (
            f"✅ Próximo dia útil:\n"
            f"Data informada: {_formatar_data(d)}\n"
            f"Próximo dia útil: {_formatar_data(proximo)}"
        )
