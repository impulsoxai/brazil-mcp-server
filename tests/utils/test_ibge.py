import pytest
from unittest.mock import AsyncMock, patch
from src.utils.ibge import normalizar_municipio, resolver_codigo_ibge, resolver_lat_lon


def test_normalizar_municipio_acentos():
    assert normalizar_municipio("Chapecó") == "chapeco"


def test_normalizar_municipio_uppercase():
    assert normalizar_municipio("SÃO PAULO") == "sao paulo"


def test_normalizar_municipio_strip():
    assert normalizar_municipio("  Curitiba  ") == "curitiba"


@pytest.mark.asyncio
async def test_resolver_codigo_ibge_cache():
    with patch("src.utils.ibge.get_cached", return_value="4204202"):
        result = await resolver_codigo_ibge("Chapecó")
        assert result == "4204202"


@pytest.mark.asyncio
async def test_resolver_codigo_ibge_api():
    with patch("src.utils.ibge.get_cached", return_value=None), \
         patch("src.utils.ibge.http_client") as mock_http, \
         patch("src.utils.ibge.set_cached"):
        mock_response = AsyncMock()
        mock_response.json.return_value = [
            {"nome": "Chapecó", "codigo_ibge": "4204202", "uf": "SC"}
        ]
        mock_response.raise_for_status = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        result = await resolver_codigo_ibge("Chapecó")
        assert result == "4204202"


@pytest.mark.asyncio
async def test_resolver_codigo_ibge_not_found():
    with patch("src.utils.ibge.get_cached", return_value=None), \
         patch("src.utils.ibge.http_client") as mock_http:
        mock_response = AsyncMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        with pytest.raises(ValueError, match="não encontrado"):
            await resolver_codigo_ibge("MunicipioInexistente")


@pytest.mark.asyncio
async def test_resolver_lat_lon():
    """Test resolver_lat_lon with Nominatim-compatible mock data."""
    with patch("src.utils.ibge.get_cached", return_value=None), \
         patch("src.utils.ibge.http_client") as mock_http, \
         patch("src.utils.ibge.set_cached"):
        mock_response = AsyncMock()
        # Nominatim returns a flat JSON array with lat/lon keys
        mock_response.json.return_value = [
            {"lat": "-27.10", "lon": "-52.62"}
        ]
        mock_response.raise_for_status = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        lat, lon = await resolver_lat_lon("4204202")
        assert lat == pytest.approx(-27.10)
        assert lon == pytest.approx(-52.62)
