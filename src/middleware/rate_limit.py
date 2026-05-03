"""Middleware de rate limiting — delega para usage service."""

from src.services import usage


def verificar_rate_limit(api_key: str) -> dict:
    """
    Verifica rate limit per-minute para uma API key.

    Retorna dict com:
    - allowed: True se permitido
    - count: requisicoes no ultimo minuto
    - limit: limite por minuto do plano
    - remaining: requisicoes restantes
    """
    return usage.check_rate_limit(api_key)


def verificar_limite_mensal(api_key: str) -> dict:
    """
    Verifica limite mensal de uso.

    Retorna dict com:
    - allowed: True se dentro do limite
    - usage: uso atual
    - limit: limite mensal do plano
    - remaining: requisicoes restantes
    """
    return usage.check_monthly_limit(api_key)
