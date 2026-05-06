"""Testes para o módulo Agrinho — ferramentas agrícolas privadas."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.tools.agrinho import register_tools, COMMODITIES_SUPORTADAS


@pytest.fixture
def mcp_mock():
    """Create a mock FastMCP that captures registered tools."""
    mock = MagicMock()
    mock._tools = {}

    def tool_decorator():
        def decorator(fn):
            mock._tools[fn.__name__] = fn
            return fn
        return decorator

    mock.tool = tool_decorator
    return mock


# ── Commodities list ───────────────────────────────────────

def test_commodities_fase1():
    """7 commodities Fase 1."""
    assert len(COMMODITIES_SUPORTADAS) == 7
    assert "soja" in COMMODITIES_SUPORTADAS
    assert "milho" in COMMODITIES_SUPORTADAS
    assert "boi_gordo" in COMMODITIES_SUPORTADAS
    assert "cafe_arabica" in COMMODITIES_SUPORTADAS
    assert "arroz" in COMMODITIES_SUPORTADAS
    assert "feijao" in COMMODITIES_SUPORTADAS
    assert "trigo" in COMMODITIES_SUPORTADAS


def test_commodidades_tem_unidade():
    """Toda commodity deve ter unidade definida."""
    for nome, info in COMMODITIES_SUPORTADAS.items():
        assert "unidade" in info, f"{nome} sem unidade"
        assert info["unidade"], f"{nome} com unidade vazia"


# ── Register ───────────────────────────────────────────────

def test_register_tools(mcp_mock):
    """Deve registrar exatamente 3 ferramentas."""
    register_tools(mcp_mock)
    assert "get_commodity_price" in mcp_mock._tools
    assert "get_weather_forecast" in mcp_mock._tools
    assert "get_weather_alert" in mcp_mock._tools
    assert len(mcp_mock._tools) == 3


# ── get_commodity_price ────────────────────────────────────

@pytest.mark.asyncio
async def test_get_commodity_price_invalida(mcp_mock):
    """Commodity não suportada retorna erro descritivo."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_commodity_price"]
    result = await fn(commodity="abacate")
    assert "não suportada" in result.lower()


@pytest.mark.asyncio
async def test_get_commodity_price_invalida_lista_disponiveis(mcp_mock):
    """Erro deve listar commodities disponíveis."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_commodity_price"]
    result = await fn(commodity="xxx")
    assert "soja" in result
    assert "milho" in result


@pytest.mark.asyncio
async def test_get_commodity_price_cache_hit(mcp_mock):
    """Deve retornar do cache quando disponível."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_commodity_price"]

    with patch("src.tools.agrinho.get_cached", return_value="cached result"):
        result = await fn(commodity="soja")
        assert result == "cached result"


@pytest.mark.asyncio
async def test_get_commodity_price_cepea_sucesso(mcp_mock):
    """CEPEA scraping com sucesso retorna preço formatado."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_commodity_price"]

    with patch("src.tools.agrinho.get_cached", return_value=None), \
         patch("src.tools.agrinho.http_client") as mock_http, \
         patch("src.tools.agrinho.set_cached"):
        mock_response = MagicMock()
        mock_response.text = '<html><span class="indicador">R$ 142,50</span></html>'
        mock_response.raise_for_status = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        result = await fn(commodity="soja")
        assert "Soja" in result
        assert "CEPEA" in result
        assert "R$" in result


@pytest.mark.asyncio
async def test_get_commodity_price_normaliza_entrada(mcp_mock):
    """Deve normalizar 'Boi Gordo' para 'boi_gordo'."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_commodity_price"]

    with patch("src.tools.agrinho.get_cached", return_value="cached boi"):
        result = await fn(commodity="Boi Gordo")
        assert result == "cached boi"


# ── get_weather_forecast ───────────────────────────────────

@pytest.mark.asyncio
async def test_get_weather_forecast_cache_hit(mcp_mock):
    """Deve retornar do cache quando disponível."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_weather_forecast"]

    with patch("src.tools.agrinho.get_cached", return_value="cached forecast"):
        result = await fn(municipio="Chapecó")
        assert result == "cached forecast"


@pytest.mark.asyncio
async def test_get_weather_forecast_ibge_erro(mcp_mock):
    """Município inválido retorna erro do IBGE."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_weather_forecast"]

    with patch("src.tools.agrinho.get_cached", return_value=None), \
         patch("src.tools.agrinho.resolver_codigo_ibge", new_callable=AsyncMock,
               side_effect=ValueError("Município 'xyz' não encontrado")):
        result = await fn(municipio="xyz")
        assert "não encontrado" in result.lower()


