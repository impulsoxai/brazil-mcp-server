"""Middleware de autenticacao — validacao de API key."""

from src.config import IMPULSOX_MASTER_KEY
from src.services import usage


def verificar_autenticacao(headers: dict) -> dict:
    """
    Verifica API key no header x-api-key.

    Retorna dict com:
    - valid: True se chave valida
    - api_key: a chave usada
    - plan: plano do usuario (None para master)
    - scope: "master" ou "public"
    - skip_rate_limit: True para master key
    - error: mensagem de erro (ou None)

    Regras:
    - Sem x-api-key ou chave vazia → 401
    - IMPULSOX_MASTER_KEY → scope "master", sem rate limit
    - Chave invalida → 401
    - Chave valida → OK
    """
    api_key = headers.get("x-api-key", "").strip()

    if not api_key:
        return {
            "valid": False,
            "api_key": None,
            "plan": None,
            "scope": None,
            "skip_rate_limit": False,
            "error": "Invalid or missing API key",
        }

    # Master key — acesso total, sem rate limit
    if IMPULSOX_MASTER_KEY and api_key == IMPULSOX_MASTER_KEY:
        return {
            "valid": True,
            "api_key": api_key,
            "plan": None,
            "scope": "master",
            "skip_rate_limit": True,
            "error": None,
        }

    # Key normal — valida contra api_keys.json
    key_data = usage.validate_key(api_key)
    if not key_data:
        return {
            "valid": False,
            "api_key": api_key,
            "plan": None,
            "scope": None,
            "skip_rate_limit": False,
            "error": "Invalid or missing API key",
        }

    return {
        "valid": True,
        "api_key": api_key,
        "plan": key_data["plan"],
        "scope": key_data.get("scope", "public"),
        "skip_rate_limit": False,
        "error": None,
    }
