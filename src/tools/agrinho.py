"""Módulo Agrinho — ferramentas agrícolas privadas."""

import json
import sys
from datetime import date
from typing import Annotated

from src.scope import register_tool_scope


def _ponto_no_poligono(lat: float, lon: float, poligono: list[list[float]]) -> bool:
    """Ray-casting: verifica se ponto está dentro do polígono."""
    n = len(poligono)
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = poligono[i][1], poligono[i][0]
        yj, xj = poligono[j][1], poligono[j][0]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

from pydantic import Field
from mcp.server.fastmcp import FastMCP

from src.services.database import get_commodity_cache
from src.utils import http_client
from src.utils.cache import get_cached, set_cached, TTL_COMMODITY, TTL_WEATHER_FORECAST, TTL_WEATHER_ALERT
from src.utils.ibge import resolver_codigo_ibge, resolver_lat_lon

# Commodities suportadas
COMMODITIES_SUPORTADAS = {
    "soja": {"unidade": "saca (60kg)"},
    "milho": {"unidade": "saca (60kg)"},
    "boi_gordo": {"unidade": "arroba"},
    "cafe_arabica": {"unidade": "saca (60kg)"},
    "arroz": {"unidade": "saca (50kg)"},
    "feijao": {"unidade": "saca (60kg)"},
    "trigo": {"unidade": "saca (60kg)"},
}

# Aliases — variações comuns que o agente pode enviar
COMMODITY_ALIASES = {
    "cafe": "cafe_arabica",
    "café": "cafe_arabica",
    "boi": "boi_gordo",
}

# Cache PostgreSQL: all commodities via CEPEA scraper (daily at 18:30)
PG_CACHE_COMMODITIES = {"arroz", "feijao", "soja", "milho", "trigo", "cafe_arabica", "boi_gordo"}