@pytest.mark.asyncio
async def test_get_weather_forecast_sucesso(mcp_mock):
    """Previsão com sucesso retorna dados formatados."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_weather_forecast"]

    with patch("src.tools.agrinho.resolver_codigo_ibge", new_callable=AsyncMock, return_value="4204202"), \
         patch("src.tools.agrinho.get_cached", return_value=None), \
         patch("src.tools.agrinho.http_client") as mock_http, \
         patch("src.tools.agrinho.set_cached"):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "4204202": {
                "06/05/2026": {
                    "manha": {"temp_max": 28, "temp_min": 15, "resumo": "Poucas nuvens",
                              "int_vento": "Fraco", "dir_vento": "NE",
                              "umidade_max": 80, "umidade_min": 40},
                    "tarde": {"temp_max": 30, "temp_min": 18, "resumo": "Parcialmente nublado",
                              "int_vento": "Moderado", "dir_vento": "SE",
                              "umidade_max": 70, "umidade_min": 35},
                    "noite": {"temp_max": 20, "temp_min": 12, "resumo": "Céu limpo",
                              "int_vento": "Fraco", "dir_vento": "S",
                              "umidade_max": 85, "umidade_min": 50},
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        result = await fn(municipio="Chapecó")
        assert "Chapecó" in result
        assert "INMET" in result
        assert "Manhã" in result
        assert "28" in result


@pytest.mark.asyncio
async def test_get_weather_forecast_inmet_indisponivel(mcp_mock):
    """INMET fora retorna mensagem de erro."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_weather_forecast"]

    with patch("src.tools.agrinho.resolver_codigo_ibge", new_callable=AsyncMock, return_value="4204202"), \
         patch("src.tools.agrinho.get_cached", return_value=None), \
         patch("src.tools.agrinho.http_client") as mock_http:
        mock_http.get = AsyncMock(side_effect=Exception("timeout"))

        result = await fn(municipio="Chapecó")
        assert "indisponível" in result.lower()


# ── get_weather_alert ──────────────────────────────────────

@pytest.mark.asyncio
async def test_get_weather_alert_cache_hit(mcp_mock):
    """Deve retornar do cache quando disponível."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_weather_alert"]

    with patch("src.tools.agrinho.get_cached", return_value="cached alert"):
        result = await fn(municipio="Chapecó")
        assert result == "cached alert"


@pytest.mark.asyncio
async def test_get_weather_alert_sem_alerta(mcp_mock):
    """Sem alertas retorna mensagem positiva."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_weather_alert"]

    with patch("src.tools.agrinho.resolver_codigo_ibge", new_callable=AsyncMock, return_value="4204202"), \
         patch("src.tools.agrinho.resolver_lat_lon", new_callable=AsyncMock, return_value=(-27.10, -52.62)), \
         patch("src.tools.agrinho.get_cached", return_value=None), \
         patch("src.tools.agrinho.http_client") as mock_http, \
         patch("src.tools.agrinho.set_cached"):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        result = await fn(municipio="Chapecó")
        assert "nenhum alerta" in result.lower()
        assert "INMET" in result


@pytest.mark.asyncio
async def test_get_weather_alert_com_alerta(mcp_mock):
    """Com alertas deve listar severidade e tipo."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_weather_alert"]

    with patch("src.tools.agrinho.resolver_codigo_ibge", new_callable=AsyncMock, return_value="4204202"), \
         patch("src.tools.agrinho.resolver_lat_lon", new_callable=AsyncMock, return_value=(-27.10, -52.62)), \
         patch("src.tools.agrinho.get_cached", return_value=None), \
         patch("src.tools.agrinho.http_client") as mock_http, \
         patch("src.tools.agrinho.set_cached"):
        mock_response = MagicMock()
        mock_response.json.return_value = [{
            "severidade": "laranja",
            "tipo": "Geada",
            "descricao": "Possibilidade de geada forte",
            "inicio": "06/05/2026",
            "fim": "07/05/2026",
        }]
        mock_response.raise_for_status = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        result = await fn(municipio="Chapecó")
        assert "laranja" in result.lower() or "LARANJA" in result
        assert "Geada" in result or "geada" in result.lower()
        assert "INMET" in result


@pytest.mark.asyncio
async def test_get_weather_alert_ibge_erro(mcp_mock):
    """Município inválido retorna erro."""
    register_tools(mcp_mock)
    fn = mcp_mock._tools["get_weather_alert"]

    with patch("src.tools.agrinho.get_cached", return_value=None), \
         patch("src.tools.agrinho.resolver_codigo_ibge", new_callable=AsyncMock,
               side_effect=ValueError("Município 'xyz' não encontrado")):
        result = await fn(municipio="xyz")
        assert "não encontrado" in result.lower()
