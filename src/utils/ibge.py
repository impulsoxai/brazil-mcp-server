"""Resolução de município → código IBGE e coordenadas."""

import json
from difflib import get_close_matches

from unidecode import unidecode

from src.utils import http_client
from src.utils.cache import get_cached, set_cached, TTL_IBGE_CODE, TTL_LAT_LON


def normalizar_municipio(municipio: str) -> str:
    """Normaliza nome do município: lowercase, sem acentos, strip."""
    return unidecode(municipio.strip().lower())


_IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
_CACHE_KEY_LISTA = "ibge:lista_municipios"


async def _carregar_municipios() -> dict[str, str]:
    """
    Carrega lista completa de municípios do IBGE.
    Cache de 24h. Retorna dict {nome_normalizado: codigo_ibge}.
    """
    cached = get_cached(_CACHE_KEY_LISTA)
    if cached is not None:
        return cached

    try:
        response = await http_client.get(_IBGE_MUNICIPIOS_URL)
        response.raise_for_status()
        try:
            data = response.json()
        except UnicodeDecodeError:
            data = json.loads(response.content.decode("latin-1"))
    except Exception:
        raise ValueError(
            "❌ Serviço do IBGE indisponível.\n"
            "Dica: tente novamente em alguns minutos."
        )

    mapping: dict[str, str] = {}
    for item in data:
        nome = normalizar_municipio(item.get("nome", ""))
        codigo = str(item.get("id", ""))
        if nome and codigo:
            mapping[nome] = codigo

    set_cached(_CACHE_KEY_LISTA, mapping, TTL_IBGE_CODE)
    return mapping


async def resolver_codigo_ibge(municipio: str) -> str:
    """
    Resolve nome do município para código IBGE.

    Normaliza input, busca na lista completa do IBGE (cache 24h).
    Tenta match exato, depois fuzzy (difflib).
    Raises ValueError se não encontrar.
    """
    normalizado = normalizar_municipio(municipio)

    cached = get_cached(f"ibge:{normalizado}")
    if cached is not None:
        return cached

    municipios = await _carregar_municipios()

    # Match exato
    codigo = municipios.get(normalizado)

    # Fuzzy match — encontra mais próximo (cutoff 0.6)
    if not codigo:
        matches = get_close_matches(normalizado, municipios.keys(), n=1, cutoff=0.6)
        if matches:
            codigo = municipios[matches[0]]

    if not codigo:
        raise ValueError(
            f"❌ Município '{municipio}' não encontrado.\n"
            "Dica: verifique a grafia e tente novamente."
        )

    set_cached(f"ibge:{normalizado}", codigo, TTL_IBGE_CODE)
    return codigo


async def resolver_lat_lon(ibge_code: str, municipio: str = "") -> tuple[float, float]:
    """
    Resolve código IBGE para latitude/longitude.

    Usa Nominatim (OpenStreetMap) com nome do município.
    Cache 24h. Raises ValueError se não encontrar.
    """
    cached = get_cached(f"latlon:{ibge_code}")
    if cached is not None:
        return cached

    # Nominatim busca por nome, não por código IBGE
    query = f"{municipio}, Brasil" if municipio else ibge_code

    try:
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
        headers = {"User-Agent": "BrazilMCPServer/1.0"}
        response = await http_client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception:
        raise ValueError(
            f"❌ Coordenadas não encontradas para {municipio or ibge_code}.\n"
            "Dica: tente novamente em alguns minutos."
        )

    if not data:
        raise ValueError(
            f"❌ Coordenadas não encontradas para {municipio or ibge_code}."
        )

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])

    set_cached(f"latlon:{ibge_code}", (lat, lon), TTL_LAT_LON)
    return lat, lon
