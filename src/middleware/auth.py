"""Middleware de autenticação — validação de API key."""

from src.config import FREE_TIER_DAILY_LIMIT, PAID_TIER_DAILY_LIMIT


# Tipos de tier
TIER_FREE = "free"
TIER_PAID = "paid"


def verificar_autenticacao(headers: dict) -> dict:
    """
    Verifica o tier do usuário a partir do header X-API-Key.

    Retorna dict com:
    - tier: "free" ou "paid"
    - api_key: a chave usada (ou None para tier free)
    - daily_limit: limite diário do tier

    Regras:
    - Sem X-API-Key ou chave vazia → tier free (FREE_TIER_DAILY_LIMIT/dia)
    - X-API-Key não vazia → tier pago (PAID_TIER_DAILY_LIMIT/dia)
    """
    api_key = headers.get("x-api-key", "").strip()

    if api_key:
        return {
            "tier": TIER_PAID,
            "api_key": api_key,
            "daily_limit": PAID_TIER_DAILY_LIMIT,
        }

    return {
        "tier": TIER_FREE,
        "api_key": None,
        "daily_limit": FREE_TIER_DAILY_LIMIT,
    }
