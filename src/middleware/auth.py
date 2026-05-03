"""Middleware de autenticacao — validacao de API key."""

from src.services import usage


def verificar_autenticacao(headers: dict) -> dict:
    """
    Verifica API key no header x-api-key.

    Retorna dict com:
    - valid: True se chave valida
    - api_key: a chave usada
    - plan: plano do usuario
    - error: mensagem de erro (ou None)

    Regras:
    - Sem x-api-key ou chave vazia → 401
    - Chave invalida → 401
    - Chave valida → OK
    """
    api_key = headers.get("x-api-key", "").strip()

    if not api_key:
        return {
            "valid": False,
            "api_key": None,
            "plan": None,
            "error": "Invalid or missing API key",
        }

    key_data = usage.validate_key(api_key)
    if not key_data:
        return {
            "valid": False,
            "api_key": api_key,
            "plan": None,
            "error": "Invalid or missing API key",
        }

    return {
        "valid": True,
        "api_key": api_key,
        "plan": key_data["plan"],
        "error": None,
    }
