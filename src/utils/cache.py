"""Cache em memória com TTL para reduzir chamadas a APIs externas."""

import sys
import time
from typing import Any


_cache: dict[str, dict[str, Any]] = {}


def get_cached(key: str) -> Any | None:
    """
    Retorna valor do cache se existir e não estiver expirado.

    Retorna None se a chave não existir ou o TTL tiver expirado.
    """
    entry = _cache.get(key)
    if entry is None:
        return None

    if time.time() > entry["expires"]:
        del _cache[key]
        return None

    return entry["value"]


def set_cached(key: str, value: Any, ttl_seconds: int) -> None:
    """
    Armazena valor no cache com TTL em segundos.

    - ttl_seconds=0 → cache permanente (nunca expira)
    """
    expires = float("inf") if ttl_seconds == 0 else time.time() + ttl_seconds
    _cache[key] = {"value": value, "expires": expires}


def limpar_cache() -> int:
    """Remove entradas expiradas. Retorna quantidade removida."""
    now = time.time()
    expiradas = [k for k, v in _cache.items() if now > v["expires"]]
    for k in expiradas:
        del _cache[k]
    return len(expiradas)


# TTLs padrão (segundos)
TTL_FERIADOS = 86400       # 24h — feriados nacionais não mudam
TTL_MOEDA = 300            # 5min — cotação muda rápido
TTL_BANCO = 3600           # 1h — dados de banco raramente mudam
TTL_DDD = 0                # permanente — DDDs nunca mudam

# TTLs Agrinho (segundos)
TTL_COMMODITY = 14400      # 4h — fechamento CEPEA ~15h
TTL_WEATHER_FORECAST = 10800  # 3h — INMET atualiza 4x/dia
TTL_WEATHER_ALERT = 1800   # 30min — alertas mudam rápido
TTL_IBGE_CODE = 86400      # 24h — municípios não mudam
TTL_LAT_LON = 86400        # 24h — coordenadas fixas
