"""Resolução de município → código IBGE e coordenadas."""

from unidecode import unidecode

from src.utils import http_client
from src.utils.cache import get_cached, set_cached, TTL_IBGE_CODE, TTL_LAT_LON


def normalizar_municipio(municipio: str) -> str:
    """Normaliza nome do município: lowercase, sem acentos, strip."""
    return unidecode(municipio.strip().lower())


async def resolver_codigo_ibge(municipio: str) -> str:
    """
    Resolve nome do município para código IBGE.

    Normaliza input, tenta cache, busca via BrasilAPI.
    Raises ValueError se não encontrar.
    """
    normalizado = normalizar_municipio(municipio)

    cached = get_cached(f"ibge:{normalizado}")
    if cached is not None:
        return cached

    try:
        url = f"https://brasilapi.com.br/api/ibge/municipios/v1/{normalizado}"
        response = await http_client.get(url)
        response.raise_for_status()
        data = response.json()
    except Exception:
        raise ValueError(
            f"❌ Município '{municipio}' não encontrado.\n"
            "Dica: verifique a grafia e tente novamente."
        )

    if not data:
        raise ValueError(
            f"❌ Município '{municipio}' não encontrado.\n"
            "Dica: verifique a grafia e tente novamente."
        )

    codigo = str(data[0].get("codigo_ibge", ""))
    if not codigo:
        raise ValueError(
            f"❌ Código IBGE não disponível para '{municipio}'.\n"
            "Dica: tente o nome completo do município."
        )

    set_cached(f"ibge:{normalizado}", codigo, TTL_IBGE_CODE)
    return codigo


async def resolver_lat_lon(ibge_code: str) -> tuple[float, float]:
    """
    Resolve código IBGE para latitude/longitude.

    Usa Nominatim (OpenStreetMap). Cache 24h.
    Raises ValueError se não encontrar.
    """
    cached = get_cached(f"latlon:{ibge_code}")
    if cached is not None:
        return cached

    try:
        url = f"https://nominatim.openstreetmap.org/search?q={ibge_code}&format=json&limit=1"
        headers = {"User-Agent": "BrazilMCPServer/1.0"}
        response = await http_client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception:
        raise ValueError(
            f"❌ Coordenadas não encontradas para código IBGE {ibge_code}.\n"
            "Dica: tente novamente em alguns minutos."
        )

    if not data:
        raise ValueError(
            f"❌ Coordenadas não encontradas para código IBGE {ibge_code}."
        )

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])

    set_cached(f"latlon:{ibge_code}", (lat, lon), TTL_LAT_LON)
    return lat, lon
