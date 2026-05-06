"""Módulo Agrinho — ferramentas agrícolas privadas."""

import re
import sys
from typing import Annotated

from pydantic import Field
from mcp.server.fastmcp import FastMCP

from src.utils import http_client
from src.utils.cache import get_cached, set_cached, TTL_COMMODITY, TTL_WEATHER_FORECAST, TTL_WEATHER_ALERT
from src.utils.ibge import resolver_codigo_ibge, resolver_lat_lon

# Commodities suportadas na Fase 1
COMMODITIES_SUPORTADAS = {
    "soja": {"unidade": "saca (60kg)"},
    "milho": {"unidade": "saca (60kg)"},
    "boi_gordo": {"unidade": "arroba"},
    "cafe_arabica": {"unidade": "saca (60kg)"},
    "arroz": {"unidade": "saca (50kg)"},
    "feijao": {"unidade": "saca (60kg)"},
    "trigo": {"unidade": "saca (60kg)"},
}


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
        café, arroz, feijão ou trigo. Dados do CEPEA/ESALQ com fallback
        para CONAB. Cache de 4 horas.

        Exemplos: "quanto tá a soja?", "preço do milho hoje", "quanto vale o arroz?"
        """
        commodity_lower = commodity.strip().lower().replace(" ", "_")

        if commodity_lower not in COMMODITIES_SUPORTADAS:
            lista = ", ".join(COMMODITIES_SUPORTADAS.keys())
            return (
                f"Commodity '{commodity}' não suportada.\n"
                f"Dica: commodities disponíveis: {lista}"
            )

        info = COMMODITIES_SUPORTADAS[commodity_lower]

        # Cache check
        cache_key = f"commodity:{commodity_lower}:{estado or 'nacional'}"
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

        # Tentar CEPEA via scraping HTTP
        try:
            cepea_url = f"https://www.cepea.esalq.usp.br/indicador/{commodity_lower}.aspx"
            response = await http_client.get(cepea_url)
            response.raise_for_status()
            html = response.text

            # Parse simples do HTML CEPEA — extrair preço do indicador
            # CEPEA mostra preço em tabela com classe "indicador"
            # Buscar padrão de preço: R$ X.XXX,XX ou X.XXX,XX
            preco_match = re.search(r'R\$\s*([\d.,]+)', html)
            if preco_match:
                preco_str = preco_match.group(1).replace(".", "").replace(",", ".")
                preco = float(preco_str)

                result = (
                    f"{commodity.replace('_', ' ').title()} — R$ {preco:,.2f}/{info['unidade']}\n"
                    f"Fonte: CEPEA/ESALQ\n"
                    f"Nota: preço de referência, consulte cepea.esalq.usp.br para cotação exata"
                )
                set_cached(cache_key, result, TTL_COMMODITY)
                return result
        except Exception as e:
            print(f"[AGRINHO] CEPEA falhou para {commodity}: {e}", file=sys.stderr)

        # Fallback CONAB
        try:
            url = f"https://dados.gov.br/dados/api/publico/conab/precos/{commodity_lower}"
            response = await http_client.get(url)
            response.raise_for_status()
            data = response.json()

            if data:
                ultimo = data[-1] if isinstance(data, list) else data
                preco = ultimo.get("preco", ultimo.get("valor"))
                data_ref = ultimo.get("data", ultimo.get("referencia", ""))

                result = (
                    f"{commodity.replace('_', ' ').title()} — R$ {preco:,.2f}/{info['unidade']}\n"
                    f"Fonte: CONAB — {data_ref}\n"
                    f"Nota: dados CONAB podem ter atraso de alguns dias"
                )
                set_cached(cache_key, result, TTL_COMMODITY)
                return result
        except Exception as e:
            print(f"[AGRINHO] CONAB falhou para {commodity}: {e}", file=sys.stderr)

        return (
            f"Não foi possível obter preço de {commodity.replace('_', ' ').title()}.\n"
            "Dica: tente novamente em alguns minutos ou consulte CEPEA (cepea.esalq.usp.br)."
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
            response = await http_client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return (
                f"Serviço do INMET indisponível no momento.\n"
                "Dica: tente novamente em alguns minutos."
            )

        ibge_str = str(ibge_code)
        if ibge_str not in data:
            return (
                f"Dados de previsão não disponíveis para {municipio}.\n"
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
            lat, lon = await resolver_lat_lon(ibge_code)
        except ValueError as e:
            return str(e)

        try:
            url = f"https://apiprevmet3.inmet.gov.br/alerta/grade/{lat}/{lon}"
            response = await http_client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return (
                f"Serviço de alertas do INMET indisponível.\n"
                "Dica: tente novamente em alguns minutos."
            )

        if not data:
            result = (
                f"Nenhum alerta meteorológico ativo para {municipio.title()}.\n"
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

        linhas = [f"Alerta para {municipio.title()}:\n"]

        for alerta in (data if isinstance(data, list) else [data]):
            sev = alerta.get("severidade", alerta.get("severity", "amarelo")).lower()
            icone = severidade_cores.get(sev, "⚠️")
            tipo = alerta.get("tipo", alerta.get("event", "Alerta"))
            descricao = alerta.get("descricao", alerta.get("description", ""))
            inicio = alerta.get("inicio", alerta.get("onset", ""))
            fim = alerta.get("fim", alerta.get("expires", ""))

            linhas.append(f"{icone} ALERTA {sev.upper()} — {tipo.title()}")
            if inicio or fim:
                linhas.append(f"Período: {inicio} até {fim}")
            if descricao:
                linhas.append(f"Descrição: {descricao}")
            linhas.append("")

        linhas.append("Fonte: INMET")
        result = "\n".join(linhas)
        set_cached(cache_key, result, TTL_WEATHER_ALERT)
        return result
