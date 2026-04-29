"""Middleware de autenticação — validação de API key.

Sprint 3 — Será implementado:
- Validação de API key via header Authorization
- Distinção entre tier free (100 req/dia) e paid (10.000 req/dia)
- Armazenamento de keys em banco de dados (SQLite ou PostgreSQL)
- Endpoints de criação/revogação de keys
"""


def verificar_autenticacao(headers: dict) -> bool:
    """Verifica se a requisição está autenticada.

    Por ora, sempre retorna True (sem autenticação real).
    No Sprint 3, validará a API key do header Authorization.
    """
    return True
