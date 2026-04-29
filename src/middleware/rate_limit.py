"""Middleware de rate limiting — controle de requisições por IP/API key."""

import time
from src.middleware.auth import TIER_FREE, TIER_PAID


# Armazenamento em memória: {chave: {"count": int, "reset_at": float}}
_contadores: dict[str, dict] = {}

# Janela de 24 horas em segundos
_JANELA_24H = 86400


def _chave_contador(identificador: str, tier: str) -> str:
    """Gera a chave do contador: 'tier:identificador'."""
    return f"{tier}:{identificador}"


def _resetar_se_necessario(chave: str) -> None:
    """Reseta o contador se a janela de 24h expirou."""
    if chave in _contadores:
        if time.time() >= _contadores[chave]["reset_at"]:
            del _contadores[chave]


def verificar_rate_limit(identificador: str, tier: str, daily_limit: int) -> dict:
    """
    Verifica se a requisição está dentro do rate limit.

    Parâmetros:
    - identificador: IP (free) ou API key (paid)
    - tier: "free" ou "paid"
    - daily_limit: limite diário do tier

    Retorna dict com:
    - allowed: True se permitido, False se bloqueado
    - count: requisições feitas hoje
    - limit: limite do tier
    - remaining: requisições restantes
    - reset_at: timestamp de quando o contador reseta
    """
    chave = _chave_contador(identificador, tier)
    _resetar_se_necessario(chave)

    if chave not in _contadores:
        _contadores[chave] = {
            "count": 0,
            "reset_at": time.time() + _JANELA_24H,
        }

    contador = _contadores[chave]

    if contador["count"] >= daily_limit:
        return {
            "allowed": False,
            "count": contador["count"],
            "limit": daily_limit,
            "remaining": 0,
            "reset_at": contador["reset_at"],
        }

    contador["count"] += 1

    return {
        "allowed": True,
        "count": contador["count"],
        "limit": daily_limit,
        "remaining": daily_limit - contador["count"],
        "reset_at": contador["reset_at"],
    }


def limpar_contadores() -> None:
    """Limpa todos os contadores. Útil para testes."""
    _contadores.clear()