def register_tools(mcp: FastMCP) -> None:
    """Registra as ferramentas agrícolas do Agrinho."""

    @mcp.tool()
    async def get_commodity_price(
        commodity: Annotated[str, Field(description="Nome da commodity: soja, milho, boi_gordo, cafe_arabica, arroz, feijao, trigo")],
        estado: Annotated[str, Field(description="Estado para preço regional (opcional, ex: 'PR', 'SC', 'RS')")] = "",
    ) -> str:
        """
        Consulta preço atual de commodities agrícolas brasileiras.

        Use quando o agricultor perguntar preço de soja, milho, boi gordo,
        café, arroz, feijão ou trigo.

        Fonte: CEPEA/ESALQ via scraper diário (cache PostgreSQL, atualizado 18:30).
        Preços em R$ — soja/milho/trigo/café por saca 60kg, arroz por saca 50kg,
        boi gordo por arroba.

        Exemplos: "quanto tá a soja?", "preço do milho hoje", "quanto vale o arroz?"
        """
        # 1. Normalizar + resolver aliases
        commodity_lower = commodity.strip().lower().replace(" ", "_")
        commodity_lower = COMMODITY_ALIASES.get(commodity_lower, commodity_lower)

        if commodity_lower not in COMMODITIES_SUPORTADAS:
            lista = ", ".join(COMMODITIES_SUPORTADAS.keys())
            return (
                f"❌ Commodity '{commodity}' não suportada.\n"
                f"Dica: commodities disponíveis: {lista}"
            )

        info = COMMODITIES_SUPORTADAS[commodity_lower]

        # 2. Cache in-memory check (TTL 4h)
        cache_key = f"commodity:{commodity_lower}"
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

        # 3. PostgreSQL cache — CEPEA scraper (all commodities)
        pg_cache = await get_commodity_cache(commodity_lower)
        if pg_cache and pg_cache["preco"] > 0:
            nome = commodity_lower.replace("_", " ").title()
            preco = pg_cache["preco"]
            fonte = pg_cache["fonte"]
            data_ref = pg_cache["data_referencia"]
            scraped_at = pg_cache["scraped_at"]

            # Verificar idade do cache
            try:
                scraped_date = date.fromisoformat(scraped_at[:10])
                age_days = (date.today() - scraped_date).days
            except (ValueError, TypeError):
                age_days = 0

            aviso = ""
            if age_days > 2:
                aviso = f"\n⚠️ Preço pode estar desatualizado (última atualização: {data_ref}, há {age_days} dias)"

            result = (
                f"✅ {nome} — R$ {preco:,.2f}/{info['unidade']}\n"
                f"Fonte: {fonte} — referência {data_ref}{aviso}"
            )
            set_cached(cache_key, result, TTL_COMMODITY)
            return result

        # 4. Erro informativo
        nome = commodity_lower.replace("_", " ").title()
        return (
            f"❌ Não foi possível obter preço de {nome}.\n"
            "Dica: tente novamente em alguns minutos ou consulte CEPEA (cepea.org.br)."
        )

    @mcp.tool()
    async def get_weather_forecast(
        municipio: Annotated[str, Field(description="Nome do município (ex: 'Chapecó', 'São Paulo', 'Ribeirão Preto')")],
    ) -> str:
        """
        Consulta previsão do tempo para 3 dias em um município brasileiro.

        Use quando o agricultor perguntar sobre clima, tempo, previsão,
        se vai chover, temperatura. Dados do INMET. Cache de 3 horas.

        Exemplos: "como vai ser o tempo em Chapecó?", "vai chover amanhã?"
        """
        cache_key = f"forecast:{municipio.strip().lower()}"
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            ibge_code = await resolver_codigo_ibge(municipio)
        except ValueError as e:
            return str(e)

        try:
            url = f"https://apiprevmet3.inmet.gov.br/previsao/{ibge_code}"
            headers = {"User-Agent": "BrazilMCPServer/1.0"}
            response = await http_client.get(url, headers=headers)
            response.raise_for_status()
            try:
                data = response.json()
            except UnicodeDecodeError:
                data = json.loads(response.content.decode("latin-1"))
        except Exception as e:
            print(f"[AGRINHO] INMET forecast falhou para {municipio} (IBGE {ibge_code}): {e}", file=sys.stderr)
            return (
                f"❌ Serviço do INMET indisponível no momento.\n"
                "Dica: tente novamente em alguns minutos."
            )

        ibge_str = str(ibge_code)
        if ibge_str not in data:
            return (
                f"❌ Dados de previsão não disponíveis para {municipio}.\n"
                "Dica: verifique o nome do município."
            )

        previsao = data[ibge_str]
        periodos = {"manha": "Manhã", "tarde": "Tarde", "noite": "Noite"}

        linhas = [f"Previsão para {municipio.title()} — próximos 3 dias:\n"]

        for i, (data_str, dados_dia) in enumerate(previsao.items()):
            if i >= 3:
                break
            label = "Hoje" if i == 0 else "Amanhã" if i == 1 else data_str
            linhas.append(f"{label} ({data_str}):")

            for periodo_key, periodo_label in periodos.items():
                p = dados_dia.get(periodo_key, {})
                if p:
                    temp_max = p.get("temp_max", "?")
                    temp_min = p.get("temp_min", "?")
                    resumo = p.get("resumo", "")
                    vento = p.get("int_vento", "")
                    direcao = p.get("dir_vento", "")
                    umid_max = p.get("umidade_max", "?")
                    umid_min = p.get("umidade_min", "?")
                    linhas.append(
                        f"  {periodo_label}: {resumo}, máx {temp_max}°C, mín {temp_min}°C"
                    )
                    if vento:
                        linhas.append(f"    Vento: {vento} {direcao}")
                    linhas.append(f"    Umidade: {umid_min}% a {umid_max}%")
            linhas.append("")

        linhas.append("Fonte: INMET")
        result = "\n".join(linhas)
        set_cached(cache_key, result, TTL_WEATHER_FORECAST)
        return result

    @mcp.tool()
    async def get_weather_alert(
        municipio: Annotated[str, Field(description="Nome do município (ex: 'Chapecó', 'São Paulo', 'Ribeirão Preto')")],
    ) -> str:
        """
        Consulta alertas meteorológicos ativos para um município.

        Use quando o agricultor perguntar sobre alertas de geada, seca,
        chuva forte, granizo ou calor extremo. Dados do INMET.
        Cache de 30 minutos.

        Exemplos: "tem alerta de geada?", "tem chuva forte prevista?", "vai ter seca?"
        """
        cache_key = f"alert:{municipio.strip().lower()}"
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            ibge_code = await resolver_codigo_ibge(municipio)
            lat, lon = await resolver_lat_lon(ibge_code, municipio)
        except ValueError as e:
            return str(e)

        try:
            url = "https://apiprevmet3.inmet.gov.br/avisos/ativos"
            headers = {"User-Agent": "BrazilMCPServer/1.0"}
            response = await http_client.get(url, headers=headers)
            response.raise_for_status()
            try:
                data = response.json()
            except UnicodeDecodeError:
                data = json.loads(response.content.decode("latin-1"))
        except Exception as e:
            print(f"[AGRINHO] INMET alert falhou para {municipio}: {e}", file=sys.stderr)
            return (
                f"❌ Serviço de alertas do INMET indisponível.\n"
                "Dica: tente novamente em alguns minutos."
            )

        # Filtrar alertas que cobrem o município (point-in-polygon)
        alertas_do_municipio = []
        for periodo in ("hoje", "futuro"):
            for alerta in data.get(periodo, []):
                try:
                    poligono_raw = alerta.get("poligono", "")
                    if not poligono_raw:
                        continue
                    poligono = json.loads(poligono_raw)
                    coords = poligono.get("coordinates", [[]])[0]
                    if coords and _ponto_no_poligono(lat, lon, coords):
                        alerta["_periodo"] = periodo
                        alertas_do_municipio.append(alerta)
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

        if not alertas_do_municipio:
            result = (
                f"✅ Nenhum alerta meteorológico ativo para {municipio.title()}.\n"
                "Fonte: INMET"
            )
            set_cached(cache_key, result, TTL_WEATHER_ALERT)
            return result

        severidade_cores = {
            "verde": "🟢",
            "amarelo": "🟡",
            "laranja": "🟠",
            "vermelho": "🔴",
        }

        linhas = [f"⚠️ Alertas para {municipio.title()}:\n"]

        for alerta in alertas_do_municipio:
            periodo = "Hoje" if alerta["_periodo"] == "hoje" else "Previsto"
            inicio = alerta.get("data_inicio", "")[:10]
            fim = alerta.get("data_fim", "")[:10]
            descricao = alerta.get("referencia", "")

            linhas.append(f"⚠️ ALERTA — {periodo}")
            if inicio or fim:
                linhas.append(f"Período: {inicio} até {fim}")
            if descricao:
                linhas.append(f"Descrição: {descricao}")
            linhas.append("")

        linhas.append("Fonte: INMET")
        result = "\n".join(linhas)
        set_cached(cache_key, result, TTL_WEATHER_ALERT)
        return result

    # Register scope for premium tools
    register_tool_scope("get_commodity_price", "premium_t2")
    register_tool_scope("get_weather_forecast", "premium_t2")
    register_tool_scope("get_weather_alert", "premium_t2")
